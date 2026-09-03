from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
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
from src.models.auth_schemas import PasswordReset, UserLogin, UserSignup
from src.services.user import UserService

auth_router = APIRouter()

REFRESH_TOKEN_EXPIRY_DAYS = 2

user_service = UserService()


def get_user_service() -> UserService:
    return user_service


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def user_signup(
    data: UserSignup,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    if await service.user_exists(data.email, session):
        raise ConflictError(detail="User with this email already exists")

    await service.create_user(data, session)
    send_welcome_message.delay(data.email)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Account created successfully"},
    )


@auth_router.post("/login")
async def user_login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
    service: UserService = Depends(get_user_service),
):
    user = await service.get_user_by_email(data.email, session)
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
    send_welcome_message.delay(user.email)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token, "refresh_token": refresh_token},
    )


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
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        },
    )


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
async def password_reset_request(email: str):
    token = create_url_safe_token({"email": email})
    link = f"http://{configure.DOMAIN}/api/auth/password_reset_confirm/{token}"
    html_message = f"""
    <h1>Reset Your Password</h1>
    <p>Please click this <a href="{link}">link</a> to Reset Your Password</p>
    """
    send_password_reset_link.delay(email=email, _body=html_message)
    return JSONResponse(
        content={
            "message": "Please Check your email for instructions to reset your password"
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/password_reset_confirm/{token}")
async def password_reset_confirm(
    token: str, data: PasswordReset, session: AsyncSession = Depends(get_session)
):

    if data.new_password != data.confirm_new_password:
        raise HTTPException(
            detail="Passwords do not match", status_code=status.HTTP_400_BAD_REQUEST
        )
    token_data = decode_url_safe_token(token)
    user_email = token_data.get("email")
    if user_email:
        user = await user_service.get_user_by_email(email=user_email, session=session)
        if not user:
            raise NotFoundError(detail="User Not Found")
        await user_service.update_user(
            data={"password_hash": create_hash_password(data.new_password)},
            user_id=user.uid,
            session=session,
        )
        return JSONResponse(
            content={"message": "Password Reset Successfully"},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"message": "Error Occured during password reset"},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
