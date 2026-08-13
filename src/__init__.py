from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.auth.routers import auth_router


@asynccontextmanager
async def lifespan(app:FastAPI):
    print("starting up...")
    await init_db()
    yield
    print("shutting down..")


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router,prefix="/api/auth")