# Databricks notebook source
# MAGIC %pip install ray

# COMMAND ----------

# Minimal test to verify AIv4 environment has compatible HuggingFace packages
from serverless_gpu.ray import ray_launch

@ray_launch(gpus=4, gpu_type='A10', remote=True)
def train_func():
    """Ray Train + Ray Data + FSDP distributed training."""
    
    import os
    import io
    import torch
    import mlflow
    import ray
    import ray.data
    import numpy as np
    from PIL import Image
    from datasets import load_dataset
    from torch.utils.data import Dataset as TorchDataset, DataLoader
    from transformers import (
        Qwen2VLForConditionalGeneration,
        AutoProcessor,
    )
    from peft import LoraConfig, get_peft_model
    from ray import train as ray_train
    from ray.train.torch import TorchTrainer
    from ray.train import ScalingConfig, RunConfig
    from ray.train.torch import TorchConfig
    
    # =========================================================================
    # PART 1: Load Dataset using Ray Data
    # =========================================================================
    
    def create_ray_dataset():
        """Load HuggingFace dataset and convert to Ray Data."""
        hf_dataset = load_dataset(
            "HuggingFaceH4/llava-instruct-mix-vsft",
            split="train[:1000]"
        )
        
        # Convert images to numpy for Arrow serialization
        dataset_items = []
        for item in hf_dataset:
            item_dict = dict(item)
            if "images" in item_dict and item_dict["images"]:
                item_dict["images"] = [
                    np.array(img) if hasattr(img, "convert") else img 
                    for img in item_dict["images"]
                ]
            dataset_items.append(item_dict)
        
        return ray.data.from_items(dataset_items)
    
    # =========================================================================
    # PART 2: Custom PyTorch Dataset for VLM
    # =========================================================================
    
    class VLMDataset(TorchDataset):
        """PyTorch Dataset that holds pre-formatted VLM data."""
        
        MAX_TEXT_LENGTH = 1500  # Limit text length to control sequence size
        MAX_IMAGE_SIZE = 448    # Resize large images to reduce tokens
        
        def __init__(self, items, processor):
            self.items = items
            self.processor = processor
        
        def __len__(self):
            return len(self.items)
        
        def __getitem__(self, idx):
            item = self.items[idx]
            messages = item["messages"]
            img = item.get("image")
            
            # Truncate long text in messages to control sequence length
            truncated_messages = []
            for msg in messages:
                if msg["role"] == "assistant":
                    content = msg["content"]
                    if isinstance(content, str) and len(content) > self.MAX_TEXT_LENGTH:
                        content = content[:self.MAX_TEXT_LENGTH] + "..."
                    truncated_messages.append({"role": "assistant", "content": content})
                else:
                    truncated_messages.append(msg)
            
            # Apply chat template
            text = self.processor.apply_chat_template(
                truncated_messages,
                tokenize=False,
                add_generation_prompt=False
            )
            
            # Resize large images to reduce token count
            if img is not None:
                w, h = img.size
                if max(w, h) > self.MAX_IMAGE_SIZE:
                    ratio = self.MAX_IMAGE_SIZE / max(w, h)
                    new_size = (int(w * ratio), int(h * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
            
            return {
                "text": text,
                "image": img if img else Image.new("RGB", (224, 224), "white"),
            }
    
    def vlm_collate_fn(batch, processor):
        """Collate function for VLM batch processing."""
        texts = [b["text"] for b in batch]
        images = [b["image"] for b in batch]
        
        # Tokenize with max_length as safety net, but images are already resized
        try:
            encoded = processor(
                text=texts,
                images=images,
                padding=True,
                truncation=True,
                max_length=2048,  # Safety limit - images are resized so this is safe
                return_tensors="pt",
            )
        except ValueError as e:
            # If image token mismatch, try without truncation
            print(f"Warning: Retrying without truncation due to: {e}")
            encoded = processor(
                text=texts,
                images=images,
                padding=True,
                truncation=False,
                return_tensors="pt",
            )
        
        encoded["labels"] = encoded["input_ids"].clone()
        return encoded
    
    # =========================================================================
    # PART 3: Training Function with FSDP
    # =========================================================================
    
    def train_func_distributed(config: dict):
        """Training function for each worker with FSDP."""
        rank = int(os.environ.get("RANK", 0))
        local_rank = int(os.environ.get("LOCAL_RANK", 0))
        world_size = int(os.environ.get("WORLD_SIZE", 1))
        
        if rank == 0:
            os.environ["MLFLOW_EXPERIMENT_NAME"] = config["experiment_name"]
            os.environ["MLFLOW_TRACKING_URI"] = "databricks"
            mlflow.start_run()
        
        # Load model in full precision (FSDP will shard it)
        MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )
        processor = AutoProcessor.from_pretrained(MODEL_NAME)
        
        # Add LoRA
        lora_config = LoraConfig(
            r=16,
            lora_alpha=16,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, lora_config)
        
        # CRITICAL: Cast ALL parameters to bfloat16 for uniform dtype
        # PEFT/LoRA adds float32 params by default, FSDP requires uniform dtype
        model = model.to(torch.bfloat16)
        
        # Enable gradient checkpointing before FSDP
        model.train()
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        
        # ==== TRUE FSDP SETUP ====
        # Import FSDP components
        from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
        from torch.distributed.fsdp import ShardingStrategy, MixedPrecision
        from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy
        from functools import partial
        
        # Get the transformer block class for auto-wrap policy
        # For Qwen2-VL, the decoder layers are Qwen2VLDecoderLayer
        from transformers.models.qwen2_vl.modeling_qwen2_vl import Qwen2VLDecoderLayer
        
        # Define auto-wrap policy - wrap each transformer layer
        auto_wrap_policy = partial(
            transformer_auto_wrap_policy,
            transformer_layer_cls={Qwen2VLDecoderLayer},
        )
        
        # Mixed precision policy for bfloat16
        mixed_precision_policy = MixedPrecision(
            param_dtype=torch.bfloat16,
            reduce_dtype=torch.bfloat16,
            buffer_dtype=torch.bfloat16,
        )
        
        # Wrap model with FSDP - FULL_SHARD shards params across all GPUs
        device = torch.device(f"cuda:{local_rank}")
        model = FSDP(
            model,
            sharding_strategy=ShardingStrategy.FULL_SHARD,
            mixed_precision=mixed_precision_policy,
            auto_wrap_policy=auto_wrap_policy,
            device_id=device,
            use_orig_params=True,  # Required for gradient checkpointing with PEFT
        )
        
        print(f"Rank {rank}: Model wrapped with FSDP (FULL_SHARD)")
        
        # Get Ray Dataset shard and format for training
        train_dataset_shard = ray_train.get_dataset_shard("train")
        
        # Process shard into list format
        train_items = []
        for batch in train_dataset_shard.iter_batches(batch_size=10):
            batch_size = len(batch["messages"])
            
            for i in range(batch_size):
                messages = batch["messages"][i]
                raw_images = batch.get("images", [None] * batch_size)[i] or []
                
                formatted_messages = []
                img = None
                
                for msg_idx, msg in enumerate(messages):
                    if msg["role"] == "user":
                        content = []
                        
                        # Get image for first user message
                        if raw_images and msg_idx == 0:
                            img_data = raw_images[0] if isinstance(raw_images, list) else raw_images
                            if isinstance(img_data, np.ndarray):
                                img = Image.fromarray(img_data).convert("RGB")
                            elif isinstance(img_data, dict):
                                if "bytes" in img_data and img_data["bytes"]:
                                    img = Image.open(io.BytesIO(img_data["bytes"])).convert("RGB")
                            elif hasattr(img_data, "convert"):
                                img = img_data.convert("RGB")
                            
                            if img:
                                content.append({"type": "image", "image": img})
                        
                        # Add text
                        if isinstance(msg["content"], str):
                            content.append({"type": "text", "text": msg["content"]})
                        elif isinstance(msg["content"], list):
                            for item in msg["content"]:
                                if item.get("type") == "text":
                                    content.append(item)
                        
                        formatted_messages.append({"role": "user", "content": content})
                    else:
                        text = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
                        formatted_messages.append({"role": "assistant", "content": text})
                
                train_items.append({
                    "messages": formatted_messages,
                    "image": img,
                })
        
        # Create PyTorch DataLoader
        train_dataset = VLMDataset(train_items, processor)
        train_dataloader = DataLoader(
            train_dataset,
            batch_size=2,
            shuffle=True,
            collate_fn=lambda b: vlm_collate_fn(b, processor),
            num_workers=0,
        )
        
        # Training hyperparameters
        MAX_STEPS = 20
        LEARNING_RATE = 2e-4
        WARMUP_STEPS = 10
        GRADIENT_ACCUMULATION_STEPS = 4
        LOGGING_STEPS = 10
        
        # Setup optimizer with only trainable parameters
        trainable_params = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(trainable_params, lr=LEARNING_RATE)
        
        # Training loop
        global_step = 0
        running_loss = 0.0
        optimizer.zero_grad()
        
        while global_step < MAX_STEPS:
            for batch_idx, batch in enumerate(train_dataloader):
                if global_step >= MAX_STEPS:
                    break
                
                # Move to device
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)
                pixel_values = batch.get("pixel_values")
                image_grid_thw = batch.get("image_grid_thw")
                
                if pixel_values is not None:
                    pixel_values = pixel_values.to(device)
                if image_grid_thw is not None:
                    image_grid_thw = image_grid_thw.to(device)
                
                # Forward pass
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                    pixel_values=pixel_values,
                    image_grid_thw=image_grid_thw,
                )
                
                loss = outputs.loss / GRADIENT_ACCUMULATION_STEPS
                running_loss += loss.item()
                loss.backward()
                
                if (batch_idx + 1) % GRADIENT_ACCUMULATION_STEPS == 0:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    optimizer.zero_grad()
                    global_step += 1
                    
                    if global_step % LOGGING_STEPS == 0 and rank == 0:
                        avg_loss = running_loss / LOGGING_STEPS
                        print(f"Step {global_step}: loss = {avg_loss:.4f}")
                        mlflow.log_metrics({"train_loss": avg_loss}, step=global_step)
                        running_loss = 0.0
                    
                    ray_train.report({"loss": loss.item() * GRADIENT_ACCUMULATION_STEPS, "step": global_step})
        
        # Save model - FSDP requires gathering full state dict
        # FSDP save: ALL ranks must participate in state_dict_type (collective operation)
        # But only rank 0 actually saves the file
        from torch.distributed.fsdp import FullStateDictConfig, StateDictType
        
        adapter_path = f"{config['checkpoint_dir']}/final_adapter"
        os.makedirs(adapter_path, exist_ok=True)
        
        full_state_dict_config = FullStateDictConfig(offload_to_cpu=True, rank0_only=True)
        with FSDP.state_dict_type(model, StateDictType.FULL_STATE_DICT, full_state_dict_config):
            state_dict = model.state_dict()
            # Only rank 0 saves the file
            if rank == 0:
                torch.save(state_dict, f"{adapter_path}/adapter_model.bin")
                processor.save_pretrained(adapter_path)
                mlflow.end_run()
                print(f"Training complete! Adapter saved to {adapter_path}")
    
    # =========================================================================
    # PART 4: Ray Train Setup with FSDP
    # =========================================================================
    
    ray_dataset = create_ray_dataset()
    
    # FSDP configuration via TorchConfig
    torch_config = TorchConfig(
        backend="nccl",
    )
    
    scaling_config = ScalingConfig(
        num_workers=4,  # 4 GPUs
        use_gpu=True,
        resources_per_worker={"GPU": 1},
    )
    
    run_config = RunConfig(
        name="ray-data-fsdp",
        storage_path=CHECKPOINT_DIR,
    )
    
    train_config = {
        "experiment_name": EXPERIMENT_NAME,
        "checkpoint_dir": CHECKPOINT_DIR,
    }
    
    ray_trainer = TorchTrainer(
        train_loop_per_worker=train_func_distributed,
        train_loop_config=train_config,
        scaling_config=scaling_config,
        run_config=run_config,
        torch_config=torch_config,
        datasets={"train": ray_dataset},
    )
    
    result = ray_trainer.fit()
    return result

# =========================================================================
# PART 5: Test Inference Function
# =========================================================================
def test_inference(adapter_path: str = "/dbfs/checkpoints/qwen2-vl-demo/final_adapter"):
    """
    Load the trained model and run inference on a sample image.
    
    Args:
        adapter_path: Path to the saved LoRA adapter weights
    """
    import torch
    import io
    from PIL import Image
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    from peft import PeftModel
    from datasets import load_dataset
    
    print("\n" + "="*50)
    print("Loading model for inference...")
    print("="*50)
    
    MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
    
    # Load base model
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    
    # Load LoRA adapter (if available)
    try:
        model = PeftModel.from_pretrained(model, adapter_path)
        print(f"✓ Loaded adapter from {adapter_path}")
    except Exception as e:
        print(f"⚠ Could not load adapter: {e}")
        print("  Using base model without fine-tuning")
    
    model.eval()
    
    # Get a sample image from the dataset
    print("Loading sample image...")
    hf_dataset = load_dataset(
        "HuggingFaceH4/llava-instruct-mix-vsft",
        split="train[:1]"
    )
    
    sample = hf_dataset[0]
    raw_image = sample["images"][0] if sample.get("images") else None
    
    if raw_image:
        # Convert to PIL
        if isinstance(raw_image, dict) and "bytes" in raw_image and raw_image["bytes"]:
            example_image = Image.open(io.BytesIO(raw_image["bytes"])).convert("RGB")
        elif hasattr(raw_image, "convert"):
            example_image = raw_image.convert("RGB")
        else:
            example_image = Image.new("RGB", (224, 224), "white")
        
        # Prepare inference input
        instruction = "Describe this image in detail."
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": example_image},
                    {"type": "text", "text": instruction}
                ]
            }
        ]
        
        input_text = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )
        
        inputs = processor(
            images=example_image,
            text=input_text,
            return_tensors="pt",
        ).to(model.device)
        
        # Generate response
        print("Generating response...")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=True,
                temperature=0.7,
            )
        
        response = processor.batch_decode(
            outputs[:, inputs["input_ids"].shape[1]:], 
            skip_special_tokens=True
        )[0]
        
        print("\n" + "="*50)
        print(f"Instruction: {instruction}")
        print(f"Model Response: {response}")
        print("="*50)
        
        return response
    else:
        print("No sample image available for inference test")
        return None


# =========================================================================
# PART 6: Launch Training (uncomment inference to test after)
# =========================================================================

# Run training
result = train_func.distributed()
print(f"\nTraining Result: {result}")

# Run inference test (uncomment after training completes)
# test_inference("/dbfs/checkpoints/qwen2-vl-demo/final_adapter")