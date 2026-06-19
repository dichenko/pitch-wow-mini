import pytest
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from apps.bot.app.services.telegram_messages import (
    SAFE_TEXT_CHUNK_SIZE,
    answer_markdown_or_text,
    send_message_markdown_or_text,
)


class _FakeMessage:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.calls = []

    async def answer(self, text, **kwargs):
        self.calls.append({"text": text, "kwargs": kwargs})
        if self.fail_first and len(self.calls) == 1:
            raise TelegramBadRequest(
                method=None,
                message="Bad Request: can't parse entities",
            )
        return {"ok": True}


class _FakeBot:
    def __init__(self, fail_first: bool = False) -> None:
        self.fail_first = fail_first
        self.calls = []

    async def send_message(self, chat_id, text, **kwargs):
        self.calls.append({"chat_id": chat_id, "text": text, "kwargs": kwargs})
        if self.fail_first and len(self.calls) == 1:
            raise TelegramBadRequest(
                method=None,
                message="Bad Request: can't parse entities",
            )
        return {"ok": True}


@pytest.mark.asyncio
async def test_answer_markdown_or_text_uses_markdown_by_default():
    message = _FakeMessage()

    await answer_markdown_or_text(message, "*hello*")

    assert message.calls == [
        {"text": "*hello*", "kwargs": {"parse_mode": ParseMode.MARKDOWN}}
    ]


@pytest.mark.asyncio
async def test_answer_markdown_or_text_retries_plain_text_on_markup_error():
    message = _FakeMessage(fail_first=True)

    await answer_markdown_or_text(message, "*broken")

    assert message.calls == [
        {"text": "*broken", "kwargs": {"parse_mode": ParseMode.MARKDOWN}},
        {"text": "*broken", "kwargs": {"parse_mode": None}},
    ]


@pytest.mark.asyncio
async def test_send_message_markdown_or_text_retries_plain_text_on_markup_error():
    bot = _FakeBot(fail_first=True)

    await send_message_markdown_or_text(bot, 123, "*broken")

    assert bot.calls == [
        {
            "chat_id": 123,
            "text": "*broken",
            "kwargs": {"parse_mode": ParseMode.MARKDOWN},
        },
        {
            "chat_id": 123,
            "text": "*broken",
            "kwargs": {"parse_mode": None},
        },
    ]


@pytest.mark.asyncio
async def test_answer_markdown_or_text_splits_long_text_as_plain_text():
    message = _FakeMessage()
    text = ("paragraph\n\n" * 500).strip()

    await answer_markdown_or_text(message, text)

    assert len(message.calls) > 1
    assert all(len(call["text"]) <= SAFE_TEXT_CHUNK_SIZE for call in message.calls)
    assert all(call["kwargs"]["parse_mode"] is None for call in message.calls)


@pytest.mark.asyncio
async def test_send_message_markdown_or_text_splits_long_text_as_plain_text():
    bot = _FakeBot()
    text = ("paragraph\n\n" * 500).strip()

    await send_message_markdown_or_text(bot, 123, text)

    assert len(bot.calls) > 1
    assert all(len(call["text"]) <= SAFE_TEXT_CHUNK_SIZE for call in bot.calls)
    assert all(call["kwargs"]["parse_mode"] is None for call in bot.calls)
