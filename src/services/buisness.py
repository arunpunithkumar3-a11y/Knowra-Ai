import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.buisness_schemas import BusinessCreate, BusinessUpdate
from src.models.database import Business


class BusinessService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_business_by_id(self, business_id: UUID) -> Optional[Business]:
        result = await self.session.execute(
            select(Business).where(Business.uid == business_id)
        )
        return result.scalar_one_or_none()

    async def get_business_by_public_key(self, public_key: str) -> Optional[Business]:
        result = await self.session.execute(
            select(Business).where(Business.public_key == public_key)
        )
        return result.scalar_one_or_none()

    async def get_businesses_by_owner(
        self, owner_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Business]:
        result = await self.session.execute(
            select(Business)
            .where(Business.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_business_with_documents(
        self, business_id: UUID
    ) -> Optional[Business]:
        result = await self.session.execute(
            select(Business)
            .options(selectinload(Business.documents))
            .where(Business.uid == business_id)
        )
        return result.scalar_one_or_none()

    async def get_business_with_chats(self, business_id: UUID) -> Optional[Business]:
        result = await self.session.execute(
            select(Business)
            .options(selectinload(Business.chats))
            .where(Business.uid == business_id)
        )
        return result.scalar_one_or_none()

    async def create_business(
        self, business_data: BusinessCreate, owner_id: UUID
    ) -> Business:
        business_name = business_data.business_name
        public_key = business_data.public_key or f"pk_{secrets.token_urlsafe(16)}"

        new_business = Business(
            owner_id=owner_id,
            business_name=business_name,
            description=business_data.description,
            website_url=business_data.website_url,
            public_key=public_key,
        )
        self.session.add(new_business)
        await self.session.commit()
        await self.session.refresh(new_business)
        return new_business

    async def update_business(
        self,
        business_data: BusinessUpdate,
        business_id: str,
    ) -> Optional[Business]:
        target_business = await self.get_business_by_id(business_id)
        update_dict = business_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(target_business, key, value)
        await self.session.commit()
        await self.session.refresh(target_business)
        return target_business

    async def delete_business(self, business_id: UUID) -> Optional[Business]:
        business = await self.get_business_by_id(business_id)
        if business:
            await self.session.delete(business)
            await self.session.commit()
        return business
