from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlmodel import select

from src.core.security import create_hash_password
from src.models.auth import UserSignup, UserUpdate
from src.models.database import User


class UserService:
    async def get_user_by_id(self, uid: str, session: AsyncSession):
        data = select(User).where(User.uid == uid)
        result = await session.execute(data)
        user = result.scalars().first()
        return user

    async def get_user_by_email(self, email: str, session: AsyncSession):
        data = select(User).where(User.email == email)
        result = await session.execute(data)
        user = result.scalars().first()
        return user

    async def user_exists(self, email: str, session: AsyncSession):
        data = await self.get_user_by_email(email, session)
        return data is not None

    async def create_user(self, data: UserSignup, session: AsyncSession):
        user_data = data.model_dump()
        password = user_data.pop("password")
        password_hash = create_hash_password(password)
        new_user = User(**user_data, password_hash=password_hash)
        session.add(new_user)
        await session.commit()
        return new_user

    async def update_user(self, data: UserUpdate, user: User, session: AsyncSession):
        user_data = data.model_dump(exclude_unset=True)
        for k, v in user_data.items():
            setattr(user, k, v)
        await session.commit()
        return user

    async def delete_user(self, uid: str, session: AsyncSession):
        user = await self.get_user_by_id(uid, session)

        if not user:
            return None
        await session.delete(user)
        await session.commit()
        return user
