from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.services.business import BusinessService


@pytest.fixture
def service():
    return BusinessService()


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def business():
    return MagicMock(
        uid=uuid4(),
        business_name="Test Business",
        website_url="https://testbusiness.com",
        description="A test business for unit testing.",
        public_key="pk_testbusiness",
    )


@pytest.mark.asyncio
async def test_get_business_by_id_found(service, session, business):
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found_business = await service.get_business_by_id(business.uid, session)

    assert found_business is business
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_by_id_string_uuid(service, session, business):
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found_business = await service.get_business_by_id(str(business.uid), session)

    assert found_business is business
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_by_id_invalid_uuid(service, session):
    found_business = await service.get_business_by_id("invalid-uuid", session)

    assert found_business is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_business_by_id_not_found(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found_business = await service.get_business_by_id(uuid4(), session)

    assert found_business is None


@pytest.mark.asyncio
async def test_get_business_by_public_key_found(service, session, business):
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found_business = await service.get_business_by_public_key("pk_testbusiness", session)

    assert found_business is business
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_by_public_key_empty(service, session):
    found_business = await service.get_business_by_public_key("", session)

    assert found_business is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_business_by_public_key_not_found(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found_business = await service.get_business_by_public_key("pk_missing", session)

    assert found_business is None


@pytest.mark.asyncio
async def test_get_businesses_by_owner_found(service, session, business):
    owner_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [business]
    session.execute.return_value = result

    businesses = await service.get_businesses_by_owner(owner_id, session)

    assert len(businesses) == 1
    assert businesses[0] is business


@pytest.mark.asyncio
async def test_get_businesses_by_owner_invalid_id(service, session):
    businesses = await service.get_businesses_by_owner("invalid-uuid", session)

    assert businesses == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_businesses_by_owner_pagination(service, session):
    owner_id = uuid4()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    businesses = await service.get_businesses_by_owner(owner_id, session, skip=10, limit=20)

    assert businesses == []
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_with_documents_found(service, session, business):
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found_business = await service.get_business_with_documents(business.uid, session)

    assert found_business is business
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_with_documents_invalid_id(service, session):
    found_business = await service.get_business_with_documents("invalid-uuid", session)

    assert found_business is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_business_with_documents_not_found(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found_business = await service.get_business_with_documents(uuid4(), session)

    assert found_business is None


@pytest.mark.asyncio
async def test_get_business_with_questions_found(service, session, business):
    result = MagicMock()
    result.scalar_one_or_none.return_value = business
    session.execute.return_value = result

    found_business = await service.get_business_with_questions(business.uid, session)

    assert found_business is business
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_business_with_questions_invalid_id(service, session):
    found_business = await service.get_business_with_questions("invalid-uuid", session)

    assert found_business is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_business_explicit_values(service, session):
    owner_id = uuid4()
    business_data = MagicMock()
    business_data.business_name = "Acme Corp"
    business_data.description = "Test Description"
    business_data.website_url = "https://acme.com"
    business_data.public_key = "pk_custom"

    created = await service.create_business(business_data, owner_id, session)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created)
    assert created.business_name == "Acme Corp"
    assert created.description == "Test Description"
    assert created.website_url == "https://acme.com"
    assert created.public_key == "pk_custom"
    assert created.owner_id == owner_id


@pytest.mark.asyncio
async def test_create_business_defaults(service, session):
    owner_id = uuid4()
    business_data = MagicMock()
    business_data.business_name = None
    business_data.name = None
    business_data.description = None
    business_data.website_url = None
    business_data.public_key = None

    created = await service.create_business(business_data, str(owner_id), session)

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created)
    assert created.business_name == "My Business"
    assert created.public_key.startswith("pk_")
    assert created.owner_id == owner_id


@pytest.mark.asyncio
async def test_update_business_found(service, session, business):
    service.get_business_by_id = AsyncMock(return_value=business)
    update_data = MagicMock()
    update_data.model_dump.return_value = {"business_name": "New Name"}

    updated = await service.update_business(business.uid, update_data, session)

    assert updated is business
    assert business.business_name == "New Name"
    service.get_business_by_id.assert_awaited_once_with(business.uid, session)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(business)


@pytest.mark.asyncio
async def test_update_business_not_found(service, session):
    service.get_business_by_id = AsyncMock(return_value=None)
    update_data = MagicMock()

    updated = await service.update_business(uuid4(), update_data, session)

    assert updated is None
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_business_found(service, session, business):
    service.get_business_by_id = AsyncMock(return_value=business)

    deleted = await service.delete_business(business.uid, session)

    assert deleted is business
    session.delete.assert_awaited_once_with(business)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_business_not_found(service, session):
    service.get_business_by_id = AsyncMock(return_value=None)

    deleted = await service.delete_business(uuid4(), session)

    assert deleted is None
    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()
