"""Welcome message service — retrieves active welcome and persists to history."""

import logging
import uuid

from sqlalchemy import select

from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.history_service import save_dialogue_turn_best_effort
from packages.shared.models.database import PromptVersion

logger = logging.getLogger(__name__)

DEFAULT_WELCOME = (
    "Привет! Я AI-ассистент. Чем могу помочь?\n\n"
    "Для администраторов: используйте /admin для входа в панель управления."
)


async def get_active_welcome_message() -> str | None:
    """Return the active welcome message content from DB."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PromptVersion.content).where(
                PromptVersion.kind == "welcome_message",
                PromptVersion.is_active == True,
            )
        )
        return result.scalar_one_or_none()


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
