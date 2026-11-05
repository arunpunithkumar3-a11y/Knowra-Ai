import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import NotFoundError, ValidationError
from src.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Knowra API"


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_schema_generation():
    # Verify the OpenAPI documentation schema compiles without error
    openapi = app.openapi()
    assert openapi["info"]["title"] == "Knowra API"
    assert "/health" in openapi["paths"]
    assert "/api/v1/auth/signup" in openapi["paths"]
    assert "/api/v1/create_document/{business_id}" in openapi["paths"]


@pytest.mark.asyncio
async def test_app_exception_handler():
    # Test that AppException returns structured JSON instead of 500
    from fastapi import APIRouter

    test_router = APIRouter()

    @test_router.get("/test-not-found")
    async def trigger_not_found():
        raise NotFoundError(detail="Custom resource missing")

    @test_router.get("/test-validation")
    async def trigger_validation():
        raise ValidationError(detail="Invalid parameter specified")

    app.include_router(test_router)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res404 = await ac.get("/test-not-found")
        assert res404.status_code == 404
        assert res404.json()["detail"] == "Custom resource missing"

        res400 = await ac.get("/test-validation")
        assert res400.status_code == 400
        assert res400.json()["detail"] == "Invalid parameter specified"
