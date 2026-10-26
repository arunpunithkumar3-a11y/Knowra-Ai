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
            END: END,
        },
    )

    workflow.add_edge("tools", "agent")

    checkpointer = await get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


_compiled_graph = None


async def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = await build_graph()
    return _compiled_graph
