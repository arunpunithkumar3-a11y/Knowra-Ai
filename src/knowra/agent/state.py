from typing import Annotated, Literal, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    safety: Literal["safe", "unsafe"]
    business_name: Optional[str]
    business_description: Optional[str]
