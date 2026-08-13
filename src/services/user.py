from src.db.model import User
from sqlmodel import select
from sqlalchemy.ext.asyncio.session import AsyncSession
from src.auth.utils import create_hash_password
from src.auth.schemas import UserSignup

class UserService:
     
    async def get_user_by_id(self,uid:str,session:AsyncSession):
        data = select(User).where(User.uid==uid)
        result = await session.execute(data)
        user = result.scalars().first() 
        return user

    async def get_user_by_email(self,email:str,session:AsyncSession):
        data = select(User).where(User.email==email)
        result = await session.execute(data)
        user = result.scalars().first() 
        return user
    
    async def user_exists(self,email:str,session:AsyncSession):
        data = await self.get_user_by_email(email,session)
        return True if data is not None else False
    
    async def create_user(self,data:UserSignup,session):
        user_data = data.model_dump()
        new_user=User(**user_data)
        new_user.password_hash = create_hash_password(user_data["password"])
        session.add(new_user)
        await session.commit()
        return new_user
    

    async def update_user(self,data:UserSignup,user:User,session):
        for k,v in data.items():
            setattr(user,k,v)
        await session.commit()
        return user    

    async def delete_user(self,uid:str,session:AsyncSession):
        user = await self.get_user_by_id(uid,session)

        if not user:
            return None
        await session.delete(user)
        await session.commit()
        return user 
