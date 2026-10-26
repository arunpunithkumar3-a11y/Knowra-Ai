import secrets
from typing import List, Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.business_schemas import BusinessCreate, BusinessUpdate
from src.models.database import Business


def to_uuid(val: Union[UUID, str, None]) -> Optional[UUID]:
    if not val:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class BusinessService:
    async def get_business_by_id(
        self, business_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Business]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return None
        result = await session.execute(select(Business).where(Business.uid == b_uuid))
        return result.scalar_one_or_none()

    async def get_business_by_public_key(
        self, public_key: str, session: AsyncSession
    ) -> Optional[Business]:
        if not public_key:
            return None
        result = await session.execute(
            select(Business).where(Business.public_key == public_key)
        )
        return result.scalar_one_or_none()

    async def get_businesses_by_owner(
        self,
        owner_id: Union[UUID, str],
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Business]:
        o_uuid = to_uuid(owner_id)
        if not o_uuid:
            return []
        result = await session.execute(
            select(Business)
            .where(Business.owner_id == o_uuid)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_business_with_documents(
        self, business_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Business]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return None
        result = await session.execute(
            select(Business)
            .options(selectinload(Business.documents))
            .where(Business.uid == b_uuid)
        )
        return result.scalar_one_or_none()

    async def get_business_with_questions(
        self, business_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Business]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return None
        result = await session.execute(
            select(Business)
            .options(selectinload(Business.questions_asked))
            .where(Business.uid == b_uuid)
        )
        return result.scalar_one_or_none()

    get_business_with_chats = get_business_with_questions

    async def create_business(
        self,
        business_data: BusinessCreate,
        owner_id: Union[UUID, str],
        session: AsyncSession,
    ) -> Business:
        o_uuid = to_uuid(owner_id)
        business_name = (
            business_data.business_name
            or getattr(business_data, "name", None)
            or "My Business"
        )
        public_key = business_data.public_key or f"pk_{secrets.token_urlsafe(16)}"

        new_business = Business(
            owner_id=o_uuid,
            business_name=business_name,
            description=business_data.description,
            website_url=business_data.website_url,
            public_key=public_key,
        )
        session.add(new_business)
        await session.commit()
        await session.refresh(new_business)
        return new_business

    async def update_business(
        self,
        business_id: Union[UUID, str],
        business_data: BusinessUpdate,
        session: AsyncSession,
        **kwargs,
    ) -> Optional[Business]:
        target_id = business_id or kwargs.get("buisness_id")
        target_data = business_data or kwargs.get("buisness_data")
        target_business = await self.get_business_by_id(target_id, session)
        if not target_business:
            return None

        update_dict = target_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(target_business, key, value)

        await session.commit()
        await session.refresh(target_business)
        return target_business

    async def delete_business(
        self, business_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Business]:
        business = await self.get_business_by_id(business_id, session)
        if business:
            await session.delete(business)
            await session.commit()
        return business


# Aliases
BuisnessService = BusinessService
business_service = BusinessService()
buisness_service = business_service
