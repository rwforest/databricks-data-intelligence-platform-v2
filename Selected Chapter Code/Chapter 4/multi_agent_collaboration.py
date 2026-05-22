"""
LangGraph Multi-Agent Collaboration with ChatDatabricks for LangGraph Studio
A demonstration of multi-agent collaboration using ChatDatabricks
Compatible with Chat mode in LangGraph Studio
"""

from typing import Annotated, Literal

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, END, StateGraph, START
from langgraph.types import Command

# Initialize LLM
llm = ChatDatabricks(
    endpoint="databricks-claude-sonnet-4",
    max_tokens=32768
)

# Initialize tools
tavily_tool = TavilySearch(max_results=5)


# System prompt utility
def make_system_prompt(suffix: str) -> str:
    return (
        "You are a helpful AI assistant, collaborating with other assistants."
        " Use the provided tools to progress towards answering the question."
        " If you are unable to fully answer, that's OK, another assistant with different tools "
        " will help where you left off. Execute what you can to make progress."
        " If you or any of the other assistants have the final answer or deliverable,"
        " prefix your response with FINAL ANSWER so the team knows to stop."
        f"\n{suffix}"
    )

# Helper function to determine next node
def get_next_node(last_message: BaseMessage, goto: str):
    if "FINAL ANSWER" in last_message.content:
        # Any agent decided the work is done
        return END
    return goto

# Research agent and node
research_agent = create_react_agent(
    llm,
    tools=[tavily_tool],
    prompt=make_system_prompt(
        "You can only do research. You are working with an analyst colleague."
    ),
)

def research_node(
    state: MessagesState,
) -> Command[Literal["analyst", "__end__"]]:
    result = research_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "analyst")
    # Wrap in a human message for compatibility
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content, name="researcher"
    )
    return Command(
        update={
            # Share internal message history of research agent with other agents
            "messages": result["messages"],
        },
        goto=goto,
    )

# Analyst agent and node (analyzes research without code execution)
analyst_agent = create_react_agent(
    llm,
    tools=[],  # No tools needed for analysis
    prompt=make_system_prompt(
        "You analyze and summarize research data. You are working with a researcher colleague. "
        "Provide insights, trends, and conclusions based on the research provided."
    ),
)

def analyst_node(state: MessagesState) -> Command[Literal["researcher", "__end__"]]:
    result = analyst_agent.invoke(state)
    goto = get_next_node(result["messages"][-1], "researcher")
    # Wrap in a human message for compatibility
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content, name="analyst"
    )
    return Command(
        update={
            # Share internal message history of analyst agent with other agents
            "messages": result["messages"],
        },
        goto=goto,
    )

# Build the graph
workflow = StateGraph(MessagesState)
workflow.add_node("researcher", research_node)
workflow.add_node("analyst", analyst_node)

workflow.add_edge(START, "researcher")

# Compile the graph
graph = workflow.compile()

# Export for LangGraph Studio
app = graph