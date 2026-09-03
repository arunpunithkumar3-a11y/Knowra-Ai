from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.core.dependency import verify_token
from src.core.main import get_session
from src.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
)
from src.knowra.agent.stream import stream_chat
from src.models.chat_schemas import ChatRequest
from src.services.business import BuisnessService

agent_router = APIRouter()


@agent_router.post("/knowra/chat/{business_id}")
async def chat(
    business_id: str,
    data: ChatRequest,
    token_details: dict = Depends(verify_token),
    session=Depends(get_session),
):
    user_id = token_details.get("user_data", {}).get("user_id")

    if not user_id:
        raise AuthenticationError(detail="Invalid token payload")

    try:
        business_uuid = UUID(business_id)
        user_uuid = UUID(user_id)
    except ValueError:
        raise ValidationError(detail="Invalid ID")

    business_service = BuisnessService()

    business = await business_service.get_business_by_id(
        business_id=business_uuid,
        session=session,
    )

    if not business:
        raise NotFoundError(detail="Business not found")

    if business.owner_id != user_uuid:
        raise AuthorizationError(detail="You do not have access to this business")
    return StreamingResponse(
        stream_chat(
            message=data.message,
            thread_id=data.thread_id,
            business_id=str(business.uid),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@agent_router.post("/widget/{public_key}")
async def widget_chat(
    public_key: str,
    data: ChatRequest,
    session=Depends(get_session),
):
    business_service = BuisnessService()

    business = await business_service.get_business_by_public_key(
        public_key=public_key,
        session=session,
    )

    if not business:
        raise NotFoundError(detail="Business not found")
    return StreamingResponse(
        stream_chat(
            message=data.message,
            thread_id=data.thread_id,
            business_id=str(business.uid),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@agent_router.get("/history/{thread_id}")
async def get_chat_history(thread_id: str):
    """
    Get message history for an ongoing chat thread from PostgreSQL checkpointer.
    """
    from langchain_core.messages import AIMessage, HumanMessage

    from src.knowra.agent.graph import build_graph

    graph = await build_graph()
    state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state and state.values else []

    formatted = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            formatted.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage) and msg.content:
            formatted.append({"role": "assistant", "content": msg.content})

    return {
        "thread_id": thread_id,
        "total_messages": len(formatted),
        "messages": formatted,
    }


@agent_router.delete("/history/{thread_id}")
async def clear_chat_history(thread_id: str):
    """
    Clear chat history for a thread from PostgreSQL checkpointer.
    """
    from src.core.postgres import get_checkpointer

    try:
        checkpointer = await get_checkpointer()
        if checkpointer:
            if hasattr(checkpointer, "adelete"):
                await checkpointer.adelete({"configurable": {"thread_id": thread_id}})
            elif hasattr(checkpointer, "adelete_thread"):
                await checkpointer.adelete_thread(thread_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat history: {str(e)}",
        )

    return {
        "status": "success",
        "message": f"Chat history for thread '{thread_id}' cleared successfully.",
    }
