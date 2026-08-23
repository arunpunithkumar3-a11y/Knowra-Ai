import secrets
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.buisness_schemas import BusinessCreate, BusinessUpdate
from src.models.database import Business


def to_uuid(val: Union[UUID, str]) -> Optional[UUID]:
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return None


class BuisnessService:
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
    ) -> list[Business]:
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

    async def get_business_with_chats(
        self, business_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[Business]:
        b_uuid = to_uuid(business_id)
        if not b_uuid:
            return None
        result = await session.execute(
            select(Business)
            .options(selectinload(Business.chats))
            .where(Business.uid == b_uuid)
        )
        return result.scalar_one_or_none()

    async def create_business(
        self,
        business_data: BusinessCreate,
        owner_id: Union[UUID, str],
        session: AsyncSession,
    ) -> Business:
        o_uuid = to_uuid(owner_id)
        business_name = business_data.business_name
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
        buisness_id: Optional[Union[UUID, str]] = None,
        buisness_data: Optional[BusinessUpdate] = None,
    ) -> Optional[Business]:
        target_id = buisness_id if buisness_id is not None else business_id
        target_data = buisness_data if buisness_data is not None else business_data
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
