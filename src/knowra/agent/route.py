from langchain_core.messages import AIMessage

from src.knowra.agent.state import AgentState


def should_continue(state: AgentState):

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"
