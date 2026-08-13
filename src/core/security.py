from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
import uuid
from src.config import configure
import logging


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
ACCESS_TOKEN_EXPIRY = 3600


def create_hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, refresh: bool = False, expire: timedelta = None):
    expiry = datetime.utcnow() + (expire if expire else timedelta(seconds=ACCESS_TOKEN_EXPIRY))

    payload = {
        "user_data": data,
        "jti": str(uuid.uuid4()),
        "exp": expiry,  # ✅ Correct claim name
        "refresh": refresh
    }

    token = jwt.encode(
        payload,
        configure.JWT_SECRET,
        algorithm=configure.JWT_ALGORITHM
    )

    return token


def decode_access_token(token):
    try:
        token_data = jwt.decode(
            token,
            configure.JWT_SECRET,
            algorithms=[configure.JWT_ALGORITHM]
        )
        return token_data

    except jwt.ExpiredSignatureError:
        logging.warning("Token expired")
        return None

    except jwt.InvalidTokenError as e:
        logging.exception(e)
        return None

