"""
LangGraph chatbot with tools for LangGraph Studio visualization
"""
import os
from dotenv import load_dotenv

from langchain_tavily import TavilySearch
from databricks_langchain import ChatDatabricks
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables.graph_mermaid import draw_mermaid
import json

# Load environment variables from .env file
load_dotenv()

# Create tools
tool = TavilySearch(max_results=2)
tools = [tool]

# Create LLM with tools
llm = ChatDatabricks(endpoint="databricks-claude-sonnet-4")
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: MessagesState):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

# Build the graph
graph_builder = StateGraph(MessagesState)

# Add nodes
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools))

# Add edges
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")

# Compile the graph
graph = graph_builder.compile()

# For LangGraph Studio, export the graph
app = graph

# Generate high-resolution graph with custom styling
mermaid_config = {
    "theme": "base",
    "themeVariables": {
        "primaryColor": "#FF5F47",
        "primaryTextColor": "#FFFFFF",
        "primaryBorderColor": "#FF5F47",
        "secondaryColor": "#FABFBB",
        "tertiaryColor": "#FFFFFF",
        "background": "#FFFFFF",
        "fontFamily": "Arial, sans-serif",
        "fontSize": "16px"
    }
}

# Use the draw_mermaid function to create high-res image
try:
    # Get the mermaid syntax from the graph
    mermaid_syntax = app.get_graph().draw_mermaid()

    # Convert the Python dict to a JSON string for the Mermaid config block
    config_json = json.dumps(mermaid_config, indent=2)

    # Combine the config and the graph syntax into a single string
    mermaid_full_string = f"""
    ---
    config: {config_json}
    ---
    {mermaid_syntax}
    """

    print(mermaid_full_string)
except Exception as e:
    print(f"Could not generate graph image: {e}")
    # Fallback to basic drawing
    try:
        png_data = app.get_graph().draw_png()
        with open("graph.png", "wb") as f:
            f.write(png_data)
        print("Basic graph saved to graph.png")
    except Exception as e2:
        print(f"Could not generate any graph visualization: {e2}")