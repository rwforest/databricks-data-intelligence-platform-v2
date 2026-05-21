# Databricks Data Intelligence Platform & GenAI

Welcome to the repository for the **GenAI Book**. This repository contains the markdown chapters detailing enterprise architectures, Agentic AI, LangGraph, and MLflow 3.0 on the Databricks Platform.

## 📖 Chapter Directory and Summaries

Below is an AI-optimized index of all chapters in this book, including a brief summary (TL;DR) and the core topics covered in each chapter.

### [Databricks Data Intelligence Platform](./03-Databricks_Data_Intelligence_Platform.md)
### [Introduction](./08-Introduction.md)
**TL;DR:** The transition from passive data storage to active, reasoning AI systems requires a fundamental shift in architecture. The 12 canonical components of an end-to-end AI system diagram presented in Databricks’ AI Security Framework outline this modern blueprint—a framework connecting raw data directly to real-world inference.

**Topics Covered:**
- 1\. Navigating the Data Intelligence Architecture
- 2\. The Foundation and the Future
- 3\. Building and Evaluating Agentic AI
- 4\. Secure, Scalable Infrastructure
- 5\. Data Engineering and Governance
- 6\. Operations and Real-World Execution

### [1\. Databricks Platform: From Lakehouse to Data Intelligence](./13-1._Databricks_Platform__From_Lakehouse_to_Data_Intelligence.md)
**TL;DR:** The intensifying pace of digital transformation has led companies to amass increasing volumes of diverse data from various sources. This data explosion carries enormous potential for organizations to uncover transformative insights to guide innovation and decision-making through advanced analytics.

**Topics Covered:**
- Data Platforms: Historical Perspective
- Emergence of the Lakehouse
- What Is a Lakehouse?
- What Is the Databricks Lakehouse?
- Key Features of the Databricks Lakehouse Platform
- Introducing the Databricks Data Intelligence Platform
- From Databricks to Agent Bricks
- Conclusion

### [2\. Generative AI on Databricks: Foundations, Capabilities, and Use Cases](./14-2._Generative_AI_on_Databricks__Foundations,_Capabilities,_and_Use_Cases.md)
**TL;DR:** Ever since ChatGPT was released to the public, there has been no shortage of interest in chatbots or generative artificial intelligence (GenAI). But what exactly is GenAI, and how does Databricks come into the picture? And how can it help organizations deploy their own chatbot or develop their own GenAI applications? In this chapter, we will first learn the concepts around GenAI. We will then discuss how Databricks and MosaicML, now an integral part of Databricks, work together to transform t...

**Topics Covered:**
- What Is Generative AI?
- Databricks Generative AI
- The GenAI Journey
- Prompt Engineering
- Retrieval-Augmented Generation (RAG)
- Testing the Vector Search Index
- Mosaic AI Fine-Tuning API
- Pre-Training
- GenAI Pricing
- Conclusion

### [3\. Composable Agents with Agent Bricks: From Prototype to Production](./15-3._Composable_Agents_with_Agent_Bricks__From_Prototype_to_Production.md)
**TL;DR:** In the rapidly evolving world of Generative AI (GenAI), there is an elephant in the room (Figure [3-1](A625176_2_En_3_Chapter)). While the potential of GenAI is immense, according to a 2024 Forbes report, 90% of GenAI projects never reach production.[1](A625176_2_En_3_Chapter) Further, in August 2025, an MIT survey states that 95% of GenAI projects don’t see a good return on investment.[2](A625176_2_En_3_Chapter) This predicament still holds true today in 2026\. The challenges often boil down...

**Topics Covered:**
- Agent Bricks: Databricks’ No-Code Solution for Production Agents
- An Agent Bricks Walkthrough
- Custom LLM
- Conclusion

### [4\. Agent Bricks Deep Dive: Retrieval, Reasoning, and Tooling Architectures](./16-4._Agent_Bricks_Deep_Dive__Retrieval,_Reasoning,_and_Tooling_Architectures.md)
**TL;DR:** In Chapter [3](./15-3._Composable_Agents_with_Agent_Bricks__From_Prototype_to_Production.md), we discussed the first two use cases for Agent Bricks: Information Extraction and Custom LLM. To recap, Agent Bricks is a UI-based product that packs the best of Databricks research behind the scenes, so we don’t need to learn or keep up with the latest techniques to make our GenAI solutions work with our data. There are two different types of bricks: generative bricks and non-generative bricks.

**Topics Covered:**
- Retrieval Augmented Generation: The Knowledge Assistant
- Similarity Search: The Magic Behind the Scenes
- Vector Search Infrastructure
- A Practical Example for RAG: Using Unstructured Data
- Quality Improvement
- Conclusion

### [5\. Agentic AI Design Patterns for Enterprise Systems](./17-5._Agentic_AI_Design_Patterns_for_Enterprise_Systems.md)
**TL;DR:** In the previous chapters, we have discussed different types of agents, including Information Extraction, Custom LLM, and Knowledge Assistant. These are great use cases, but at the same time, they are isolated for a specific use case. This is obviously by design because they are built for domain-specific purposes. What if we can chain all these agents together to create a very powerful system? This is called an Agentic AI workflow. We will first discuss the various Agentic AI design patterns a...

**Topics Covered:**
- A Case Study
- Deep Dive into Agentic Patterns
- Conclusion

### [6\. Databricks As an Agentic Platform: Orchestration, Context, and Control](./18-6._Databricks_As_an_Agentic_Platform__Orchestration,_Context,_and_Control.md)
**TL;DR:** In the previous chapters, we learned about the new Agent Bricks offerings. Since 2023, with the rise of GenAI and LLMs, Databricks has integrated them into its platform. The Databricks data intelligence platform (see Figure [6-1](A625176_2_En_6_Chapter)) combines the lakehouse platform and AI/LLMs to add the “data intelligence” engine that understands the uniqueness of your data and uses that understanding across everything in the platform. However, tools are increasingly designed for AI Agen...

**Topics Covered:**
- Data Intelligence
- Deep Dive into Data Intelligence
- Conclusion

### [7\. Quality Tuning and Evaluation with Agent Bricks](./19-7._Quality_Tuning_and_Evaluation_with_Agent_Bricks.md)
**TL;DR:** So far, we have discussed how to create agents with Agent Bricks; it’s a new paradigm for UI-driven AI. It is understandable in a user interface-driven framework that all we are seeing are spinning circles or progress bars. Scientists and engineers alike often want more details, and companies that adopt the latest AI products also need to evaluate the pros and cons of bringing in new technology, since they can no longer analyze the underlying model internals to understand how things work. How...

**Topics Covered:**
- Evaluating Information Extraction and Custom LLM
- Evaluation-Driven Development with MLflow
- Manual Evaluation
- Systematic Evaluation
- Monitoring
- Dataset
- Agent Learning from Human Feedback (ALHF) in Knowledge Assistant
- Extending the Paradigm to the Multi-Agent Supervisor
- Conclusion

### [8\. Lakebase: The OLTP Engine for Intelligent Applications](./20-8._Lakebase__The_OLTP_Engine_for_Intelligent_Applications.md)
**TL;DR:** Databricks is the most optimized platform for data and analytics, including Online Analytical Processing (OLAP). However, several use cases require sub-second data latency, in which case Lakehouse data must be moved to a low-latency online transactional processing (OLTP) database to serve online applications. In the past, organizations have adopted a strategy of copying data from Delta Lake into a separate OLTP database like Azure SQL Database, Amazon Aurora, or GCP Cloud SQL. The purpose was...

**Topics Covered:**
- What Is Databricks Lakebase?
- Getting Started with Lakebase
- Welcome to the Lakebase Interface
- Lakebase Core Features
- Managed Data Synchronization
- Lakebase: Before and After
- Conclusion

### [9\. Building Security-First, Production-Grade Databricks Apps](./21-9._Building_Security-First,_Production-Grade_Databricks_Apps.md)
**TL;DR:** In the previous chapters, we learned about the Databricks Lakehouse, which essentially means storing all your data in open storage in an open format with Unity Catalog providing a single governance layer. Databricks provides features that support all use cases, including data engineering, data science, streaming, and warehousing. Since 2023, with the rise of GenAI and LLMs, Databricks has integrated them into its platform. The Databricks data intelligence platform (see Figure [9-1](A625176_2_...

**Topics Covered:**
- Building Apps Where Your Data Lives
- Core Architecture: A Serverless, Containerized Foundation
- The Serverless Compute Plane
- Isolation and Security by Design
- The Runtime Environment
- Unity Catalog As the Governance Layer
- App Authorization (Service Principal Model)
- User Authorization (“On-Behalf-Of” Model)
- From Code to Production
- Deployment Using Declarative Automation Bundles
- A CI/CD Workflow Example
- Auditing and Observability
- Integrating with External Monitoring Tools
- Strategic Use Cases: Beyond Dashboards
- Conclusion: The Future of the Full-Stack Data Intelligence Platform

### [10\. AI Runtime: Elastic Compute for AI Workloads](./22-10._AI_Runtime__Elastic_Compute_for_AI_Workloads.md)
**TL;DR:** When it comes to graphics processing units (GPUs), people undoubtedly think of Copilot or ChatGPT. No doubt that large language models are powered by a massive number of GPUs, and we will also discuss AI models in this chapter. One lesser-known limitation is the limited support for training traditional machine learning models on serverless CPU compute. The reason is that serverless is using the Spark Connect architecture. As shown in Figure [10-1](A625176_2_En_10_Chapter), the Spark Connect a...

**Topics Covered:**
- AI (Serverless GPU) Runtime
- Serverless API at a Glance
- Conclusion

### [11\. MLflow 3 and the GenAI Agents](./23-11._MLflow_3_and_the_GenAI_Agents.md)
**TL;DR:** Since launching in 2018, MLflow has been one of the major open-source tools in managing machine learning lifecycles. In the previous edition, we discussed the machine learning lifecycle and how to use MLflow to track experiments. Since MLflow 3.0, the community as well as Databricks has successfully evolved MLflow to support various GenAI use cases, from the basics like prompt versioning to agent tracing to custom judges.

**Topics Covered:**
- Tracing
- Evaluation
- Creating Judges (Scorers) from the MLflow UI
- Review App: Labeling Session
- Hello Prompt Optimization, Goodbye, Prompt Management
- Conclusion

### [12\. Real-Time Intelligence with Spark Structured Streaming](./24-12._Real-Time_Intelligence_with_Spark_Structured_Streaming.md)
**TL;DR:** Many people think of streaming as some very low-latency continuous real-time events like X, formerly Twitter, feeds or IoT devices. While that was the original use case, streaming has evolved over the years to allow integration with other non-real-time tables and as a useful technique to enable incremental processing for batch pipelines. In this chapter, we will first go back in time to visit Spark Streaming; then we will look at the latest Databricks Structured Streaming engine. They are lar...

**Topics Covered:**
- The Foundation of Structured Streaming
- Structured Streaming
- Spark Real-Time Mode
- Triggers
- Output Modes
- Windowed Grouped Aggregation
- State Management
- Late-Arrival Handling: Watermark
- Auto Loader
- Spark Real-Time Mode Deep Dive
- Advanced State Management
- Use Case: Real-Time Stock Tracking
- Structured Streaming Best Practices
- Real-Time Machine Learning
- Online Store
- Conclusion

### [13\. Lakeflow Connect: Data Ingestion for the Lakehouse](./25-13._Lakeflow_Connect__Data_Ingestion_for_the_Lakehouse.md)
**TL;DR:** Organizations have a wealth of information siloed in various data sources. It could be relational databases, on-premises data warehouses, big data storage systems like Hadoop, ERP/CRM systems, or real-time streaming sources. Many analytics use cases require not only efficient processing of this data but also a unified approach to produce meaningful reports and predictions. To start this journey, organizations need to ingest data from different sources into a single location. In this chapter, ...

**Topics Covered:**
- Cloud Ingestion
- Files Ingestion
- Beyond Ingestion
- Conclusion

### [14\. Open Data Governance with Unity Catalog](./26-14._Open_Data_Governance_with_Unity_Catalog.md)
**TL;DR:** Data is one of an organization’s most significant assets. An important determinant of a company’s performance and growth is how well its data is handled regarding quality, management, and ownership. Organizations today, especially with ever-expanding use cases for GenAI, face increasingly stringent data privacy regulations. Nonetheless, the reliance on data is increasing as organizations look to help optimize operations and drive business decision-making. Therefore, they are looking for data ...

**Topics Covered:**
- What Is Databricks Unity Catalog?
- Unity Catalog: Before and After
- Unity Catalog Hierarchy
- Unity Catalog Admin Roles
- Organizing Data in Unity Catalog
- Key Features of Unity Catalog
- Data Lineage
- Data Access Auditing
- Data Search and Discovery
- Row-Level Security and Column-Level Masking
- Delta Sharing
- Delta Sharing: Iceberg Version
- Conclusion

### [15\. Delta Lake: The Foundation of Reliable Data and AI](./27-15._Delta_Lake__The_Foundation_of_Reliable_Data_and_AI.md)
**TL;DR:** In this chapter, we will examine a crucial aspect of the lakehouse paradigm: the data storage format. As discussed in Chapter [1](./13-1._Databricks_Platform__From_Lakehouse_to_Data_Intelligence.md), the ideal storage format for a lakehouse is one that provides similar data management and performance features of a data warehouse but is an open format and built on top of cloud data storage. Delta Lake is a storage protocol that exactly fits the requirements. Delta Lake is an open, performant s...

**Topics Covered:**
- The Challenges of Other Formats
- What Is Delta Lake?
- Transaction Log: Single Source of Truth
- Delta Lake: Medallion Architecture
- Delta Lake Key Features
- Time Travel
- Clone Delta Tables
- Generated Column
- Change Data Feed
- Universal Format
- Delta Optimization
- Liquid Clustering
- Working with Liquid Clustering
- Current Limitations
- Predictive I/O
- Delta Lake 4.0: The Future of Open Data Lakehouses
- Delta Sharing
- Conclusion

### [16\. Lakeflow Declarative Pipelines: Managing Data and AI Workflows](./28-16._Lakeflow_Declarative_Pipelines__Managing_Data_and_AI_Workflows.md)
**TL;DR:** It is no secret that well-curated, trustworthy data is the foundation of the lakehouse architecture. Organizations need clean, fresh, and reliable data to drive their analytics and data science projects, which in turn help them make decisions for key business initiatives.

**Topics Covered:**
- What Are Declarative Pipelines?
- Lakeflow Designer
- Logging and Monitoring
- Conclusion

### [17\. Data Warehousing with Databricks SQL](./29-17._Data_Warehousing_with_Databricks_SQL.md)
**TL;DR:** If you’re a data analyst who primarily uses SQL to write queries and reports and create comprehensive dashboards for analysis using your favorite business intelligence (BI) tools, Databricks SQL (DBSQL) provides a comprehensive environment for running ad hoc queries and creating dashboards on data stored in your data lakehouse.

**Topics Covered:**
- What Is Databricks SQL?
- SQL Warehouses
- Constraints in DBSQL
- Streaming Tables and Materialized Views
- Materialized Views
- Connect Power BI Desktop to Databricks
- Conclusion

### [18\. Databricks Pricing and Observability Using System Tables](./30-18._Databricks_Pricing_and_Observability_Using_System_Tables.md)
**TL;DR:** In this chapter, we will investigate how pricing for running workloads on Databricks works. It is important to understand how Databricks calculates the cost of your workloads. We will see what factors determine the pricing model and recommend which compute SKU should be used for running your specific workloads.

**Topics Covered:**
- Costs Associated with the Databricks Platform
- Cloud Infrastructure Costs
- Databricks Pricing
- Databricks Cost Management Best Practices
- Databricks Observability: System Tables
- Conclusion

### [19\. From Ideation to Creation: Building Intelligent Products with GenAI](./31-19._From_Ideation_to_Creation__Building_Intelligent_Products_with_GenAI.md)
**TL;DR:** In the last edition, we created a chatbot for understanding diabetes; you are encouraged to check out the chapter. Despite the chatbot now being achievable with Agent Bricks’ Knowledge Assistant, it’s still critical to understand the end-to-end workflow. In this second edition, we will walk through a practical healthcare case study in which we will attempt to fine-tune a vision language model (VLM), a.k.a. Qwen3-VL-2B-Instruct, to watch real surgery videos and generate post-surgical reports t...

**Topics Covered:**
- The Problem Statement
- End-to-End Architecture

## 💻 Code Extracts

For an exhaustive mapping of all 91 code snippets, SQL pipelines, and Python LangGraph architectures used in this book, please see the [code_map.csv](./code_map.csv). This provides language metadata, captions, and the raw code blocks for easy retrieval.
