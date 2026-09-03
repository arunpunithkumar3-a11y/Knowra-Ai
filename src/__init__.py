import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api import agent_router, auth_router, business_router, document_router
from src.core.main import get_session, init_db
from src.core.redis import close_memory, redis_client
from src.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NotFoundError,
    ValidationError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    try:
        await asyncio.wait_for(init_db(), timeout=5.0)
    except Exception as e:
        logger.warning(f"Database init warning: {e}")
    yield
    logger.info("Application shutting down...")
    try:
        await close_memory()
    except Exception as e:
        logger.warning(f"Redis shutdown warning: {e}")


app = FastAPI(
    title="Knowra API",
    description="Production-grade AI Knowledge Management API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware for web apps & widget integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    logger.warning(
        f"Application error: {exc.message}",
        extra={"detail": exc.detail, "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "detail": exc.detail},
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found", "detail": str(exc)},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.exception("Internal server error")
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": "An unexpected error occurred",
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "knowra-api"}


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(business_router, prefix="/api/business", tags=["business"])
app.include_router(document_router, prefix="/api/document", tags=["document"])
app.include_router(agent_router, prefix="/api/chat", tags=["chat"])
