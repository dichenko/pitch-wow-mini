"""Shared bot flow for sending localized welcome messages."""

from aiogram.types import Message, User

from apps.bot.app.agent.agent import get_current_thread_id
from apps.bot.app.services.welcome_service import get_active_welcome_message
from apps.bot.app.services.telegram_messages import answer_markdown_or_text
from packages.shared.utils.languages import Language


async def send_welcome(
    message: Message,
    user: User,
    language: Language,
) -> None:
    await get_current_thread_id(user.id)
    welcome_text = await get_active_welcome_message(language)
    await answer_markdown_or_text(message, welcome_text)
