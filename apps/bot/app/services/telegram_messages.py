"""Telegram text sending helpers."""

import logging
from typing import Any

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


def _is_markup_error(exc: TelegramBadRequest) -> bool:
    message = str(exc).lower()
    return any(
        marker in message
        for marker in (
            "can't parse entities",
            "can't find end",
            "unsupported start tag",
            "entity",
            "parse",
        )
    )


async def answer_markdown_or_text(message: Any, text: str, **kwargs: Any) -> Any:
    """Answer with Markdown first, then retry as plain text on markup errors."""
    try:
        return await message.answer(text, parse_mode=ParseMode.MARKDOWN, **kwargs)
    except TelegramBadRequest as exc:
        if not _is_markup_error(exc):
            raise
        logger.warning("Markdown answer failed, retrying as plain text: %s", exc)
        return await message.answer(text, parse_mode=None, **kwargs)


async def send_message_markdown_or_text(
    bot: Any,
    chat_id: int,
    text: str,
    **kwargs: Any,
) -> Any:
    """Send a message with Markdown first, then retry as plain text on markup errors."""
    try:
        return await bot.send_message(
            chat_id,
            text,
            parse_mode=ParseMode.MARKDOWN,
            **kwargs,
        )
    except TelegramBadRequest as exc:
        if not _is_markup_error(exc):
            raise
        logger.warning("Markdown send_message failed, retrying as plain text: %s", exc)
        return await bot.send_message(chat_id, text, parse_mode=None, **kwargs)
