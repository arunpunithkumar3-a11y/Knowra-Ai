from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.api.auth import (
    password_reset_confirm,
    password_reset_request,
    refresh_token_endpoint,
    user_login,
    user_logout,
    user_logout_by_param,
    user_signup,
)
from src.exceptions import AuthenticationError, ConflictError, NotFoundError, ValidationError
from src.models.auth_schemas import PasswordReset, PasswordResetRequest, UserLogin, UserSignup


@pytest.fixture
def session():
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


@pytest.fixture
def user():
    return MagicMock(
        uid=uuid4(),
        email="test@example.com",
        password_hash="hashed_pw",
    )


@pytest.mark.asyncio
async def test_user_signup_success(session):
    signup_data = UserSignup(
        email="newuser@example.com",
        password="secretpassword",
        user_name="newuser",
    )

    with patch("src.api.auth.user_service.user_exists", new=AsyncMock(return_value=False)), \
         patch("src.api.auth.user_service.create_user", new=AsyncMock()), \
         patch("src.api.auth.send_welcome_message.delay") as mock_delay:
        response = await user_signup(signup_data, session)

    assert response == {"message": "Account created successfully"}
    mock_delay.assert_called_once_with("newuser@example.com")


@pytest.mark.asyncio
async def test_user_signup_conflict(session):
    signup_data = UserSignup(
        email="existing@example.com",
        password="secretpassword",
    )

    with patch("src.api.auth.user_service.user_exists", new=AsyncMock(return_value=True)):
        with pytest.raises(ConflictError) as exc_info:
            await user_signup(signup_data, session)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_user_login_success(session, user):
    login_data = UserLogin(email="test@example.com", password="password123")

    with patch("src.api.auth.user_service.get_user_by_email", new=AsyncMock(return_value=user)), \
         patch("src.api.auth.verify_password", return_value=True):
        response = await user_login(login_data, session)

    assert "access_token" in response
    assert "refresh_token" in response


@pytest.mark.asyncio
async def test_user_login_not_found(session):
    login_data = UserLogin(email="missing@example.com", password="password123")

    with patch("src.api.auth.user_service.get_user_by_email", new=AsyncMock(return_value=None)):
        with pytest.raises(AuthenticationError):
            await user_login(login_data, session)


@pytest.mark.asyncio
async def test_user_login_wrong_password(session, user):
    login_data = UserLogin(email="test@example.com", password="wrongpassword")

    with patch("src.api.auth.user_service.get_user_by_email", new=AsyncMock(return_value=user)), \
         patch("src.api.auth.verify_password", return_value=False):
        with pytest.raises(AuthenticationError):
            await user_login(login_data, session)


@pytest.mark.asyncio
async def test_refresh_token_success():
    token_details = {
        "user_data": {"user_id": str(uuid4()), "email": "user@example.com"},
        "jti": "sample-jti",
    }

    with patch("src.api.auth.add_jti_to_blacklist", new=AsyncMock()) as mock_blacklist:
        response = await refresh_token_endpoint(token_details)

    assert "access_token" in response
    assert "refresh_token" in response
    mock_blacklist.assert_awaited_once_with("sample-jti")


@pytest.mark.asyncio
async def test_refresh_token_invalid_payload():
    with pytest.raises(AuthenticationError):
        await refresh_token_endpoint({})


@pytest.mark.asyncio
async def test_user_logout():
    token_details = {"jti": "jti-to-blacklist"}

    with patch("src.api.auth.add_jti_to_blacklist", new=AsyncMock()) as mock_blacklist:
        response = await user_logout(token_details)

    assert response == {"message": "Logout successful"}
    mock_blacklist.assert_awaited_once_with("jti-to-blacklist")


@pytest.mark.asyncio
async def test_user_logout_by_param_success():
    with patch("src.api.auth.add_jti_to_blacklist", new=AsyncMock()) as mock_blacklist:
        response = await user_logout_by_param("param-jti")

    assert response == {"message": "Logout successful"}
    mock_blacklist.assert_awaited_once_with("param-jti")


@pytest.mark.asyncio
async def test_user_logout_by_param_empty():
    with pytest.raises(ValidationError):
        await user_logout_by_param("   ")


@pytest.mark.asyncio
async def test_password_reset_request_success():
    data = PasswordResetRequest(email="user@example.com")

    with patch("src.api.auth.send_password_reset_link.delay") as mock_delay:
        response = await password_reset_request(data=data)

    assert "message" in response
    mock_delay.assert_called_once()


@pytest.mark.asyncio
async def test_password_reset_request_missing_email():
    with pytest.raises(ValidationError):
        await password_reset_request(data=None, email=None)


@pytest.mark.asyncio
async def test_password_reset_confirm_mismatch(session):
    data = PasswordReset(new_password="pass12345", confirm_new_password="pass54321")

    with pytest.raises(ValidationError):
        await password_reset_confirm("token", data, session)


@pytest.mark.asyncio
async def test_password_reset_confirm_success(session, user):
    data = PasswordReset(new_password="newsecretpass", confirm_new_password="newsecretpass")

    with patch("src.api.auth.decode_url_safe_token", return_value={"email": "test@example.com"}), \
         patch("src.api.auth.user_service.get_user_by_email", new=AsyncMock(return_value=user)), \
         patch("src.api.auth.user_service.update_user", new=AsyncMock()) as mock_update:
        response = await password_reset_confirm("valid-token", data, session)

    assert response == {"message": "Password Reset Successfully"}
    mock_update.assert_awaited_once()
