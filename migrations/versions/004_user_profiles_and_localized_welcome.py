"""Add user profiles and localized welcome prompt kinds.

Revision ID: 004
Revises: 003
Create Date: 2026-06-10 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOCALIZED_PROMPT_KIND_CHECK = (
    "kind IN ("
    "'system_prompt', 'tools_instruction', 'censor_prompt', "
    "'welcome_message', 'welcome_message_ru', 'welcome_message_uz', "
    "'welcome_message_en'"
    ")"
)

LEGACY_PROMPT_KIND_CHECK = (
    "kind IN ('system_prompt', 'tools_instruction', 'censor_prompt', 'welcome_message')"
)


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("tg_id", sa.BigInteger(), primary_key=True),
        sa.Column("preferred_language", sa.Text(), nullable=True),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("language_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "preferred_language IS NULL OR preferred_language IN ('ru', 'uz', 'en')",
            name="check_user_profiles_preferred_language",
        ),
    )
    op.create_index(
        "ix_user_profiles_preferred_language",
        "user_profiles",
        ["preferred_language"],
    )

    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        LOCALIZED_PROMPT_KIND_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        LEGACY_PROMPT_KIND_CHECK,
    )
    op.drop_index("ix_user_profiles_preferred_language", table_name="user_profiles")
    op.drop_table("user_profiles")
