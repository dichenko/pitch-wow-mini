"""Replace daily scheduling with inactivity-based conversation reports.

Revision ID: 008
Revises: 007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dialogue_history", sa.Column("user_message_at", sa.DateTime(timezone=True)))
    op.create_table(
        "inactivity_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("last_history_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_user_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_name", sa.Text()),
        sa.Column("last_name", sa.Text()),
        sa.Column("username", sa.Text()),
        sa.Column("transcript_markdown", sa.Text(), nullable=False),
        sa.Column("review_text", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("superseded_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.UniqueConstraint("user_tg_id", "last_history_id", name="uq_inactivity_review_history"),
    )
    op.create_index("ix_inactivity_reviews_delivery", "inactivity_reviews",
                    ["sent_at", "superseded_at", "next_attempt_at"])


def downgrade() -> None:
    op.drop_index("ix_inactivity_reviews_delivery", table_name="inactivity_reviews")
    op.drop_table("inactivity_reviews")
    op.drop_column("dialogue_history", "user_message_at")
