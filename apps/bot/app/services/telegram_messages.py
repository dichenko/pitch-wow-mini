"""Telegram text sending helpers."""

import logging
from typing import Any

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

TELEGRAM_TEXT_LIMIT = 4096
SAFE_TEXT_CHUNK_SIZE = 3800


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


def _split_long_text(text: str, limit: int = SAFE_TEXT_CHUNK_SIZE) -> list[str]:
    """Split text into Telegram-safe chunks, preferring paragraph boundaries."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit

        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()

    if remaining:
        chunks.append(remaining)
    return chunks


async def answer_markdown_or_text(message: Any, text: str, **kwargs: Any) -> Any:
    """Answer with Markdown first, then retry as plain text on markup errors."""
    if len(text) > SAFE_TEXT_CHUNK_SIZE:
        results = []
        for chunk in _split_long_text(text):
            results.append(await message.answer(chunk, parse_mode=None, **kwargs))
        return results[-1] if results else None

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
    if len(text) > SAFE_TEXT_CHUNK_SIZE:
        results = []
        for chunk in _split_long_text(text):
            results.append(
                await bot.send_message(chat_id, chunk, parse_mode=None, **kwargs)
            )
        return results[-1] if results else None

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
