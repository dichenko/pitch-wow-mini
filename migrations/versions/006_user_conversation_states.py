"""Add persistent user conversation states.

Revision ID: 006
Revises: 005
Create Date: 2026-06-19 00:10:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_conversation_states",
        sa.Column("user_tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("reset_counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_thread_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_user_conversation_states_updated_at",
        "user_conversation_states",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_conversation_states_updated_at",
        table_name="user_conversation_states",
    )
    op.drop_table("user_conversation_states")

