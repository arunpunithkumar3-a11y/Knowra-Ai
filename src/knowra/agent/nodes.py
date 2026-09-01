import re

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config import configure, safety_llm
from src.knowra.agent.state import AgentState
from src.knowra.agent.tools import tools
from src.knowra.guardrails import get_rails
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


async def safety_node(state: AgentState):
    user_query = str(state["messages"][-1].content)
    response = await safety_llm.ainvoke(user_query)
    result = str(response.content).strip().lower()

    if "user safety: unsafe" in result:
        return {"safety": "unsafe"}

    return {"safety": "safe"}


def should_continue(state: AgentState):

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


def safe_check_node(state: AgentState):
    node = state.get("safety", "safe")
    if node == "unsafe":
        return "unsafe"
    return "safe"


async def guard(state: AgentState):
    user_query = state["messages"][-1].content

    rails = get_rails()

    response = await rails.generate_async(
        messages=[
            {
                "role": "user",
                "content": user_query,
            }
        ]
    )

    return {
        "messages": [AIMessage(content=clean_guardrail_response(response["content"]))]
    }


def clean_guardrail_response(response: str) -> str:
    # Remove <think>...</think>
    response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)

    return response.strip()
