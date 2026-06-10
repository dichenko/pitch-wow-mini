"""/start command handler."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from apps.bot.app.services.language_service import (
    answer_language_selection,
    get_preferred_language,
)
from apps.bot.app.services.welcome_flow import reset_thread_and_send_welcome

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return

    user = message.from_user
    language = await get_preferred_language(user)
    if language is None:
        await answer_language_selection(message)
        logger.info("User %s started without language, selection requested", user.id)
        return

    await reset_thread_and_send_welcome(message, user, language)
    logger.info("User %s started, localized welcome sent language=%s", user.id, language)
