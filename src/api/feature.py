from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.analyse.cluster import analyse
from src.core.dependency import verify_token
from src.core.main import get_session
from src.exceptions import AuthenticationError, ValidationError
from src.services.questions import question_service

feature_router = APIRouter()


def _parse_uuid(value: str, field_name: str = "ID") -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        raise ValidationError(detail=f"Invalid {field_name} format")


@feature_router.get("/feature/questions/{business_id}")
async def get_total_questions(
    business_id: str,
    session: AsyncSession = Depends(get_session),
    token_details=Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise AuthenticationError(detail="Invalid token payload")

    business_uuid = _parse_uuid(business_id, "business ID")
    questions = await question_service.get_total_question_by_business_id(
        business_id=business_uuid, session=session
    )
    return {"message": questions, "total_questions": questions}


@feature_router.post("/feature/cluster/{business_id}")
async def get_cluster_feature(
    business_id: str,
    start: int,
    end: int,
    session: AsyncSession = Depends(get_session),
    token_details=Depends(verify_token),
):
    user_id = token_details.get("user_data", {}).get("user_id")
    if not user_id:
        raise AuthenticationError(detail="Invalid token payload")

    business_uuid = _parse_uuid(business_id, "business ID")

    total_questions = await question_service.get_total_question_by_business_id(
        business_id=business_uuid, session=session
    )
    if total_questions == 0:
        raise ValidationError(detail="No questions available for analysis.")
    if start < 1:
        raise ValidationError(detail=f"Start index must be >= 1 (got {start}).")
    if end < start:
        raise ValidationError(
            detail=f"End index must be >= start index (got start={start}, end={end})."
        )
    range_size = end - start + 1
    if range_size > 100:
        raise ValidationError(
            detail=f"Analysis range cannot exceed 100 questions per request (selected: {range_size})."
        )
    if end > total_questions:
        raise ValidationError(
            detail=f"End index ({end}) exceeds total available questions ({total_questions})."
        )

    raw_questions = await question_service.get_questions_by_range(
        business_id=business_uuid,
        start=start - 1,
        end=end,
        session=session,
    )
    question_texts = [
        q.question_text for q in raw_questions if getattr(q, "question_text", None)
    ]
    result = await analyse(question_texts)
    serialized_result = [
        item.model_dump() if hasattr(item, "model_dump") else item for item in result
    ]
    return {"message": serialized_result}
