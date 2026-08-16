from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrgBase(BaseModel):
    org_name: str
    description: Optional[str] = None


class OrgCreate(OrgBase):
    pass


class OrgUpdate(OrgBase):
    pass


class OrgRead(OrgBase):
    model_config = ConfigDict(from_attributes=True)
    
    uid: UUID
    user_id: UUID
    created_at: datetime


class OrgWithMembers(OrgRead):
    members: list["OrgMemberRead"] = []


class OrgMemberBase(BaseModel):
    user_id: UUID
    org_id: UUID


class OrgMemberRead(OrgMemberBase):
    model_config = ConfigDict(from_attributes=True)
    
    uid: UUID
    joined_at: datetime