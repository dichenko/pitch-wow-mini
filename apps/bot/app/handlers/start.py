"""/start command handler."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from apps.bot.app.agent.agent import reset_user_thread_state
from apps.bot.app.services.language_service import (
    answer_language_selection,
    clear_preferred_language,
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not message.from_user:
        return

    user = message.from_user
    await reset_user_thread_state(user.id)
    await clear_preferred_language(user)
    await answer_language_selection(message)
    logger.info("User %s started, memory reset and language selection requested", user.id)
