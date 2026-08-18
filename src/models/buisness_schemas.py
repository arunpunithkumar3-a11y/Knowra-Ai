from typing import Optional

from pydantic import BaseModel


class BusinessCreate(BaseModel):
    business_name: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
    public_key: Optional[str] = None


class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    description: Optional[str] = None
    website_url: Optional[str] = None
