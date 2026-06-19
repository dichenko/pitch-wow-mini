"""Add artifact generator prompt kind and jobs.

Revision ID: 005
Revises: 004
Create Date: 2026-06-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ARTIFACT_PROMPT_KIND_CHECK = (
    "kind IN ("
    "'system_prompt', 'tools_instruction', 'censor_prompt', "
    "'welcome_message', 'welcome_message_ru', 'welcome_message_uz', "
    "'welcome_message_en', 'artifact_generator_prompt'"
    ")"
)

LOCALIZED_PROMPT_KIND_CHECK = (
    "kind IN ("
    "'system_prompt', 'tools_instruction', 'censor_prompt', "
    "'welcome_message', 'welcome_message_ru', 'welcome_message_uz', "
    "'welcome_message_en'"
    ")"
)


def upgrade() -> None:
    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        ARTIFACT_PROMPT_KIND_CHECK,
    )

    op.create_table(
        "artifact_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=False),
        sa.Column("user_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("input_comment", sa.Text(), nullable=True),
        sa.Column("input_dialogue_md", sa.Text(), nullable=True),
        sa.Column("artifact_prompt_version", sa.Integer(), nullable=True),
        sa.Column("artifact_model_provider", sa.Text(), nullable=True),
        sa.Column("artifact_model", sa.Text(), nullable=True),
        sa.Column("output_markdown", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'success', 'error')",
            name="check_artifact_job_status",
        ),
    )
    op.create_index(
        "ix_artifact_jobs_status_created_at",
        "artifact_jobs",
        ["status", "created_at"],
    )
    op.create_index("ix_artifact_jobs_trace_id", "artifact_jobs", ["trace_id"])
    op.create_index(
        "ix_artifact_jobs_user_tg_id_created_at",
        "artifact_jobs",
        ["user_tg_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_artifact_jobs_user_tg_id_created_at", table_name="artifact_jobs")
    op.drop_index("ix_artifact_jobs_trace_id", table_name="artifact_jobs")
    op.drop_index("ix_artifact_jobs_status_created_at", table_name="artifact_jobs")
    op.drop_table("artifact_jobs")

    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        LOCALIZED_PROMPT_KIND_CHECK,
    )

