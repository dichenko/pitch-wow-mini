"""Language selection callback handlers."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from apps.bot.app.services.language_service import (
    LANGUAGE_LABELS,
    normalize_preferred_language,
    set_preferred_language,
)
from apps.bot.app.services.welcome_flow import reset_thread_and_send_welcome

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("language:"))
async def language_selected(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data:
        await callback.answer()
        return

    language = normalize_preferred_language(callback.data.split(":", 1)[1])
    if language is None:
        await callback.answer("Unsupported language", show_alert=True)
        return

    saved_language = await set_preferred_language(callback.from_user, language)
    await callback.answer(LANGUAGE_LABELS[saved_language])

    if not isinstance(callback.message, Message):
        return

    await reset_thread_and_send_welcome(
        callback.message,
        callback.from_user,
        saved_language,
    )
    logger.info(
        "User %s selected language=%s",
        callback.from_user.id,
        saved_language,
    )
