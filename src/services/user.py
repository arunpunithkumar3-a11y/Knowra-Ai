from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.password import create_hash_password
from src.models.auth_schemas import UserSignup, UserUpdate
from src.models.database import User


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, uid: UUID) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.uid == uid))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_user_name(self, user_name: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.user_name == user_name)
        )
        return result.scalar_one_or_none()

    async def user_exists(self, email: str) -> bool:
        user = await self.get_user_by_email(email)
        return user is not None

    async def create_user(self, data: UserSignup) -> User:
        user_data = data.model_dump()
        password = user_data.pop("password")
        password_hash = create_hash_password(password)
        new_user = User(**user_data, password_hash=password_hash)
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def update_user(self, data: UserUpdate, user: User) -> User:
        user_data = data.model_dump(exclude_unset=True)
        for k, v in user_data.items():
            setattr(user, k, v)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete_user(self, uid: UUID) -> Optional[User]:
        user = await self.get_user_by_id(uid)
        if user:
            await self.session.delete(user)
            await self.session.commit()
        return user

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        result = await self.session.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()
