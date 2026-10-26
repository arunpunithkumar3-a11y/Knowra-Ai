from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import Questions


def to_uuid(val: Union[UUID, str, None]) -> Optional[UUID]:
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class QuestionService:
    async def get_questions_by_business_id(
        self,
        session: AsyncSession,
        business_id: Union[UUID, str],
        limit: int = 100,
    ) -> List[Questions]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return []
        stmt = (
            select(Questions)
            .where(Questions.business_id == b_uuid)
            .order_by(Questions.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def add_questions(
        self,
        question: str,
        session: AsyncSession,
        business_id: Union[UUID, str],
    ) -> Optional[Questions]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return None
        text = (question or "").strip()[:500]
        if not text:
            return None
        new_question = Questions(question_text=text, business_id=b_uuid)
        session.add(new_question)
        await session.commit()
        await session.refresh(new_question)
        return new_question

    async def get_questions_by_range(
        self,
        session: AsyncSession,
        business_id: Union[UUID, str],
        start: int = 0,
        end: int = 10,
    ) -> List[Questions]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return []

        limit = max(end - start, 0)
        stmt = (
            select(Questions)
            .where(Questions.business_id == b_uuid)
            .order_by(Questions.created_at.desc())
            .offset(max(start, 0))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_question_by_business_id(
        self,
        session: AsyncSession,
        business_id: Union[UUID, str],
    ) -> int:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return 0
        stmt = (
            select(func.count())
            .select_from(Questions)
            .where(Questions.business_id == b_uuid)
        )
        result = await session.execute(stmt)
        return int(result.scalar() or 0)


question_service = QuestionService()
