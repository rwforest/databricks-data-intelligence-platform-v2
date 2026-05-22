"""
LangGraph ReAct Agent with ChatDatabricks for LangGraph Studio
A custom reasoning and action agent that works with chat models with tool calling support
Compatible with Chat mode in LangGraph Studio
"""

from datetime import UTC, datetime
from typing import Dict, List, Literal, Optional, Any, cast

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from databricks_langchain import ChatDatabricks
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode

# Initialize LLM
llm = ChatDatabricks(
    endpoint="databricks-claude-sonnet-4",
    max_tokens=32768
)

# ReAct System prompt
SYSTEM_PROMPT = """You are a helpful AI assistant that uses the ReAct (Reasoning and Acting) approach to solve problems.

You should follow this pattern:
1. **Thought**: Think about what you need to do to answer the question
2. **Action**: Use a tool if needed to gather information
3. **Observation**: Analyze the results from the tool
4. Repeat steps 1-3 as needed
5. **Final Answer**: Provide your conclusion when you have enough information

Always start your response with "Thought:" and clearly show your reasoning process.
When you use a tool, explain why you're using it.
When you get results, analyze what they mean.

System time: {system_time}"""

# Tools
@tool
async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    tavily = TavilySearch(max_results=10)
    return cast(dict[str, Any], await tavily.ainvoke({"query": query}))

TOOLS = [search]

# State definition that extends MessagesState for Chat mode compatibility
class State(MessagesState):
    is_last_step: bool = False
    reasoning_step: int = 0

# Node functions
async def reasoning_step(state: State) -> Dict[str, Any]:
    """ReAct reasoning step - the model thinks about what to do next.

    This is where the 'Reasoning' part of ReAct happens.
    """
    # Initialize the model with tool binding
    model = llm.bind_tools(TOOLS)

    # Format the system prompt
    system_message = SYSTEM_PROMPT.format(
        system_time=datetime.now(tz=UTC).isoformat()
    )

    # Add ReAct-specific guidance based on step count
    step_count = state.get("reasoning_step", 0)
    if step_count == 0:
        guidance = "\n\nThis is your first step. Start with 'Thought:' and think about how to approach this problem."
    else:
        guidance = f"\n\nThis is step {step_count + 1}. Continue with 'Thought:' and decide what to do next based on previous observations."

    # Prepare messages with system prompt and guidance
    messages = [
        {"role": "system", "content": system_message + guidance}
    ] + state["messages"]

    # Get the model's response
    response = cast(AIMessage, await model.ainvoke(messages))

    # Handle the case when it's the last step and the model still wants to use a tool
    if state.get("is_last_step", False) and response.tool_calls:
        return {
            "messages": [
                AIMessage(
                    id=response.id,
                    content="Thought: I've reached the maximum number of steps. Let me provide a final answer based on what I've learned so far.\n\nFinal Answer: Sorry, I could not complete the full investigation in the specified number of steps, but I can provide the information I've gathered.",
                )
            ],
            "reasoning_step": step_count + 1
        }

    # Return the model's response and increment step count
    return {
        "messages": [response],
        "reasoning_step": step_count + 1
    }

def route_reasoning_output(state: State) -> Literal["__end__", "tools"]:
    """Determine the next node based on the reasoning output.

    In ReAct, after reasoning:
    - If the model wants to use tools (Action), go to tools
    - If the model provides a final answer, end
    """
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError(
            f"Expected AIMessage in output edges, but got {type(last_message).__name__}"
        )

    # Check if this is a final answer
    if "final answer" in last_message.content.lower():
        return "__end__"

    # If there is a tool call (Action), go to tools
    if last_message.tool_calls:
        return "tools"

    # If no tool call and no final answer, something went wrong - end anyway
    return "__end__"

# Build the ReAct graph
builder = StateGraph(State)

# Define the nodes
builder.add_node("reasoning", reasoning_step)  # The "Reasoning" part of ReAct
builder.add_node("tools", ToolNode(TOOLS))     # The "Acting" part of ReAct

# Set the entrypoint as reasoning
builder.add_edge(START, "reasoning")

# After reasoning, either use tools or end
builder.add_conditional_edges(
    "reasoning",
    route_reasoning_output,
)

# After tools (Action), return to reasoning for observation and next thought
builder.add_edge("tools", "reasoning")

# Compile the graph
graph = builder.compile()

# Export for LangGraph Studio
app = graph