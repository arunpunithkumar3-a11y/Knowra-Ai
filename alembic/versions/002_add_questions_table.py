"""Add questions table

Revision ID: 002
Revises: 001
Create Date: 2026-09-05 10:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create questions table
    op.create_table(
        'questions',
        sa.Column('uid', pg.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('business_id', pg.UUID(as_uuid=True), sa.ForeignKey('businesses.uid', ondelete='CASCADE'), nullable=False),
        sa.Column('question_text', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_questions_business_id', 'questions', ['business_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_questions_business_id', table_name='questions')
    op.drop_table('questions')
