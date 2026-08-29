from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from src.knowra.agent.graph import graph


async def stream_chat(
    message: str,
    thread_id: str,
    business_id: str,
) -> AsyncGenerator[str, None]:

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
            if event.get("event") != "on_chat_model_stream":
                continue

            chunk = event.get("data", {}).get("chunk")

            if not chunk:
                continue

            content = getattr(chunk, "content", None)

            if content:
                yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"

    except Exception:
        yield "event: error\n"
        yield "data: Internal server error\n\n"
