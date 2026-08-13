from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession
from src.config import configure
from src.db.model import User,Org,Document,Chats,Message


engine = create_async_engine(configure.DATABASE_URL,echo=True)

async def init_db():
    from src.db.model import User,Org,Document,Chats,Message

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session():
    Session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)        
    async with Session() as session:
        yield session

