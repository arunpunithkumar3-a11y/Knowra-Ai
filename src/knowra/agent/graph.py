from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.core.postgres import get_checkpointer
from src.knowra.agent.nodes import (
    agent_node,
    guard,
    safe_check_node,
    safety_node,
    should_continue,
)
from src.knowra.agent.state import AgentState
from src.knowra.agent.tools import tools


async def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("safety_node", safety_node)
    workflow.add_node("guard", guard)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("safety_node")
    workflow.add_conditional_edges(
        "safety_node", safe_check_node, {"unsafe": "guard", "safe": "agent"}
    )
    workflow.add_edge("guard", END)

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=await get_checkpointer())


def __getattr__(name: str):
    if name == "graph":
        return build_graph()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
