import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.api import auth_router, org_router
from src.core.main import init_db
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
    await init_db()
    yield
    logger.info("Application shutting down...")


app = FastAPI(
    title="Knowra API",
    description="Production-grade API with authentication and organization management",
    version="1.0.0",
    lifespan=lifespan,
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


@app.get("/health/ready")
async def readiness_check():
    return {"status": "ready", "service": "knowra-api"}


app.include_router(auth_router, prefix="/api/auth")
app.include_router(org_router, prefix="/api/orgs")
