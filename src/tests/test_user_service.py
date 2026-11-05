from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.user import UserService


@pytest.fixture
def service():
    return UserService()


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.delete = AsyncMock()
    return mock_session


@pytest.fixture
def user():
    return MagicMock(
        uid=uuid4(),
        email="test@example.com",
        user_name="Test User",
    )


@pytest.mark.asyncio
async def test_get_user_by_id_found(service, session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result

    found_user = await service.get_user_by_id(user.uid, session)

    assert found_user is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_id_string_uuid(service, session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result

    found_user = await service.get_user_by_id(str(user.uid), session)

    assert found_user is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_by_id_invalid_uuid(service, session):
    found_user = await service.get_user_by_id("not-a-valid-uuid", session)

    assert found_user is None
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(service, session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    found_user = await service.get_user_by_id(uuid4(), session)

    assert found_user is None


@pytest.mark.asyncio
async def test_get_user_by_email_found(service, session, user):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    session.execute.return_value = result

    found_user = await service.get_user_by_email("test@example.com", session)

    assert found_user is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_exists_true(service, session, user):
    service.get_user_by_email = AsyncMock(return_value=user)

    exists = await service.user_exists("test@example.com", session)

    assert exists is True
    service.get_user_by_email.assert_awaited_once_with("test@example.com", session)


@pytest.mark.asyncio
async def test_user_exists_false(service, session):
    service.get_user_by_email = AsyncMock(return_value=None)

    exists = await service.user_exists("missing@example.com", session)

    assert exists is False


@pytest.mark.asyncio
async def test_create_user(service, session):
    signup_data = MagicMock()
    signup_data.model_dump.return_value = {
        "email": "new@example.com",
        "password": "plain_password",
        "role": "admin",
    }

    with patch(
        "src.services.user.create_hash_password",
        return_value="secure_hash",
    ) as hash_password:
        created_user = await service.create_user(signup_data, session)

    hash_password.assert_called_once_with("plain_password")

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(created_user)

    assert created_user.password_hash == "secure_hash"
    assert getattr(created_user, "password", None) != "plain_password"
    assert getattr(created_user, "role", None) != "admin"


@pytest.mark.asyncio
async def test_update_user_found(service, session, user):
    service.get_user_by_id = AsyncMock(return_value=user)

    updated_user = await service.update_user(
        {"email": "updated@example.com"},
        user.uid,
        session,
    )

    assert updated_user is user
    assert user.email == "updated@example.com"
    service.get_user_by_id.assert_awaited_once_with(user.uid, session)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update_user_not_found(service, session):
    service.get_user_by_id = AsyncMock(return_value=None)

    updated_user = await service.update_user(
        {"email": "updated@example.com"},
        uuid4(),
        session,
    )

    assert updated_user is None
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_user_found(service, session, user):
    service.get_user_by_id = AsyncMock(return_value=user)

    deleted_user = await service.delete_user(user.uid, session)

    assert deleted_user is user
    session.delete.assert_awaited_once_with(user)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_user_not_found(service, session):
    service.get_user_by_id = AsyncMock(return_value=None)

    deleted_user = await service.delete_user(uuid4(), session)

    assert deleted_user is None
    session.delete.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_all_users(service, session, user):
    result = MagicMock()
    result.scalars.return_value.all.return_value = [user]
    session.execute.return_value = result

    users = await service.get_all_users(session)

    assert len(users) == 1
    assert users[0] is user


@pytest.mark.asyncio
async def test_get_all_users_pagination(service, session):
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    users = await service.get_all_users(session, skip=20, limit=10)

    assert users == []
    session.execute.assert_awaited_once()
