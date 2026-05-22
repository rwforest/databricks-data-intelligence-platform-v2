# Databricks notebook source
# MAGIC %md
# MAGIC # CholecSeg8k Fine-tuning with Qwen3-VL
# MAGIC
# MAGIC Fine-tune **Qwen3-VL-8B-Instruct** for surgical object detection/grounding on the CholecSeg8k dataset.
# MAGIC
# MAGIC **Features:**
# MAGIC - LoRA fine-tuning for memory efficiency
# MAGIC - 4-bit quantization via bitsandbytes
# MAGIC - Lazy loading from HuggingFace via HfFileSystem + zipfile

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Install Dependencies

# COMMAND ----------

# MAGIC %pip install transformers>=4.45.0 peft>=0.13.0 trl>=0.12.0 accelerate>=0.34.0 bitsandbytes>=0.44.0 huggingface_hub>=0.20.0 opencv-python>=4.8.0 hf_transfer flash-attn

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Imports and Configuration

# COMMAND ----------

import os
import zipfile
import random
from io import BytesIO
from dataclasses import dataclass
from typing import List, Dict, Any

import numpy as np
import cv2
from PIL import Image
from tqdm import tqdm

import torch
from torch.utils.data import Dataset

from transformers import (
    Qwen3VLForConditionalGeneration,
    AutoProcessor,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

from huggingface_hub import HfFileSystem

# COMMAND ----------

# MAGIC %md
# MAGIC ### Configuration

# COMMAND ----------

@dataclass
class TrainingConfig:
    model_name: str = "Qwen/Qwen3-VL-2B-Instruct"
    use_4bit: bool = True
    use_flash_attention: bool = True
    
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None
    
    output_dir: str = "/tmp/qwen3vl_cholecseg8k"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.1
    max_seq_length: int = 2048
    
    hf_dataset_repo: str = "minwoosun/CholecSeg8k"
    zip_path: str = "data/CholecSeg8k.zip"
    image_size: int = 384
    train_split: float = 0.8
    val_split: float = 0.1
    
    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]

config = TrainingConfig()

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Class Mappings

# COMMAND ----------

CLASS_NAME_MAPPING = {
    0: 'Black Background',
    1: 'Abdominal Wall',
    2: 'Liver',
    3: 'Gastrointestinal Tract',
    4: 'Fat',
    5: 'Grasper',
    6: 'Connective Tissue',
    7: 'Blood',
    8: 'Cystic Duct',
    9: 'L-hook Electrocautery',
    10: 'Gallbladder',
    11: 'Hepatic Vein',
    12: 'Liver Ligament',
}

# CholecSeg8k watershed masks use grayscale values (R=G=B)
# Complete mapping discovered by scanning all 8080 masks
GRAYSCALE_TO_CLASS = {
    0: 0,     # Black Background (125 pixels)
    5: 5,     # Grasper (13.8M pixels) - direct match
    11: 11,   # Hepatic Vein (714M pixels) - direct match
    12: 12,   # Liver Ligament (487M pixels) - direct match
    13: 3,    # Gastrointestinal Tract (62M pixels) - offset 13-10=3
    21: 2,    # Liver (704M pixels)
    22: 7,    # Blood (212M pixels) - offset 22-15=7
    23: 6,    # Connective Tissue (75M pixels)
    24: 4,    # Fat (13.9M pixels)
    25: 5,    # Grasper variant (1.2M pixels) - may overlap with 5
    31: 9,    # L-hook Electrocautery (80M pixels) - offset 31-22=9
    32: 1,    # Abdominal Wall (43M pixels)
    33: 8,    # Cystic Duct (314K pixels) - offset 33-25=8
    50: 10,   # Gallbladder (877M pixels)
    255: 0,   # White = ignore/background (24.5M pixels)
}

# Skip background classes
SKIP_CLASSES = {0}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Load Dataset from HuggingFace

# COMMAND ----------

fs = HfFileSystem()
zip_hf_path = f"datasets/{config.hf_dataset_repo}/{config.zip_path}"
print(f"Loading from: {zip_hf_path}")

# Open zip and get file list
zip_file = fs.open(zip_hf_path, "rb")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Get Image Pairs (lazy - just file names)

# COMMAND ----------

def get_image_pairs_from_zip(zip_file) -> List[tuple]:
    """Get list of image-mask pairs. Uses _endo.png -> _endo_watershed_mask.png"""
    pairs = []
    with zipfile.ZipFile(zip_file, 'r') as z:
        all_files = z.namelist()
        file_set = set(all_files)
        for fname in all_files:
            if fname.endswith("_endo.png") and "__MACOSX" not in fname:
                mask_fname = fname.replace("_endo.png", "_endo_watershed_mask.png")
                if mask_fname in file_set:
                    pairs.append((fname, mask_fname))
    print(f"Found {len(pairs)} image-mask pairs")
    return pairs

all_pairs = get_image_pairs_from_zip(zip_file)

# Split
random.seed(42)
random.shuffle(all_pairs)
n_train = int(len(all_pairs) * config.train_split)
n_val = int(len(all_pairs) * config.val_split)

train_pairs = all_pairs[:n_train]
val_pairs = all_pairs[n_train:n_train + n_val]
test_pairs = all_pairs[n_train + n_val:]

print(f"Split: {len(train_pairs)} train, {len(val_pairs)} val, {len(test_pairs)} test")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Helper Functions
# MAGIC 
# MAGIC ### Bounding Box Format
# MAGIC 
# MAGIC Bounding boxes use **normalized coordinates (0-1)** in the format:
# MAGIC ```
# MAGIC - ClassName: (x1, y1), (x2, y2)
# MAGIC ```
# MAGIC 
# MAGIC Where:
# MAGIC - `(x1, y1)` = **top-left corner** (normalized 0-1)
# MAGIC - `(x2, y2)` = **bottom-right corner** (normalized 0-1)
# MAGIC - Coordinates are **relative to image dimensions** (0.5 = center of image)
# MAGIC 
# MAGIC **Example output:**
# MAGIC ```
# MAGIC I can identify the following:
# MAGIC - Liver: (0.125, 0.200), (0.875, 0.650)
# MAGIC - Grasper: (0.450, 0.100), (0.550, 0.400)
# MAGIC ```

# COMMAND ----------

def extract_bboxes_from_watershed(mask: np.ndarray) -> Dict[int, List[float]]:
    """
    Extract bounding boxes from watershed mask.
    CholecSeg8k watershed masks use grayscale values where R=G=B.
    """
    h, w = mask.shape[:2]
    
    # Convert to single channel (masks are grayscale stored as RGB where R=G=B)
    if len(mask.shape) == 3:
        mask = mask[:, :, 0]
    
    boxes = {}
    for gray_value in np.unique(mask):
        # Map grayscale value to class ID
        if gray_value not in GRAYSCALE_TO_CLASS:
            continue
        
        class_id = GRAYSCALE_TO_CLASS[gray_value]
        if class_id in SKIP_CLASSES or class_id == 0:
            continue
            
        class_mask = (mask == gray_value).astype(np.uint8)
        if class_mask.sum() < 100:  # Skip very small regions
            continue
            
        contours, _ = cv2.findContours(class_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            pts = np.vstack(contours)
            x, y, bw, bh = cv2.boundingRect(pts)
            boxes[class_id] = [round(x/w, 3), round(y/h, 3), round((x+bw)/w, 3), round((y+bh)/h, 3)]
    
    return boxes


def format_response(boxes: Dict[int, List[float]]) -> str:
    if not boxes:
        return "No surgical objects detected."
    lines = ["I can identify the following:"]
    for cid, bbox in sorted(boxes.items()):
        lines.append(f"- {CLASS_NAME_MAPPING[cid]}: ({bbox[0]:.3f}, {bbox[1]:.3f}), ({bbox[2]:.3f}, {bbox[3]:.3f})")
    return "\n".join(lines)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Dataset Class (lazy loading)

# COMMAND ----------

class CholecSeg8kDataset(Dataset):
    PROMPTS = [
        "Identify all surgical objects in this laparoscopic image.",
        "What instruments and organs are visible? Provide their locations.",
        "Detect objects in this cholecystectomy image.",
    ]
    
    def __init__(self, pairs: List[tuple], zip_path: str, fs: HfFileSystem, processor, image_size: int = 384):
        self.pairs = pairs
        self.zip_path = zip_path
        self.fs = fs
        self.processor = processor
        self.image_size = image_size
    
    def __len__(self):
        return len(self.pairs)
    
    def __getitem__(self, idx) -> Dict[str, Any]:
        img_fname, mask_fname = self.pairs[idx]
        
        with self.fs.open(self.zip_path, "rb") as zf:
            with zipfile.ZipFile(zf, 'r') as z:
                img = Image.open(BytesIO(z.read(img_fname))).convert("RGB")
                img = img.resize((self.image_size, self.image_size), Image.LANCZOS)
                
                mask = np.array(Image.open(BytesIO(z.read(mask_fname))))
                mask = cv2.resize(mask, (self.image_size, self.image_size), interpolation=cv2.INTER_NEAREST)
        
        boxes = extract_bboxes_from_watershed(mask)
        prompt = random.choice(self.PROMPTS)
        response = format_response(boxes)
        
        messages = [
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]},
            {"role": "assistant", "content": [{"type": "text", "text": response}]}
        ]
        return {"messages": messages, "images": [img]}

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Load Model

# COMMAND ----------

def setup_model(config):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    ) if config.use_4bit else None
    
    model_kwargs = {
        "quantization_config": bnb_config,
        "device_map": "auto",
        "torch_dtype": torch.bfloat16,
        "trust_remote_code": True,
    }
    if config.use_flash_attention:
        model_kwargs["attn_implementation"] = "flash_attention_2"
    
    model = Qwen3VLForConditionalGeneration.from_pretrained(config.model_name, **model_kwargs)
    processor = AutoProcessor.from_pretrained(config.model_name, trust_remote_code=True)
    
    if config.use_4bit:
        model = prepare_model_for_kbit_training(model)
    
    lora_config = LoraConfig(
        r=config.lora_r, lora_alpha=config.lora_alpha, lora_dropout=config.lora_dropout,
        target_modules=config.lora_target_modules, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, processor

model, processor = setup_model(config)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9. Create Datasets

# COMMAND ----------

train_dataset = CholecSeg8kDataset(train_pairs, zip_hf_path, fs, processor, config.image_size)
val_dataset = CholecSeg8kDataset(val_pairs, zip_hf_path, fs, processor, config.image_size)
test_dataset = CholecSeg8kDataset(test_pairs, zip_hf_path, fs, processor, config.image_size)

print(f"Datasets: {len(train_dataset)} train, {len(val_dataset)} val, {len(test_dataset)} test")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10. Collate Function

# COMMAND ----------

def collate_fn(batch):
    texts, images = [], []
    for item in batch:
        texts.append(processor.apply_chat_template(item["messages"], tokenize=False, add_generation_prompt=False))
        images.extend(item["images"])
    
    inputs = processor(text=texts, images=images, padding=True, truncation=True, max_length=config.max_seq_length, return_tensors="pt")
    inputs["labels"] = inputs["input_ids"].clone()
    return inputs

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11. Train

# COMMAND ----------

training_args = SFTConfig(
    output_dir=config.output_dir,
    num_train_epochs=config.num_train_epochs,
    per_device_train_batch_size=config.per_device_train_batch_size,
    gradient_accumulation_steps=config.gradient_accumulation_steps,
    learning_rate=config.learning_rate,
    warmup_ratio=config.warmup_ratio,
    logging_steps=10,
    logging_first_step=True,
    log_level="info",
    save_strategy="epoch",
    eval_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    # max_seq_length=config.max_seq_length,
    remove_unused_columns=False,
    report_to=["mlflow"],
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=collate_fn,
    processing_class=processor,
)

# COMMAND ----------

# Add callback to print loss to notebook (Databricks sometimes needs this)
from transformers import TrainerCallback, EarlyStoppingCallback

class PrintLossCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if logs:
            step = state.global_step
            loss = logs.get("loss", logs.get("train_loss", "N/A"))
            print(f"Step {step}: loss = {loss}")

trainer.add_callback(PrintLossCallback())

# Early stopping: stop if eval_loss doesn't improve for 2 evaluations
trainer.add_callback(EarlyStoppingCallback(early_stopping_patience=2))

# COMMAND ----------

trainer.train()

# COMMAND ----------

trainer.save_model(config.output_dir)
processor.save_pretrained(config.output_dir)
print(f"Model saved to {config.output_dir}")

# COMMAND ----------

trainer.save_model('/Volumes/unitygo/diabetes_cure/surgical_vlm/final_full')
processor.save_pretrained('/Volumes/unitygo/diabetes_cure/surgical_vlm/final_full')

# COMMAND ----------

# MAGIC %md
# MAGIC ## 12. Test Inference

# COMMAND ----------

sample = test_dataset[0]
img = sample["images"][0]

messages = [{"role": "user", "content": [{"type": "image", "image": img}, {"type": "text", "text": "Identify all surgical objects."}]}]
inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt").to(model.device)

with torch.no_grad():
    out = model.generate(**inputs, max_new_tokens=256)
print(processor.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 13. Full Test Set Evaluation
# MAGIC 
# MAGIC Run comprehensive evaluation on the **full test set** with Precision, Recall, and Mean IoU metrics.

# COMMAND ----------

import re
from typing import Tuple

def parse_bbox_response(text: str) -> List[Tuple[str, List[float]]]:
    """
    Parse bounding boxes from model response.
    Format: '- ClassName: (x1, y1), (x2, y2)'
    Returns list of (class_name, [x1, y1, x2, y2]) tuples.
    """
    boxes = []
    pattern = r'-\s+([^:]+):\s+\(([\d.]+),\s*([\d.]+)\),\s*\(([\d.]+),\s*([\d.]+)\)'
    for match in re.finditer(pattern, text or ""):
        class_name = match.group(1).strip()
        coords = [float(match.group(i)) for i in range(2, 6)]
        boxes.append((class_name, coords))
    return boxes

def compute_iou(box1: List[float], box2: List[float]) -> float:
    """Compute Intersection over Union (IoU) for normalized coords [x1, y1, x2, y2]."""
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    x1_i = max(x1_1, x1_2)
    y1_i = max(y1_1, y1_2)
    x2_i = min(x2_1, x2_2)
    y2_i = min(y2_1, y2_2)
    
    if x2_i <= x1_i or y2_i <= y1_i:
        return 0.0
    
    intersection = (x2_i - x1_i) * (y2_i - y1_i)
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0

def evaluate_detection(predictions: List[str], ground_truths: List[str], iou_threshold: float = 0.5) -> Dict[str, float]:
    """Evaluate detection performance with precision, recall, IoU."""
    total_tp, total_fp, total_fn = 0, 0, 0
    ious = []
    
    for pred_text, gt_text in zip(predictions, ground_truths):
        pred_boxes = parse_bbox_response(pred_text)
        gt_boxes = parse_bbox_response(gt_text)
        
        matched_gt = set()
        for pred_class, pred_box in pred_boxes:
            best_iou, best_idx = 0.0, -1
            for gt_idx, (gt_class, gt_box) in enumerate(gt_boxes):
                if gt_idx in matched_gt:
                    continue
                if pred_class == gt_class:
                    iou = compute_iou(pred_box, gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_idx = gt_idx
            
            if best_iou >= iou_threshold and best_idx >= 0:
                total_tp += 1
                matched_gt.add(best_idx)
                ious.append(best_iou)
            else:
                total_fp += 1
        
        total_fn += len(gt_boxes) - len(matched_gt)
    
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    mean_iou = sum(ious) / len(ious) if ious else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "mean_iou": mean_iou,
        "true_positives": total_tp,
        "false_positives": total_fp,
        "false_negatives": total_fn,
    }

# COMMAND ----------

# DBTITLE 1,Run Full Test Set Evaluation
print("=" * 70)
print("📊 FULL TEST SET EVALUATION")
print("=" * 70)
print(f"Test samples: {len(test_dataset)}")

model.eval()
predictions = []
ground_truths = []

# Run inference on ALL test samples
with torch.no_grad():
    for idx in tqdm(range(len(test_dataset)), desc="Evaluating"):
        try:
            sample = test_dataset[idx]
            img = sample["images"][0]
            
            # Ground truth from dataset
            gt_messages = sample["messages"]
            gt_text = gt_messages[1]["content"][0]["text"]  # Assistant response
            
            # Inference
            messages = [{"role": "user", "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": "Identify all surgical objects in this laparoscopic image."}
            ]}]
            inputs = processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True, 
                return_dict=True, return_tensors="pt"
            ).to(model.device)
            
            output_ids = model.generate(**inputs, max_new_tokens=256)
            pred_text = processor.decode(output_ids[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            
            predictions.append(pred_text)
            ground_truths.append(gt_text)
            
        except Exception as e:
            print(f"Error at sample {idx}: {e}")
            continue

# Calculate overall metrics
metrics = evaluate_detection(predictions, ground_truths)

print("\n" + "=" * 70)
print("📊 FULL TEST SET RESULTS")
print("=" * 70)
print(f"\n📈 Overall Metrics (N={len(predictions)} samples):")
print(f"   Precision:  {metrics['precision']:.4f}")
print(f"   Recall:     {metrics['recall']:.4f}")
print(f"   F1 Score:   {metrics['f1_score']:.4f}")
print(f"   Mean IoU:   {metrics['mean_iou']:.4f}")
print(f"\n   TP: {metrics['true_positives']}, FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}")

# COMMAND ----------

# DBTITLE 1,Per-Class Metrics
print("\n📊 Per-Class Metrics:")
print("-" * 70)
print(f"{'Class':<25} {'Precision':>10} {'Recall':>10} {'IoU':>10} {'TP':>6} {'FP':>6} {'FN':>6}")
print("-" * 70)

class_names = [CLASS_NAME_MAPPING[i] for i in CLASS_NAME_MAPPING if i not in SKIP_CLASSES]

class_metrics = {}
for cls in class_names:
    cls_tp, cls_fp, cls_fn, cls_ious = 0, 0, 0, []
    
    for pred_text, gt_text in zip(predictions, ground_truths):
        pred_boxes = [(c, b) for c, b in parse_bbox_response(pred_text) if c == cls]
        gt_boxes = [(c, b) for c, b in parse_bbox_response(gt_text) if c == cls]
        
        matched_gt = set()
        for _, pred_box in pred_boxes:
            best_iou, best_idx = 0.0, -1
            for idx, (_, gt_box) in enumerate(gt_boxes):
                if idx in matched_gt:
                    continue
                iou = compute_iou(pred_box, gt_box)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = idx
            
            if best_iou >= 0.5 and best_idx >= 0:
                cls_tp += 1
                matched_gt.add(best_idx)
                cls_ious.append(best_iou)
            else:
                cls_fp += 1
        
        cls_fn += len(gt_boxes) - len(matched_gt)
    
    if cls_tp + cls_fp + cls_fn > 0:
        cls_precision = cls_tp / (cls_tp + cls_fp) if (cls_tp + cls_fp) > 0 else 0.0
        cls_recall = cls_tp / (cls_tp + cls_fn) if (cls_tp + cls_fn) > 0 else 0.0
        cls_mean_iou = sum(cls_ious) / len(cls_ious) if cls_ious else 0.0
        
        class_metrics[cls] = {"precision": cls_precision, "recall": cls_recall, "mean_iou": cls_mean_iou, "tp": cls_tp, "fp": cls_fp, "fn": cls_fn}
        print(f"{cls:<25} {cls_precision:>10.4f} {cls_recall:>10.4f} {cls_mean_iou:>10.4f} {cls_tp:>6} {cls_fp:>6} {cls_fn:>6}")

print("=" * 70)

# COMMAND ----------

# DBTITLE 1,Diagnostic: Class Distribution Analysis
from collections import Counter

print("\n" + "=" * 70)
print("🔍 DIAGNOSTIC: CLASS DISTRIBUTION ANALYSIS")
print("=" * 70)

# Count classes in ground truth
gt_class_counts = Counter()
for gt_text in ground_truths:
    for cls, _ in parse_bbox_response(gt_text):
        gt_class_counts[cls] += 1

# Count classes in predictions
pred_class_counts = Counter()
for pred_text in predictions:
    for cls, _ in parse_bbox_response(pred_text):
        pred_class_counts[cls] += 1

print("\n📊 Ground Truth Class Distribution (what's actually in test set):")
print("-" * 50)
if gt_class_counts:
    for cls, count in gt_class_counts.most_common():
        pct = count / sum(gt_class_counts.values()) * 100
        bar = "█" * int(pct / 2)
        print(f"  {cls:<25} {count:>5} ({pct:>5.1f}%) {bar}")
else:
    print("  ⚠️ No bounding boxes found in ground truth!")

print(f"\n  Total GT boxes: {sum(gt_class_counts.values())}")
print(f"  Unique classes in GT: {len(gt_class_counts)}")

print("\n📊 Model Predictions Distribution (what model is detecting):")
print("-" * 50)
if pred_class_counts:
    for cls, count in pred_class_counts.most_common():
        pct = count / sum(pred_class_counts.values()) * 100
        bar = "█" * int(pct / 2)
        print(f"  {cls:<25} {count:>5} ({pct:>5.1f}%) {bar}")
else:
    print("  ⚠️ No bounding boxes detected by model!")

print(f"\n  Total predicted boxes: {sum(pred_class_counts.values())}")
print(f"  Unique classes predicted: {len(pred_class_counts)}")

# Show missing classes
all_class_names = set(CLASS_NAME_MAPPING.values()) - {"Black Background"}
gt_classes = set(gt_class_counts.keys())
pred_classes = set(pred_class_counts.keys())

missing_in_gt = all_class_names - gt_classes
missing_in_pred = gt_classes - pred_classes

if missing_in_gt:
    print(f"\n⚠️ Classes MISSING from ground truth (not in test set):")
    for cls in missing_in_gt:
        print(f"   - {cls}")

if missing_in_pred:
    print(f"\n⚠️ Classes in GT but NOT detected by model:")
    for cls in missing_in_pred:
        print(f"   - {cls} (GT has {gt_class_counts.get(cls, 0)} instances)")

print("=" * 70)

# Show a few example predictions vs ground truths
print("\n📋 Sample Predictions vs Ground Truth (first 3):")
print("-" * 70)
for i in range(min(3, len(predictions))):
    print(f"\n[Sample {i+1}]")
    print(f"GT: {ground_truths[i][:200]}...")
    print(f"Pred: {predictions[i][:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 14. Full Dataset Class Distribution Analysis
# MAGIC 
# MAGIC Scan the **entire CholecSeg8k dataset** to understand the true class distribution.

# COMMAND ----------

# DBTITLE 1,Scan Full Dataset for Class Distribution
from collections import Counter
import zipfile

print("=" * 70)
print("📊 FULL DATASET CLASS DISTRIBUTION ANALYSIS")
print("=" * 70)
print("Scanning ALL images in CholecSeg8k dataset...")

# Counters
class_image_count = Counter()  # How many images contain each class
class_pixel_count = Counter()  # Total pixels per class (proxy for area)
total_images = 0

fs = HfFileSystem()
zip_hf_path = f"datasets/{config.hf_dataset_repo}/{config.zip_path}"

with fs.open(zip_hf_path, "rb") as zf:
    with zipfile.ZipFile(zf, 'r') as z:
        all_files = z.namelist()
        mask_files = [f for f in all_files if f.endswith("_endo_watershed_mask.png") and "__MACOSX" not in f]
        
        print(f"Found {len(mask_files)} mask files to analyze...")
        
        for i, mask_fname in enumerate(tqdm(mask_files, desc="Scanning masks")):
            try:
                mask = np.array(Image.open(BytesIO(z.read(mask_fname))))
                total_images += 1
                
                # Convert RGB to grayscale (R=G=B in CholecSeg8k watershed masks)
                if len(mask.shape) == 3:
                    mask = mask[:, :, 0]
                
                # Map grayscale values to class IDs
                for gray_value in np.unique(mask):
                    if gray_value in GRAYSCALE_TO_CLASS:
                        class_id = GRAYSCALE_TO_CLASS[gray_value]
                        if class_id != 0 and class_id in CLASS_NAME_MAPPING:
                            class_name = CLASS_NAME_MAPPING[class_id]
                            class_image_count[class_name] += 1
                            class_pixel_count[class_name] += np.sum(mask == gray_value)
                        
            except Exception as e:
                continue

print(f"\n✅ Scanned {total_images} images")
print("\n" + "=" * 70)
print("📊 CLASS DISTRIBUTION (by number of images containing class):")
print("-" * 70)
print(f"{'Class':<25} {'Images':>8} {'% Images':>10} {'Total Pixels':>15}")
print("-" * 70)

for cls, count in class_image_count.most_common():
    pct = count / total_images * 100
    pixels = class_pixel_count[cls]
    bar = "█" * int(pct / 2)
    print(f"{cls:<25} {count:>8} {pct:>9.1f}% {pixels:>15,} {bar}")

# Check which classes are truly rare or missing
print("\n" + "=" * 70)
print("📋 CLASS RARITY ANALYSIS:")
print("-" * 70)

all_possible = set(CLASS_NAME_MAPPING.values()) - {"Black Background"}
found_classes = set(class_image_count.keys())
missing = all_possible - found_classes

if missing:
    print("❌ Classes NOT FOUND in dataset:")
    for cls in missing:
        print(f"   - {cls}")
else:
    print("✅ All classes found in dataset")

# Classify by rarity
print("\n🔸 Rare classes (<5% of images):")
for cls, count in class_image_count.items():
    pct = count / total_images * 100
    if pct < 5:
        print(f"   - {cls}: {count} images ({pct:.1f}%)")

print("\n🔸 Common classes (>20% of images):")
for cls, count in class_image_count.items():
    pct = count / total_images * 100
    if pct > 20:
        print(f"   - {cls}: {count} images ({pct:.1f}%)")

print("=" * 70)

# COMMAND ----------

# DBTITLE 1,Debug: Discover Actual Colors in Masks
print("=" * 70)
print("🔍 DEBUG: DISCOVERING ALL UNIQUE GRAYSCALE VALUES")
print("=" * 70)
print("Scanning 100 masks to find all unique grayscale values...")

all_gray_values = Counter()
sample_masks = 100

fs = HfFileSystem()
zip_hf_path = f"datasets/{config.hf_dataset_repo}/{config.zip_path}"

with fs.open(zip_hf_path, "rb") as zf:
    with zipfile.ZipFile(zf, 'r') as z:
        all_files = z.namelist()
        mask_files = [f for f in all_files if f.endswith("_endo_watershed_mask.png") and "__MACOSX" not in f][:sample_masks]
        
        for mask_fname in tqdm(mask_files, desc="Scanning masks"):
            mask = np.array(Image.open(BytesIO(z.read(mask_fname))))
            
            # Convert to grayscale (take first channel since R=G=B)
            if len(mask.shape) == 3:
                mask = mask[:, :, 0]
            
            # Count pixels for each grayscale value
            for val in np.unique(mask):
                all_gray_values[int(val)] += np.sum(mask == val)

print("\n" + "=" * 70)
print("📊 ALL UNIQUE GRAYSCALE VALUES FOUND:")
print("-" * 70)
print(f"{'Value':<10} {'Total Pixels':>15} {'Mapped to Class':>25}")
print("-" * 70)

for val, count in sorted(all_gray_values.items()):
    if val in GRAYSCALE_TO_CLASS:
        class_id = GRAYSCALE_TO_CLASS[val]
        class_name = CLASS_NAME_MAPPING.get(class_id, "Unknown")
        status = f"✅ {class_id} ({class_name})"
    else:
        status = "❌ NOT MAPPED"
    print(f"{val:<10} {count:>15,} {status:>25}")

print("\n" + "=" * 70)
print("💡 Copy the grayscale values above into GRAYSCALE_TO_CLASS mapping!")
print("=" * 70)