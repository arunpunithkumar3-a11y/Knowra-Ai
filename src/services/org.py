from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.database import JoinRequest, JoinRequestStatus, Org, OrgMember
from src.models.org_schemas import OrgCreate, OrgUpdate


class OrgService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_orgs(self, skip: int = 0, limit: int = 100) -> list[Org]:
        result = await self.session.execute(select(Org).offset(skip).limit(limit))
        return result.scalars().all()

    async def get_org_by_id(self, org_id: UUID) -> Optional[Org]:
        result = await self.session.execute(select(Org).where(Org.uid == org_id))
        return result.scalar_one_or_none()

    async def get_org_with_members(self, org_id: UUID) -> Optional[Org]:
        result = await self.session.execute(
            select(Org).options(selectinload(Org.members)).where(Org.uid == org_id)
        )
        return result.scalar_one_or_none()

    async def get_orgs_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Org]:
        result = await self.session.execute(
            select(Org).where(Org.user_id == user_id).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def get_org_members(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[OrgMember]:
        result = await self.session.execute(
            select(OrgMember)
            .where(OrgMember.org_id == org_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_member_by_user_and_org(
        self, user_id: UUID, org_id: UUID
    ) -> Optional[OrgMember]:
        result = await self.session.execute(
            select(OrgMember).where(
                OrgMember.user_id == user_id,
                OrgMember.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_org(self, org_data: OrgCreate, user_id: UUID) -> Org:
        new_org = Org(
            org_name=org_data.org_name,
            description=org_data.description,
            user_id=user_id,
        )
        self.session.add(new_org)
        await self.session.commit()
        await self.session.refresh(new_org)
        return new_org

    async def update_org(self, org_data: OrgUpdate, org: Org) -> Org:
        org.org_name = org_data.org_name
        org.description = org_data.description
        await self.session.commit()
        await self.session.refresh(org)
        return org

    async def delete_org(self, org_id: UUID) -> Optional[Org]:
        org = await self.get_org_by_id(org_id)
        if org:
            await self.session.delete(org)
            await self.session.commit()
        return org

    async def get_join_requests(
        self, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[JoinRequest]:
        result = await self.session.execute(
            select(JoinRequest)
            .where(JoinRequest.org_id == org_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_pending_join_request(
        self, user_id: UUID, org_id: UUID
    ) -> Optional[JoinRequest]:
        result = await self.session.execute(
            select(JoinRequest).where(
                JoinRequest.user_id == user_id,
                JoinRequest.org_id == org_id,
                JoinRequest.status == JoinRequestStatus.pending,
            )
        )
        return result.scalar_one_or_none()
