from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.password import create_hash_password
from src.models.auth_schemas import UserSignup, UserUpdate
from src.models.database import User


class UserService:

    async def get_user_by_id(
        self, uid: Union[UUID, str], session: AsyncSession
    ) -> Optional[User]:
        if isinstance(uid, str):
            try:
                uid = UUID(uid)
            except ValueError:
                return None
        result = await session.execute(select(User).where(User.uid == uid))
        return result.scalar_one_or_none()

    async def get_user_by_email(
        self, email: str, session: AsyncSession
    ) -> Optional[User]:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_user_name(
        self, user_name: str, session: AsyncSession
    ) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.user_name == user_name)
        )
        return result.scalar_one_or_none()

    async def user_exists(self, email: str, session: AsyncSession) -> bool:
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(self, data: UserSignup, session: AsyncSession) -> User:
        user_data = data.model_dump()
        password = user_data.pop("password")
        user_data.pop("role", None)
        password_hash = create_hash_password(password)
        new_user = User(**user_data, password_hash=password_hash)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

    async def update_user(
        self, data: UserUpdate, user_id: Union[UUID, str], session: AsyncSession
    ) -> Optional[User]:
        user_data = data.model_dump(exclude_unset=True)
        user = await self.get_user_by_id(user_id, session)
        if not user:
            return None
        for k, v in user_data.items():
            setattr(user, k, v)
        await session.commit()
        await session.refresh(user)
        return user

    async def delete_user(
        self, uid: Union[UUID, str], session: AsyncSession
    ) -> Optional[User]:
        user = await self.get_user_by_id(uid, session)
        if user:
            await session.delete(user)
            await session.commit()
        return user

    async def get_all_users(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[User]:
        result = await session.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())
