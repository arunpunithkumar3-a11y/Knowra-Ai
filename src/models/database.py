import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import Column, ForeignKey, Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class UserRole(str, Enum):
    admin = "admin"
    member = "member"


class JoinRequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class EmbeddingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    email: str = Field(index=True, unique=True, max_length=255)
    password_hash: str = Field(exclude=True)
    user_name: str = Field(max_length=100)
    role: UserRole = Field(default=UserRole.member)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    created_orgs: List["Org"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    memberships: List["OrgMember"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    join_requests: List["JoinRequest"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "foreign_keys": "[JoinRequest.user_id]",
        },
    )

    documents: List["Document"] = Relationship(
        back_populates="uploader",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    chats: List["Chat"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
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
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    org_name: str = Field(index=True, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    owner: Optional["User"] = Relationship(back_populates="created_orgs")

    members: List["OrgMember"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    join_requests: List["JoinRequest"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    documents: List["Document"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    chats: List["Chat"] = Relationship(
        back_populates="org",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
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
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    org_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("orgs.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    org: Optional["Org"] = Relationship(back_populates="members")
    user: Optional["User"] = Relationship(back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_org_members_user_org"),
    )


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
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    org_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("orgs.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    status: JoinRequestStatus = Field(default=JoinRequestStatus.pending)

    requested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    reviewed_at: Optional[datetime] = None

    reviewed_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    user: Optional["User"] = Relationship(
        back_populates="join_requests",
        sa_relationship_kwargs={"foreign_keys": "[JoinRequest.user_id]"},
    )
    org: Optional["Org"] = Relationship(back_populates="join_requests")

    __table_args__ = (
        Index(
            "uq_pending_join_requests",
            "user_id",
            "org_id",
            unique=True,
            postgresql_where=(status == JoinRequestStatus.pending),
        ),
    )


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
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("orgs.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    uploaded_by: Optional[uuid.UUID] = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="SET NULL"),
            nullable=True,
            index=True,
        )
    )

    title: str = Field(max_length=255)
    file_path: str = Field(max_length=1024)

    embedding_status: EmbeddingStatus = Field(default=EmbeddingStatus.pending)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    org: Optional["Org"] = Relationship(back_populates="documents")
    uploader: Optional["User"] = Relationship(back_populates="documents")


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    org_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("orgs.uid", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )

    thread_id: str = Field(index=True, max_length=255)
    chat_title: str = Field(max_length=255)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        sa_column_kwargs={"server_default": "now()"},
    )

    user: Optional["User"] = Relationship(back_populates="chats")
    org: Optional["Org"] = Relationship(back_populates="chats")
