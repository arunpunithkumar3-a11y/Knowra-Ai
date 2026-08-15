from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.models.database import Org


class OrgService:
    async def get_all_org(self, session: AsyncSession):
        data = select(Org)
        result = await session.execute(data)
        orgs = result.all()
        return orgs
