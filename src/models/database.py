import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.dialects import postgresql as pg
from sqlmodel import Field, Relationship, SQLModel

# ============================================================
# ENUMS
# ============================================================


class EmbeddingStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ============================================================
# HELPER
# ============================================================


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# USER
# ============================================================


class User(SQLModel, table=True):
    __tablename__ = "users"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    email: str = Field(
        index=True,
        unique=True,
        max_length=255,
    )

    password_hash: str = Field(exclude=True)

    user_name: str = Field(
        max_length=100,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": "now()"},
    )

    # Relationships

    businesses: List["Business"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    uploaded_documents: List["Documents"] = Relationship(
        back_populates="uploader",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )


class Business(SQLModel, table=True):
    __tablename__ = "businesses"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    owner_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey(
                "users.uid",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    business_name: str = Field(
        max_length=255,
        index=True,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
    )

    website_url: Optional[str] = Field(
        default=None,
        max_length=1024,
    )

    # Public identifier used by the website widget/API.
    public_key: str = Field(
        index=True,
        unique=True,
        max_length=100,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": "now()"},
    )

    # Relationships

    owner: Optional["User"] = Relationship(
        back_populates="businesses",
    )

    documents: List["Documents"] = Relationship(
        back_populates="business",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )


# ============================================================
# DOCUMENT
# ============================================================


class Documents(SQLModel, table=True):
    __tablename__ = "documents"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    business_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey(
                "businesses.uid",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    uploaded_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey(
                "users.uid",
                ondelete="SET NULL",
            ),
            nullable=True,
            index=True,
        ),
    )

    original_filename: str = Field(
        max_length=255,
    )

    file_type: str = Field(
        max_length=100,
    )

    extracted_text: Optional[str] = Field(
        default=None,
        sa_column=Column(
            Text,
            nullable=True,
        ),
    )
    document_chunks: Optional[List[dict]] = Field(
        default=None,
        sa_column=Column(
            pg.JSONB,
            nullable=True,
        ),
    )
    embedding_status: EmbeddingStatus = Field(
        default=EmbeddingStatus.pending,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": "now()"},
    )

    business: Optional["Business"] = Relationship(
        back_populates="documents",
    )

    uploader: Optional["User"] = Relationship(
        back_populates="uploaded_documents",
    )


# Backwards compatibility alias
Document = Documents
