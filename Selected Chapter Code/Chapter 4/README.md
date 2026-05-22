# LangGraph Tutorial Collection

A comprehensive collection of LangGraph examples using ChatDatabricks, optimized for LangGraph Studio with Chat mode compatibility.

## 🚀 Quick Start

1. **Clone and navigate to the tutorial directory**
   ```bash
   cd langgraph_tutorial
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys
   ```

3. **Run with LangGraph Studio**
   ```bash
   langgraph dev
   ```

## 📋 Available Graphs

| Graph | Description | Pattern | Use Case |
|-------|-------------|---------|----------|
| `chatbot_with_tools` | Tool-enabled chatbot | Basic Tool Use | Simple Q&A with search |
| `reflection` | Essay writing with critique | Reflection | Content creation with self-improvement |
| `plan_and_execute` | Multi-step planning agent | Plan-Execute | Complex multi-step tasks |
| `hierarchical_agent_teams` | Multi-level agent teams | Hierarchical Multi-Agent | Research + document writing |
| `multi_agent_collaboration` | Researcher + Analyst team | Collaborative Multi-Agent | Data research and analysis |
| `react_agent` | Reasoning and Acting agent | ReAct | Step-by-step problem solving |

## 🛠️ Setup Requirements

### Required API Keys

- **TAVILY_API_KEY**: For web search functionality
  - Get from: [Tavily](https://tavily.com)
  - Used in: All agents with search capabilities

- **DATABRICKS_HOST** & **DATABRICKS_TOKEN**: For ChatDatabricks LLM
  - Your Databricks workspace URL and access token
  - Used in: All graphs (primary LLM)

## 📖 Graph Details

### 1. Chatbot with Tools
**File**: `graph_with_tools.py`
- Simple chatbot with Tavily search
- Direct tool integration
- Chat mode compatible

### 2. Reflection Agent
**File**: `reflection.py`
- Generates essays and critiques them
- Iterative improvement cycle
- Stops after 3 essay revisions

### 3. Plan and Execute
**File**: `plan_and_execute.py`
- Creates multi-step plans
- Executes plans step by step
- Replans based on results

### 4. Hierarchical Agent Teams
**File**: `hierarchical_agent_teams.py`
- **Research Team**: Search + Web scraper agents
- **Writing Team**: Document writer + Note taker agents
- **Top Supervisor**: Coordinates between teams

### 5. Multi-Agent Collaboration
**File**: `multi_agent_collaboration.py`
- **Researcher**: Gathers information with Tavily
- **Analyst**: Analyzes and summarizes findings
- Collaborative back-and-forth until "FINAL ANSWER"

### 6. ReAct Agent
**File**: `react_agent.py`
- Explicit **Thought** → **Action** → **Observation** cycle
- Shows reasoning process clearly
- True ReAct pattern implementation

## 🎯 Usage Examples

### Basic Chat
```bash
langgraph dev chatbot_with_tools.py
```
Ask: *"What's the weather in San Francisco?"*

### Essay Writing
```bash
langgraph dev reflection.py
```
Ask: *"Write an essay about renewable energy"*

### Complex Planning
```bash
langgraph dev plan_and_execute.py
```
Ask: *"Plan a 3-day trip to Tokyo including budget analysis"*

### Team Research
```bash
langgraph dev hierarchical_agent_teams.py
```
Ask: *"Research AI trends and write a comprehensive report"*

### Data Analysis
```bash
langgraph dev multi_agent_collaboration.py
```
Ask: *"Research the latest AI developments and analyze key trends"*

### Step-by-Step Reasoning
```bash
langgraph dev react_agent.py
```
Ask: *"What are the main causes of climate change and their solutions?"*

## 🔧 Configuration

The `langgraph.json` file configures:
- **Dependencies**: All required packages
- **Graphs**: Available graph endpoints
- **Environment**: Points to `.env` file

## 🎨 Chat Mode Features

All graphs are optimized for LangGraph Studio's Chat mode:
- ✅ Uses `MessagesState` for conversation history
- ✅ Interactive back-and-forth conversations
- ✅ Real-time agent responses
- ✅ Visual graph execution flow

## 🚨 Security Notes

- **Never commit `.env`** - Contains sensitive API keys
- **File operations**: Some agents create temporary files
- **Code execution**: ReAct agent executes search queries only

## 🤝 Contributing

To add new graph examples:
1. Create new `.py` file following existing patterns
2. Use `MessagesState` for Chat mode compatibility
3. Add to `langgraph.json` graphs section
4. Update this README

## 📚 Learn More

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Studio](https://github.com/langchain-ai/langgraph-studio)
- [Multi-Agent Patterns](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [ChatDatabricks](https://python.langchain.com/docs/integrations/chat/databricks/)

## 🎉 Happy Building!

Each graph demonstrates different multi-agent patterns and LangGraph capabilities. Start with `chatbot_with_tools` for basics, then explore more complex patterns like `hierarchical_agent_teams` for production use cases.