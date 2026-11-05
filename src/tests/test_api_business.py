from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.business import (
    create_business,
    deleted_business,
    get_all_business,
    get_business,
    get_widget_info,
    update_business,
)
from src.exceptions import AuthenticationError, AuthorizationError, NotFoundError, ValidationError
from src.models.business_schemas import BusinessCreate, BusinessUpdate


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def token_details(owner_id):
    return {"user_data": {"user_id": str(owner_id)}}


@pytest.fixture
def business(owner_id):
    return MagicMock(
        uid=uuid4(),
        owner_id=owner_id,
        business_name="Test Enterprise",
        description="A great enterprise",
        public_key="pk_enterprise",
    )


@pytest.mark.asyncio
async def test_get_business_success(session, token_details, business):
    with patch("src.api.business.business_service.get_business_by_id", new=AsyncMock(return_value=business)):
        res = await get_business(str(business.uid), session, token_details)

    assert res is business


@pytest.mark.asyncio
async def test_get_business_not_found(session, token_details):
    with patch("src.api.business.business_service.get_business_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await get_business(str(uuid4()), session, token_details)


@pytest.mark.asyncio
async def test_get_business_unauthorized(session, token_details, business):
    business.owner_id = uuid4()
    with patch("src.api.business.business_service.get_business_by_id", new=AsyncMock(return_value=business)):
        with pytest.raises(AuthorizationError):
            await get_business(str(business.uid), session, token_details)


@pytest.mark.asyncio
async def test_get_all_business(session, token_details, business):
    with patch("src.api.business.business_service.get_businesses_by_owner", new=AsyncMock(return_value=[business])):
        res = await get_all_business(session, token_details)

    assert res == [business]


@pytest.mark.asyncio
async def test_create_business_success(session, token_details, business):
    data = BusinessCreate(business_name="My Company", description="Info")

    with patch("src.api.business.business_service.create_business", new=AsyncMock(return_value=business)):
        res = await create_business(data, session, token_details)

    assert res is business


@pytest.mark.asyncio
async def test_create_business_missing_name(session, token_details):
    data = BusinessCreate(business_name="   ")

    with pytest.raises(ValidationError):
        await create_business(data, session, token_details)


@pytest.mark.asyncio
async def test_update_business_success(session, token_details, business):
    data = BusinessUpdate(business_name="Updated Company")

    with patch("src.api.business.business_service.get_business_by_id", new=AsyncMock(return_value=business)), \
         patch("src.api.business.business_service.update_business", new=AsyncMock(return_value=business)):
        res = await update_business(str(business.uid), data, session, token_details)

    assert res is business


@pytest.mark.asyncio
async def test_delete_business_success(session, token_details, business):
    with patch("src.api.business.business_service.get_business_by_id", new=AsyncMock(return_value=business)), \
         patch("src.api.business.business_service.delete_business", new=AsyncMock(return_value=business)):
        res = await deleted_business(str(business.uid), session, token_details)

    assert res["message"] == "Business deleted successfully"


@pytest.mark.asyncio
async def test_get_widget_info_success(session, business):
    with patch("src.api.business.business_service.get_business_by_public_key", new=AsyncMock(return_value=business)):
        info = await get_widget_info(business.public_key, session)

    assert info["business_name"] == business.business_name
    assert "welcome_message" in info


@pytest.mark.asyncio
async def test_get_widget_info_not_found(session):
    with patch("src.api.business.business_service.get_business_by_public_key", new=AsyncMock(return_value=None)):
        with pytest.raises(NotFoundError):
            await get_widget_info("pk_nonexistent", session)
