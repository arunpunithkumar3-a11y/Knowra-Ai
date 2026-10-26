import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status

from src.config import configure

ACCESS_TOKEN_EXPIRY = 3600


def create_access_token(
    data: dict,
    refresh: bool = False,
    expire: Optional[timedelta] = None,
) -> str:
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


def decode_access_token(token: str) -> dict:
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
        logging.warning("Invalid token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
