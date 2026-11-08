import asyncio
import logging
import re
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END

from src.config import configure, safety_llm
from src.knowra.agent.state import AgentState
from src.knowra.agent.tools import tools
from src.knowra.guardrails import get_rails
from src.knowra.prompt import prompt_template

logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    base_url=configure.NVIDIA_BASE_URL,
    model=configure.LLM_MODEL,
    api_key=configure.NVIDIA_API_KEY,
    temperature=0.2,
)

model_with_tools = llm.bind_tools(tools)

agent_chain = prompt_template | model_with_tools


def clean_thinking(response: str) -> str:
    """Remove internal reasoning/thought tags (<think>...</think>)."""
    if not response:
        return ""
    return re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()


clean_guardrail_response = clean_thinking


async def agent_node(state: AgentState, config: RunnableConfig = None):
    """
    ReAct Agent node.
    Acts as an employee and customer representative of the specified business.
    Decides whether to invoke search_knowledge_base or answer directly.
    Generates document-grounded, business-aligned responses without mentioning Knowra.
    """
    messages = state.get("messages", [])
    question = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage) or getattr(m, "type", "") == "human":
            question = str(getattr(m, "content", ""))
            break
    if not question and messages:
        question = str(getattr(messages[-1], "content", messages[-1]))

    for attempt in range(3):
        try:
            response = await agent_chain.ainvoke(
                {"question": question},
                config=config,
            )
            content_str = (
                response.content
                if isinstance(response.content, str)
                else str(response.content or "")
            )
            response.content = clean_thinking(content_str)
            return {"messages": [response]}
        except Exception as e:
            logger.warning("agent_node attempt %s failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(2**attempt)
            else:
                return {
                    "messages": [
                        AIMessage(
                            content="I am temporarily unable to complete your request. Please try again in a moment."
                        )
                    ]
                }


async def safety_node(state: AgentState):
    messages = state.get("messages", [])
    if not messages:
        return {"safety": "safe"}

    user_query = str(messages[-1].content)
    try:
        response = await asyncio.wait_for(safety_llm.ainvoke(user_query), timeout=2.5)
        result = str(response.content).strip().lower()
        if "user safety: unsafe" in result:
            return {"safety": "unsafe"}
    except Exception as e:
        logger.warning("Safety check skipped or timed out, defaulting to safe: %s", e)

    return {"safety": "safe"}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Route to tools if agent generated tool_calls, otherwise finish conversation turn."""
    messages = state.get("messages", [])
    if not messages:
        return END

    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and getattr(
        last_message, "tool_calls", None
    ):
        return "tools"

    return END


def safe_check_node(state: AgentState) -> Literal["safe", "unsafe"]:
    return state.get("safety", "safe")


async def guard(state: AgentState):
    messages = state.get("messages", [])
    user_query = messages[-1].content if messages else ""

    try:
        rails = get_rails()
        response = await rails.generate_async(
            messages=[
                {
                    "role": "user",
                    "content": str(user_query),
                }
            ]
        )

        raw_content = ""
        if isinstance(response, dict):
            raw_content = response.get("content", "")
        elif isinstance(response, str):
            raw_content = response
        elif hasattr(response, "content"):
            raw_content = str(response.content)
        else:
            raw_content = str(response)

        cleaned = clean_thinking(raw_content)
        return {
            "messages": [
                AIMessage(
                    content=cleaned
                    or "I am unable to assist with this request as it does not align with our guidelines."
                )
            ]
        }
    except Exception as e:
        logger.warning("Guardrails processing failed: %s", e)
        return {
            "messages": [
                AIMessage(
                    content="I am unable to assist with this request as it does not comply with our guidelines."
                )
            ]
        }
