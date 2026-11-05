from datetime import timedelta
import pytest
from fastapi import HTTPException

from src.core.dependency import create_url_safe_token, decode_url_safe_token
from src.core.password import create_hash_password, verify_password
from src.core.security import create_access_token, decode_access_token


def test_password_hash_and_verify():
    password = "SuperSecretPassword123"
    hashed = create_hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_and_decode_access_token():
    payload = {"user_id": "12345", "email": "user@example.com"}
    token = create_access_token(payload)

    decoded = decode_access_token(token)

    assert decoded["user_data"] == payload
    assert decoded["refresh"] is False
    assert "exp" in decoded
    assert "jti" in decoded


def test_create_and_decode_refresh_token():
    payload = {"user_id": "12345", "email": "user@example.com"}
    token = create_access_token(payload, refresh=True)

    decoded = decode_access_token(token)

    assert decoded["user_data"] == payload
    assert decoded["refresh"] is True


def test_decode_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("invalid.token.value")

    assert exc_info.value.status_code == 401
    assert "Invalid token" in exc_info.value.detail


def test_decode_expired_token():
    payload = {"user_id": "12345"}
    token = create_access_token(payload, expire=timedelta(seconds=-10))

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401
    assert "Token expired" in exc_info.value.detail


def test_url_safe_token():
    data = {"email": "reset@example.com"}
    token = create_url_safe_token(data)

    decoded = decode_url_safe_token(token)

    assert decoded == data


def test_decode_invalid_url_safe_token():
    with pytest.raises(HTTPException) as exc_info:
        decode_url_safe_token("corrupted_or_invalid_token")

    assert exc_info.value.status_code == 400
