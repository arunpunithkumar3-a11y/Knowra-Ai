import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from src.knowra.agent.graph import build_graph

logger = logging.getLogger(__name__)


async def stream_chat(
    message: str,
    thread_id: str,
    business_id: str,
) -> AsyncGenerator[str, None]:

    # Guardrails check

    # Agent streaming
    graph = await build_graph()
    config = {
        "configurable": {
            "thread_id": thread_id,
            "business_id": business_id,
        }
    }
    try:
        async for event in graph.astream_events(
            {
                "messages": [
                    HumanMessage(content=message),
                ]
            },
            config=config,
            version="v2",
        ):
            event_type = event.get("event")
            node_name = event.get("metadata", {}).get("langgraph_node")

            if event_type == "on_chat_model_stream" and node_name == "agent":
                chunk = event.get("data", {}).get("chunk")
                if chunk:
                    content = getattr(chunk, "content", None)
                    if content and isinstance(content, str):
                        yield f"data: {content}\n\n"

            elif event_type == "on_chain_end" and event.get("name") == "guard":
                output = event.get("data", {}).get("output", {})
                messages = output.get("messages", [])
                for msg in messages:
                    content = getattr(msg, "content", None)
                    if content and isinstance(content, str):
                        yield f"data: {content}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Error in stream_chat: {e}", exc_info=True)
        yield "event: error\n"
        yield "data: Internal server error\n\n"
