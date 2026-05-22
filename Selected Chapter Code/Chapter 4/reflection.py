"""
LangGraph Reflection - Essay Writing with Critique and Revision
A demonstration of reflection pattern using ChatDatabricks for LangGraph Studio
"""

import os
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from databricks_langchain import ChatDatabricks
from langgraph.graph import END, StateGraph, START, MessagesState

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatDatabricks(
    endpoint="databricks-claude-sonnet-4",
    max_tokens=32768
)

# Generation prompt and chain
generation_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an essay assistant tasked with writing excellent 5-paragraph essays."
        " Generate the best essay possible for the user's request."
        " If the user provides critique, respond with a revised version of your previous attempts.",
    ),
    MessagesPlaceholder(variable_name="messages"),
])
generate = generation_prompt | llm

# Reflection prompt and chain
reflection_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a teacher grading an essay submission. Generate critique and recommendations for the user's submission."
        " Provide detailed recommendations, including requests for length, depth, style, etc.",
    ),
    MessagesPlaceholder(variable_name="messages"),
])
reflect = reflection_prompt | llm

# Node functions
async def generation_node(state: MessagesState) -> MessagesState:
    """Generate or revise the essay based on current messages"""
    return {"messages": [await generate.ainvoke(state["messages"])]}

async def reflection_node(state: MessagesState) -> MessagesState:
    """Reflect on the generated essay and provide critique"""
    # Transform messages for reflection - swap AI/human roles for proper critique flow
    cls_map = {"ai": HumanMessage, "human": AIMessage}
    # Keep first message (original request) the same, transform the rest
    translated = [state["messages"][0]] + [
        cls_map[msg.type](content=msg.content) for msg in state["messages"][1:]
    ]
    res = await reflect.ainvoke(translated)
    # Return critique as human feedback for the generator
    return {"messages": [HumanMessage(content=res.content)]}

# Conditional logic
def should_continue(state: MessagesState):
    """Decide whether to continue reflecting or end the process"""
    # Count AI messages (essays) - stop after 3 essays have been generated
    ai_messages = [msg for msg in state["messages"] if msg.type == "ai"]
    if len(ai_messages) >= 3:
        return END
    return "reflect"

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)

# Add edges
builder.add_edge(START, "generate")
builder.add_conditional_edges("generate", should_continue)
builder.add_edge("reflect", "generate")

# Compile the graph (LangGraph Studio handles persistence automatically)
graph = builder.compile()

# Export for LangGraph Studio
app = graph