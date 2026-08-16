from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserSignup(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    user_name: str = Field(..., min_length=2, max_length=100)
    role: Literal["member", "admin"] = Field(default="member")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., max_length=128)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    user_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role: Optional[Literal["member", "admin"]] = Field(default=None)
