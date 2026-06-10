"""Welcome message service — retrieves localized welcome and persists to history."""

import logging

from sqlalchemy import select

from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.history_service import save_dialogue_turn_best_effort
from packages.shared.models.database import PromptVersion
from packages.shared.utils.languages import DEFAULT_LANGUAGE, Language, normalize_preferred_language
from packages.shared.utils.welcome_messages import (
    DEFAULT_WELCOME,
    DEFAULT_WELCOME_MESSAGES,
    WELCOME_PROMPT_KINDS,
    get_default_welcome_message,
    get_welcome_prompt_kind,
)

logger = logging.getLogger(__name__)


async def get_active_welcome_message(language: str | None = None) -> str:
    """Return active localized welcome content from DB or fallback default."""
    normalized = normalize_preferred_language(language) or DEFAULT_LANGUAGE
    kind = WELCOME_PROMPT_KINDS[normalized]
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromptVersion.content).where(
                PromptVersion.kind == kind,
                PromptVersion.is_active == True,
            )
        )
        content = result.scalar_one_or_none()
        if content:
            return content

        if normalized == "ru":
            result = await session.execute(
                select(PromptVersion.content).where(
                    PromptVersion.kind == "welcome_message",
                    PromptVersion.is_active == True,
                )
            )
            legacy_content = result.scalar_one_or_none()
            if legacy_content:
                return legacy_content

        return DEFAULT_WELCOME_MESSAGES[normalized]


async def persist_welcome_to_history(
    user_tg_id: int,
    thread_id: str,
    trace_id: str,
    welcome_text: str,
) -> None:
    """Save the welcome message as an assistant dialogue record.

    Uses an empty user_message so the welcome appears before the
    first real user message in chronological order.
    """
    await save_dialogue_turn_best_effort(
        user_tg_id=user_tg_id,
        thread_id=thread_id,
        trace_id=trace_id,
        user_message="[start]",
        assistant_response=welcome_text,
    )
