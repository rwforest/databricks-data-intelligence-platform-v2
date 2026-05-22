"""
LangGraph Plan-and-Execute Agent with ChatDatabricks for LangGraph Studio
A demonstration of the plan-and-execute pattern using ChatDatabricks
Compatible with Chat mode in LangGraph Studio
"""

import operator
from typing import Annotated, List, Tuple, Union, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, MessagesState

# State definition that extends MessagesState for Chat mode compatibility
class PlanExecute(MessagesState):
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str

# Pydantic models for structured output
class Plan(BaseModel):
    """Plan to follow in future"""
    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class Response(BaseModel):
    """Response to user."""
    response: str

class Act(BaseModel):
    """Action to perform."""
    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )

# Initialize LLM and tools
llm = ChatDatabricks(
    endpoint="databricks-claude-sonnet-4",
    max_tokens=32768
)

tools = [TavilySearchResults(max_results=3)]

# Create execution agent
prompt = "You are a helpful assistant."
agent_executor = create_react_agent(llm, tools, prompt=prompt)

# Planning chain
planner_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.""",
    ),
    ("placeholder", "{messages}"),
])
planner = planner_prompt | llm.with_structured_output(Plan)

# Re-planning chain
replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
)
replanner = replanner_prompt | llm.with_structured_output(Act)

# Node functions
async def plan_step(state: PlanExecute):
    """Create initial plan based on user messages"""
    # Get the last user message as the objective
    user_message = next((msg.content for msg in reversed(state["messages"]) if msg.type == "human"), "")
    plan = await planner.ainvoke({"messages": [("user", user_message)]})
    return {"plan": plan.steps}

async def execute_step(state: PlanExecute):
    """Execute the current step in the plan"""
    plan = state["plan"]
    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}."""

    agent_response = await agent_executor.ainvoke(
        {"messages": [("user", task_formatted)]}
    )
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }

async def replan_step(state: PlanExecute):
    """Re-evaluate plan based on completed steps"""
    # Get the original user input for re-planning
    user_message = next((msg.content for msg in reversed(state["messages"]) if msg.type == "human"), "")

    replan_input = {
        "input": user_message,
        "plan": state.get("plan", []),
        "past_steps": state.get("past_steps", [])
    }

    output = await replanner.ainvoke(replan_input)
    if isinstance(output.action, Response):
        # Add the final response as an AI message
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=output.action.response)]}
    else:
        return {"plan": output.action.steps}

def should_end(state: PlanExecute) -> Literal["agent", "__end__"]:
    """Determine if we should continue or end"""
    # Check if the last message is an AI response (indicating completion)
    if state["messages"] and state["messages"][-1].type == "ai":
        # Check if it's a final response (not from agent_executor)
        last_msg = state["messages"][-1]
        if hasattr(last_msg, 'content') and not any(word in last_msg.content.lower() for word in ['step', 'plan', 'task']):
            return "__end__"
    return "agent"

# Build the graph
workflow = StateGraph(PlanExecute)

# Add nodes
workflow.add_node("planner", plan_step)
workflow.add_node("agent", execute_step)
workflow.add_node("replan", replan_step)

# Add edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "agent")
workflow.add_edge("agent", "replan")
workflow.add_conditional_edges(
    "replan",
    should_end,
    ["agent", "__end__"],
)

# Compile the graph
graph = workflow.compile()

# Export for LangGraph Studio
app = graph