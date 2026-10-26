import asyncio
import json
import logging
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage

from src.knowra.agent.graph import get_compiled_graph

logger = logging.getLogger(__name__)


def _sse(payload: dict) -> str:
    """Format SSE data frame."""
    return f"data: {json.dumps(payload)}\n\n"


class ThinkFilter:
    """Filters out <think>...</think> reasoning tags from streaming text."""

    def __init__(self):
        self.inside = False
        self.buf = ""

    def process(self, chunk: str) -> str:
        self.buf += chunk
        out = []

        while self.buf:
            if not self.inside:
                if "<think>" in self.buf:
                    before, _, self.buf = self.buf.partition("<think>")
                    out.append(before)
                    self.inside = True
                else:
                    # Check if the buffer ends with an incomplete prefix of "<think>"
                    keep_len = 0
                    for i in range(1, min(len(self.buf), 7)):
                        if "<think>".startswith(self.buf[-i:]):
                            keep_len = i
                    if keep_len > 0:
                        out.append(self.buf[:-keep_len])
                        self.buf = self.buf[-keep_len:]
                        break
                    out.append(self.buf)
                    self.buf = ""
            else:
                if "</think>" in self.buf:
                    _, _, self.buf = self.buf.partition("</think>")
                    self.inside = False
                    self.buf = self.buf.lstrip("\r\n")
                else:
                    # Check if the buffer ends with an incomplete prefix of "</think>"
                    keep_len = 0
                    for i in range(1, min(len(self.buf), 8)):
                        if "</think>".startswith(self.buf[-i:]):
                            keep_len = i
                    if keep_len > 0:
                        self.buf = self.buf[-keep_len:]
                    else:
                        self.buf = ""
                    break

        return "".join(out)

    def flush(self) -> str:
        res = self.buf if not self.inside else ""
        self.buf = ""
        return res


# Backward compatibility alias
StreamingThinkFilter = ThinkFilter


async def stream_chat(
    message: str,
    thread_id: str,
    business_id: str,
    business_name: str = "",
    business_description: str = "",
) -> AsyncGenerator[str, None]:
    """
    Public streaming interface for business-aligned conversational agent.
    Streams only the final user-facing response from the ReAct 'agent' node or 'guard' node.
    Guarantees [DONE] termination frame on completion or error.
    """
    try:
        graph = await get_compiled_graph()
    except Exception as e:
        logger.error("Failed to compile or load graph: %s", e, exc_info=True)
        yield _sse(
            {
                "type": "error",
                "error": "Unable to initialize conversational assistant. Please try again.",
            }
        )
        yield "data: [DONE]\n\n"
        return

    config = {
        "configurable": {
            "thread_id": thread_id,
            "business_id": business_id,
            "business_name": business_name,
            "business_description": business_description,
        }
    }
    input_data = {
        "messages": [HumanMessage(content=message)],
        "business_name": business_name,
        "business_description": business_description,
    }

    think_filter = ThinkFilter()

    try:
        async for msg, meta in graph.astream(
            input_data, config=config, stream_mode="messages"
        ):
            if meta.get("langgraph_node") not in ("agent", "guard"):
                continue

            if getattr(msg, "tool_call_chunks", None) or getattr(
                msg, "tool_calls", None
            ):
                continue

            content = getattr(msg, "content", None)
            if not content or not isinstance(content, str):
                continue

            delta = think_filter.process(content)
            if delta:
                yield _sse({"type": "delta", "content": delta})

        remaining = think_filter.flush()
        if remaining:
            yield _sse({"type": "delta", "content": remaining})

        yield _sse({"type": "done"})

    except asyncio.CancelledError:
        logger.info("Chat stream cancelled by client for thread '%s'", thread_id)
        return
    except Exception as e:
        logger.error(
            "Error in stream_chat for thread '%s': %s", thread_id, e, exc_info=True
        )
        yield _sse(
            {
                "type": "error",
                "error": "A temporary error occurred while generating your response. Please try again.",
            }
        )
    finally:
        yield "data: [DONE]\n\n"
