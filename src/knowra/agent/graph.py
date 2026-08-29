from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.core.redis import checkpointer
from src.knowra.agent.nodes import agent_node
from src.knowra.agent.route import should_continue
from src.knowra.agent.state import AgentState
from src.knowra.agent.tools import tools


def build_graph():

    workflow = StateGraph(AgentState)

    workflow.add_node(
        "agent",
        agent_node,
    )

    workflow.add_node(
        "tools",
        ToolNode(tools),
    )

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    workflow.add_edge(
        "tools",
        "agent",
    )

    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
