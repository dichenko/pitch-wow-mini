"""Allow welcome_message prompt kind.

Revision ID: 003
Revises: 002
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        "kind IN ('system_prompt', 'tools_instruction', 'censor_prompt', 'welcome_message')",
    )


def downgrade() -> None:
    op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")
    op.create_check_constraint(
        "check_prompt_kind",
        "prompt_versions",
        "kind IN ('system_prompt', 'tools_instruction', 'censor_prompt')",
    )
