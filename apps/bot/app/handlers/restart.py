"""/restart command handler — clears conversation history."""

import uuid
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from apps.bot.app.agent.agent import get_thread_id, reset_user_thread
from apps.bot.app.services.welcome_service import (
    DEFAULT_WELCOME,
    get_active_welcome_message,
    persist_welcome_to_history,
)

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("restart"))
async def cmd_restart(message: Message) -> None:
    if not message.from_user:
        return

    user = message.from_user
    trace_id = str(uuid.uuid4())

    reset_user_thread(user.id)
    thread_id = get_thread_id(user.id)

    logger.info(f"User {user.id} restarted conversation via /restart")

    welcome_text = await get_active_welcome_message()
    if not welcome_text:
        welcome_text = DEFAULT_WELCOME

    await message.answer(welcome_text)

    await persist_welcome_to_history(
        user_tg_id=user.id,
        thread_id=thread_id,
        trace_id=trace_id,
        welcome_text=welcome_text,
    )
