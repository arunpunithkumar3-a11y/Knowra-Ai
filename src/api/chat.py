from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from src.core.dependency import verify_token
from src.core.main import get_session
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        business_uuid = UUID(business_id)
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID",
        )

    business_service = BuisnessService()

    business = await business_service.get_business_by_id(
        business_id=business_uuid,
        session=session,
    )

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )

    if business.owner_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this business",
        )
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
