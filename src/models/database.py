import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Text, UniqueConstraint
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

    uploaded_documents: List["Document"] = Relationship(
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

    documents: List["Document"] = Relationship(
        back_populates="business",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )

    chats: List["Chat"] = Relationship(
        back_populates="business",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )


# ============================================================
# DOCUMENT
# ============================================================


class Document(SQLModel, table=True):
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

    chunks: List["DocumentChunk"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        },
    )


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    document_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey(
                "documents.uid",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
        )
    )

    chunk_index: int = Field(
        nullable=False,
    )

    content: str = Field(
        sa_column=Column(
            Text,
            nullable=False,
        )
    )

    embedding: Optional[List[float]] = Field(
        default=None,
        sa_column=Column(
            Vector(1536),
            nullable=True,
        ),
    )

    chunk_metadata: Optional[dict] = Field(
        default=None,
        sa_column=Column(
            "metadata",
            pg.JSONB,
            nullable=True,
        ),
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": "now()"},
    )

    document: Optional["Document"] = Relationship(
        back_populates="chunks",
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunk_index",
        ),
    )


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    uid: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        )
    )

    user_id: Optional[uuid.UUID] = Field(
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

    thread_id: str = Field(
        index=True,
        max_length=255,
    )

    chat_title: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": "now()"},
    )

    user: Optional["User"] = Relationship(
        back_populates="chats",
    )

    business: Optional["Business"] = Relationship(
        back_populates="chats",
    )
