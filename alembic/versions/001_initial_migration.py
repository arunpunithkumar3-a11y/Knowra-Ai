"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2026-08-29 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    embedding_status = sa.Enum('pending', 'processing', 'completed', 'failed', name='embeddingstatus')
    embedding_status.create(op.get_bind(), checkfirst=True)

    # Create users table
    op.create_table(
        'users',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('user_name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Create businesses table
    op.create_table(
        'businesses',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('owner_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('business_name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('website_url', sa.String(1024), nullable=True),
        sa.Column('public_key', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_businesses_owner_id', 'businesses', ['owner_id'], unique=False)
    op.create_index('ix_businesses_business_name', 'businesses', ['business_name'], unique=False)
    op.create_index('ix_businesses_public_key', 'businesses', ['public_key'], unique=True)

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('business_id', pg.UUID(as_uuid=True), sa.ForeignKey('businesses.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('uploaded_by', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(100), nullable=False),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('document_chunks', pg.JSONB, nullable=True),
        sa.Column('embedding_status', embedding_status, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_documents_business_id', 'documents', ['business_id'], unique=False)
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'], unique=False)
    op.create_index('ix_documents_embedding_status', 'documents', ['embedding_status'], unique=False)


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('businesses')
    op.drop_table('users')

    # Drop enums
    sa.Enum(name='embeddingstatus').drop(op.get_bind(), checkfirst=True)