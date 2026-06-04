"""/restart command handler — clears conversation history."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from apps.bot.app.agent.agent import reset_user_thread

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    if not message.from_user:
        return

    reset_user_thread(message.from_user.id)
    logger.info(f"User {message.from_user.id} restarted conversation via /restart")
    await message.answer(
        "История диалога очищена. Начинаем с чистого листа. Чем могу помочь?"
    )
