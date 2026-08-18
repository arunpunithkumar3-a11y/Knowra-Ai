import logging
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import configure
from src.core.main import get_session
from src.models.database import User
from src.services.user import UserService

ACCESS_TOKEN_EXPIRY = 3600

security = HTTPBearer()


def create_access_token(data: dict, refresh: bool = False, expire: timedelta = None):
    expiry = datetime.now(timezone.utc) + (
        expire if expire else timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    )

    payload = {
        "user_data": data,
        "jti": str(uuid.uuid4()),
        "exp": expiry,
        "refresh": refresh,
    }

    token = jwt.encode(payload, configure.JWT_SECRET, algorithm=configure.JWT_ALGORITHM)

    return token


def decode_access_token(token):
    try:
        token_data = jwt.decode(
            token, configure.JWT_SECRET, algorithms=[configure.JWT_ALGORITHM]
        )
        return token_data

    except jwt.ExpiredSignatureError:
        logging.warning("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    except jwt.InvalidTokenError as e:
        logging.exception(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = credentials.credentials
    token_data = decode_access_token(token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_data = token_data.get("user_data", {})
    user_id = user_data.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_service = UserService(session)
    user = await user_service.get_user_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
