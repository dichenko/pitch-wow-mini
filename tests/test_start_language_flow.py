from types import SimpleNamespace

import pytest

from apps.bot.app.handlers import start as start_module


class FakeMessage:
    def __init__(self):
        self.from_user = SimpleNamespace(
            id=100,
            first_name="Test",
            last_name=None,
            username="tester",
            language_code="ru",
        )
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append({"text": text, "kwargs": kwargs})


@pytest.mark.asyncio
async def test_start_always_resets_memory_and_requests_language(monkeypatch):
    calls = []

    async def reset_user_thread_state(user_id):
        calls.append(("reset", user_id))

    async def clear_preferred_language(user):
        calls.append(("clear_language", user.id))

    async def answer_language_selection(message):
        calls.append(("language_menu", message.from_user.id))
        await message.answer("language menu")

    monkeypatch.setattr(start_module, "reset_user_thread_state", reset_user_thread_state)
    monkeypatch.setattr(start_module, "clear_preferred_language", clear_preferred_language)
    monkeypatch.setattr(start_module, "answer_language_selection", answer_language_selection)

    message = FakeMessage()
    await start_module.cmd_start(message)

    assert calls == [
        ("reset", 100),
        ("clear_language", 100),
        ("language_menu", 100),
    ]
    assert message.answers == [{"text": "language menu", "kwargs": {}}]
