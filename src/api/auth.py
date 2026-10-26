from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_tasks import send_password_reset_link, send_welcome_message
from src.config import configure
from src.core.dependency import (
    create_url_safe_token,
    decode_url_safe_token,
    verify_any_token,
    verify_refresh_token,
)
from src.core.main import get_session
from src.core.password import create_hash_password, verify_password
from src.core.redis import add_jti_to_blacklist
from src.core.security import create_access_token
from src.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.models.auth_schemas import (
    PasswordReset,
    PasswordResetRequest,
    UserLogin,
    UserSignup,
)
from src.services.user import user_service

auth_router = APIRouter()

REFRESH_TOKEN_EXPIRY_DAYS = 2


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def user_signup(
    data: UserSignup,
    session: AsyncSession = Depends(get_session),
):
    if await user_service.user_exists(data.email, session):
        raise ConflictError(detail="User with this email already exists")

    await user_service.create_user(data, session)
    try:
        send_welcome_message.delay(data.email)
    except Exception:
        pass

    return {"message": "Account created successfully"}


@auth_router.post("/login")
async def user_login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    user = await user_service.get_user_by_email(data.email, session)
    if not user:
        raise AuthenticationError(detail="Invalid email or password")
    if not verify_password(data.password, user.password_hash):
        raise AuthenticationError(detail="Invalid password")

    access_token = create_access_token(
        data={"email": user.email, "user_id": str(user.uid)}
    )
    refresh_token = create_access_token(
        data={"email": user.email, "user_id": str(user.uid)},
        refresh=True,
        expire=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token}


@auth_router.post("/refresh")
async def refresh_token_endpoint(
    token_details: dict = Depends(verify_refresh_token),
):
    user_data = token_details.get("user_data", {})
    if not user_data:
        raise AuthenticationError(detail="Invalid token payload")
    old_jti = token_details.get("jti")
    if old_jti:
        await add_jti_to_blacklist(old_jti)

    new_access_token = create_access_token(data=user_data)
    new_refresh_token = create_access_token(
        data=user_data,
        refresh=True,
        expire=timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }


@auth_router.post("/logout")
async def user_logout(
    token_details: dict = Depends(verify_any_token),
):
    jti = token_details.get("jti")
    if jti:
        await add_jti_to_blacklist(jti)
    return {"message": "Logout successful"}


@auth_router.post("/logout/{jti}")
async def user_logout_by_param(jti: str):
    if not jti or not jti.strip():
        raise ValidationError(detail="JTI must be provided and cannot be empty")
    await add_jti_to_blacklist(jti.strip())
    return {"message": "Logout successful"}


@auth_router.post("/password_reset")
async def password_reset_request(
    data: Optional[PasswordResetRequest] = None,
    email: Optional[str] = None,
):
    target_email = (data.email if data else email) or ""
    target_email = target_email.strip()
    if not target_email:
        raise ValidationError(detail="Email is required")

    token = create_url_safe_token({"email": target_email})
    domain = getattr(configure, "DOMAIN", "localhost:3000")
    if "://" not in domain:
        domain = f"http://{domain}"
    link = f"{domain}/reset-password/{token}"
    html_message = f"""
    <h1>Reset Your Password</h1>
    <p>Please click this <a href="{link}">link</a> to Reset Your Password</p>
    """
    try:
        send_password_reset_link.delay(email=target_email, _body=html_message)
    except Exception:
        pass

    return {
        "message": "Please Check your email for instructions to reset your password"
    }


@auth_router.get("/password_reset_confirm/{token}")
async def password_reset_confirm_redirect(token: str):
    domain = getattr(configure, "DOMAIN", "localhost:3000")
    if "://" not in domain:
        domain = f"http://{domain}"
    return RedirectResponse(
        url=f"{domain}/reset-password/{token}",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@auth_router.post("/password_reset_confirm/{token}")
async def password_reset_confirm(
    token: str,
    data: PasswordReset,
    session: AsyncSession = Depends(get_session),
):
    if data.new_password != data.confirm_new_password:
        raise ValidationError(detail="Passwords do not match")

    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email") if isinstance(token_data, dict) else None
    if not user_email:
        raise ValidationError(detail="Invalid or expired reset token")

    user = await user_service.get_user_by_email(email=user_email, session=session)
    if not user:
        raise NotFoundError(detail="User Not Found")

    await user_service.update_user(
        data={"password_hash": create_hash_password(data.new_password)},
        user_id=user.uid,
        session=session,
    )
    return {"message": "Password Reset Successfully"}
