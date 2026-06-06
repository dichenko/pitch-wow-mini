"""Dialogue history service for database-backed LLM context."""

import logging
from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import select

from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import DialogueHistory

logger = logging.getLogger(__name__)


async def load_dialogue_history(
    user_tg_id: int,
    thread_id: str,
    limit: int,
) -> list[DialogueHistory]:
    """Load latest dialogue records for a user/thread in chronological order."""
    if limit <= 0:
        return []

    async with async_session_factory() as session:
        result = await session.execute(
            select(DialogueHistory)
            .where(
                DialogueHistory.user_tg_id == user_tg_id,
                DialogueHistory.thread_id == thread_id,
            )
            .order_by(DialogueHistory.created_at.desc())
            .limit(limit)
        )
        records = list(result.scalars().all())

    records.reverse()
    return records


def dialogue_history_to_messages(
    records: Sequence[DialogueHistory],
) -> list[BaseMessage]:
    """Convert dialogue rows into provider-neutral LangChain chat messages."""
    messages: list[BaseMessage] = []
    for record in records:
        messages.append(HumanMessage(content=record.user_message))
        messages.append(AIMessage(content=record.assistant_response))
    return messages


async def save_dialogue_turn(
    user_tg_id: int,
    thread_id: str,
    trace_id: str,
    user_message: str,
    assistant_response: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> None:
    """Persist one completed dialogue turn."""
    async with async_session_factory() as session:
        session.add(
            DialogueHistory(
                user_tg_id=user_tg_id,
                thread_id=thread_id,
                trace_id=trace_id,
                user_message=user_message,
                assistant_response=assistant_response,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
        )
        await session.commit()


async def save_dialogue_turn_best_effort(**kwargs) -> None:
    """Persist a dialogue turn without breaking user-facing message handling."""
    try:
        await save_dialogue_turn(**kwargs)
    except Exception as exc:
        logger.error(
            "Failed to save dialogue history trace_id=%s: %s",
            kwargs.get("trace_id", "unknown"),
            exc,
            exc_info=True,
        )


async def load_all_user_history(
    user_tg_id: int,
) -> list[DialogueHistory]:
    """Load all dialogue records for a user across all threads, chronologically."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(DialogueHistory)
            .where(DialogueHistory.user_tg_id == user_tg_id)
            .order_by(DialogueHistory.created_at.asc())
        )
        return list(result.scalars().all())
