from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from src.config import configure
from src.knowra.agent.state import AgentState
from src.knowra.agent.tools import tools
from src.knowra.prompt import REACT_AGENT_SYSTEM_PROMPT

llm = ChatOpenAI(
    base_url=configure.NVIDIA_BASE_URL,
    model=configure.LLM_MODEL,
    api_key=configure.NVIDIA_API_KEY,
    temperature=0.2,
)

model_with_tools = llm.bind_tools(tools)


async def agent_node(state: AgentState):

    messages = list(state["messages"])

    if not messages or not isinstance(
        messages[0],
        SystemMessage,
    ):
        messages.insert(
            0,
            SystemMessage(content=REACT_AGENT_SYSTEM_PROMPT),
        )

    response = await model_with_tools.ainvoke(messages)

    return {"messages": [response]}
