import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel


class OrgRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class JoinRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    email: str = Field(index=True, unique=True)
    password_hash: str = Field(exclude=True)
    user_name: str

    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    memberships: List["OrgMember"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    join_requests: List["JoinRequest"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    chats: List["ChatState"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class Org(SQLModel, table=True):
    __tablename__ = "orgs"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    org_name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None

    plan: str = Field(default="free")

    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    members: List["OrgMember"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    join_requests: List["JoinRequest"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    documents: List["Document"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    chats: List["ChatState"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={"lazy": "selectin"},
    )


class OrgMember(SQLModel, table=True):
    __tablename__ = "org_members"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    user_id: uuid.UUID = Field(
        foreign_key="users.uid",
        index=True,
    )

    org_id: uuid.UUID = Field(
        foreign_key="orgs.uid",
        index=True,
    )

    role: OrgRole = Field(default=OrgRole.member)

    joined_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    user: Optional["User"] = Relationship(back_populates="memberships")

    org: Optional["Org"] = Relationship(back_populates="members")


class JoinRequest(SQLModel, table=True):
    __tablename__ = "join_requests"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    user_id: uuid.UUID = Field(
        foreign_key="users.uid",
        index=True,
    )

    org_id: uuid.UUID = Field(
        foreign_key="orgs.uid",
        index=True,
    )

    status: JoinRequestStatus = Field(default=JoinRequestStatus.pending)

    requested_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    reviewed_at: Optional[datetime] = None

    reviewed_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.uid",
    )

    user: Optional["User"] = Relationship(back_populates="join_requests")

    org: Optional["Org"] = Relationship(back_populates="join_requests")


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    org_id: uuid.UUID = Field(
        foreign_key="orgs.uid",
        index=True,
    )

    uploaded_by: uuid.UUID = Field(
        foreign_key="users.uid",
        index=True,
    )

    title: str
    file_path: str

    embedding_status: str = Field(default="pending")

    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    org: Optional["Org"] = Relationship(back_populates="documents")


class ChatState(SQLModel, table=True):
    __tablename__ = "chats"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    user_uid: uuid.UUID = Field(
        foreign_key="users.uid",
        index=True,
    )

    org_id: uuid.UUID = Field(
        foreign_key="orgs.uid",
        index=True,
    )

    thread_id: str = Field(index=True)

    chat_title: str

    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))

    user: Optional["User"] = Relationship(back_populates="chats")

    org: Optional["Org"] = Relationship(back_populates="chats")
