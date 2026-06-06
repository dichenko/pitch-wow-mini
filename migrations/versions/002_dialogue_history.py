"""Add dialogue history table.

Revision ID: 002
Revises: 001
Create Date: 2026-06-06 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dialogue_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("assistant_response", sa.Text(), nullable=False),
        sa.Column("llm_provider", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_dialogue_history_user_thread_created_at",
        "dialogue_history",
        ["user_tg_id", "thread_id", "created_at"],
    )
    op.create_index(
        "ix_dialogue_history_trace_id",
        "dialogue_history",
        ["trace_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dialogue_history_trace_id", table_name="dialogue_history")
    op.drop_index(
        "ix_dialogue_history_user_thread_created_at",
        table_name="dialogue_history",
    )
    op.drop_table("dialogue_history")
