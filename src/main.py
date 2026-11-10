import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.auth import auth_router
from src.api.business import business_router
from src.api.chat import agent_router
from src.api.document import document_router
from src.api.feature import feature_router
from src.core.main import init_db
from src.core.redis import close_memory, redis_client
from src.exceptions import AppException

logger = logging.getLogger("knowra")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    logger.info("Initializing Knowra application...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning("Database initialization deferred/failed: %s", e)

    try:
        await redis_client.ping()
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.warning("Redis connection check failed: %s", e)

    yield

    logger.info("Shutting down Knowra application...")
    await close_memory()
    logger.info("Knowra application stopped cleanly.")


app = FastAPI(
    title="Knowra API",
    description="Enterprise Multi-Tenant Agentic RAG Platform with Hybrid Retrieval, LangGraph ReAct Agents, and Asynchronous Celery Processing.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for domain/application exceptions
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
        },
    )


# Health check endpoint
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Knowra API",
        "version": "1.0.0",
    }


# Include Routers
# Primary API v1 namespace
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(business_router, prefix="/api/v1", tags=["Business"])
app.include_router(agent_router, prefix="/api/v1", tags=["Chat & Agent"])
app.include_router(document_router, prefix="/api/v1", tags=["Documents"])
app.include_router(feature_router, prefix="/api/v1", tags=["Features & Analytics"])

# Direct root aliases for convenience and backwards-compatibility
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(business_router, tags=["Business"])
app.include_router(agent_router, tags=["Chat & Agent"])
app.include_router(document_router, tags=["Documents"])
app.include_router(feature_router, tags=["Features & Analytics"])
