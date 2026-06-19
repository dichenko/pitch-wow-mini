"""Shared bot flow for sending localized welcome messages."""

import uuid

from aiogram.types import Message, User

from apps.bot.app.agent.agent import get_current_thread_id, reset_user_thread_state
from apps.bot.app.services.welcome_service import (
    get_active_welcome_message,
    persist_welcome_to_history,
)
from apps.bot.app.services.telegram_messages import answer_markdown_or_text
from packages.shared.utils.languages import Language


async def reset_thread_and_send_welcome(
    message: Message,
    user: User,
    language: Language,
) -> None:
    await reset_user_thread_state(user.id)
    await send_welcome(message, user, language)


async def send_welcome(
    message: Message,
    user: User,
    language: Language,
) -> None:
    trace_id = str(uuid.uuid4())
    thread_id = await get_current_thread_id(user.id)
    welcome_text = await get_active_welcome_message(language)
    await answer_markdown_or_text(message, welcome_text)

    await persist_welcome_to_history(
        user_tg_id=user.id,
        thread_id=thread_id,
        trace_id=trace_id,
        welcome_text=welcome_text,
    )
