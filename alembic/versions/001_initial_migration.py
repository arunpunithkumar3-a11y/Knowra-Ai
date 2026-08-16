"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2026-08-15 14:30:00.000000

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
    # Create enums first
    user_role = sa.Enum('admin', 'member', name='userrole')
    user_role.create(op.get_bind(), checkfirst=True)
    
    join_request_status = sa.Enum('pending', 'approved', 'rejected', name='joinrequeststatus')
    join_request_status.create(op.get_bind(), checkfirst=True)
    
    embedding_status = sa.Enum('pending', 'processing', 'completed', 'failed', name='embeddingstatus')
    embedding_status.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('user_name', sa.String(100), nullable=False),
        sa.Column('role', user_role, nullable=False, server_default='member'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    
    # Create orgs table
    op.create_table(
        'orgs',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('org_name', sa.String(255), nullable=False, index=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_orgs_org_name', 'orgs', ['org_name'], unique=False)
    op.create_index('ix_orgs_user_id', 'orgs', ['user_id'], unique=False)
    
    # Create org_members table
    op.create_table(
        'org_members',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('org_id', pg.UUID(as_uuid=True), sa.ForeignKey('orgs.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('joined_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('user_id', 'org_id', name='uq_org_members_user_org'),
    )
    op.create_index('ix_org_members_user_id', 'org_members', ['user_id'], unique=False)
    op.create_index('ix_org_members_org_id', 'org_members', ['org_id'], unique=False)
    
    # Create join_requests table
    op.create_table(
        'join_requests',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('org_id', pg.UUID(as_uuid=True), sa.ForeignKey('orgs.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', join_request_status, nullable=False, server_default='pending'),
        sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_join_requests_user_id', 'join_requests', ['user_id'], unique=False)
    op.create_index('ix_join_requests_org_id', 'join_requests', ['org_id'], unique=False)
    op.create_index('ix_join_requests_status', 'join_requests', ['status'], unique=False)
    # Partial unique index for pending join requests (PostgreSQL specific)
    op.execute('''
        CREATE UNIQUE INDEX uq_pending_join_requests 
        ON join_requests (user_id, org_id) 
        WHERE status = 'pending'
    ''')
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', pg.UUID(as_uuid=True), sa.ForeignKey('orgs.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('uploaded_by', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(1024), nullable=False),
        sa.Column('embedding_status', embedding_status, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_documents_org_id', 'documents', ['org_id'], unique=False)
    op.create_index('ix_documents_uploaded_by', 'documents', ['uploaded_by'], unique=False)
    op.create_index('ix_documents_embedding_status', 'documents', ['embedding_status'], unique=False)
    
    # Create chats table
    op.create_table(
        'chats',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', pg.UUID(as_uuid=True), sa.ForeignKey('users.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('org_id', pg.UUID(as_uuid=True), sa.ForeignKey('orgs.uid', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('thread_id', sa.String(255), nullable=False, index=True),
        sa.Column('chat_title', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_chats_user_id', 'chats', ['user_id'], unique=False)
    op.create_index('ix_chats_org_id', 'chats', ['org_id'], unique=False)
    op.create_index('ix_chats_thread_id', 'chats', ['thread_id'], unique=False)


def downgrade() -> None:
    op.drop_table('chats')
    op.drop_table('documents')
    op.drop_table('join_requests')
    op.drop_table('org_members')
    op.drop_table('orgs')
    op.drop_table('users')
    
    # Drop enums
    sa.Enum(name='embeddingstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='joinrequeststatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='userrole').drop(op.get_bind(), checkfirst=True)