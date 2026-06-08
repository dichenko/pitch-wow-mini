from datetime import datetime, timezone
import importlib
import sys
from types import ModuleType

import pytest

from apps.bot.app.agent.tools.send_to_admin import (
    _current_context,
    _format_history_markdown,
    set_tool_context,
)
from packages.shared.models.database import DialogueHistory


def _history_record(
    user_message: str,
    assistant_response: str,
    created_at: datetime,
    thread_id: str = "183866240",
    trace_id: str = "trace-1",
) -> DialogueHistory:
    return DialogueHistory(
        user_tg_id=183866240,
        thread_id=thread_id,
        trace_id=trace_id,
        user_message=user_message,
        assistant_response=assistant_response,
        created_at=created_at,
    )


def test_format_history_markdown_groups_db_records_by_date():
    records = [
        _history_record(
            user_message="First question",
            assistant_response="First answer",
            created_at=datetime(2026, 6, 6, 7, 10, 11, tzinfo=timezone.utc),
            trace_id="trace-1",
        ),
        _history_record(
            user_message="Second question",
            assistant_response="Second answer",
            created_at=datetime(2026, 6, 6, 7, 20, 22, tzinfo=timezone.utc),
            trace_id="trace-2",
        ),
        _history_record(
            user_message="Third question",
            assistant_response="Third answer",
            created_at=datetime(2026, 6, 7, 12, 30, 33, tzinfo=timezone.utc),
            thread_id="183866240_1",
            trace_id="trace-3",
        ),
    ]

    md = _format_history_markdown(
        first_name="Ivan",
        last_name="Petrov",
        username="ivan",
        tg_id=183866240,
        records=records,
        current_user_message="Current question",
        current_comment="Please forward to admin",
    )

    assert "# История диалога" in md
    assert "2026-06-06" in md
    assert "2026-06-07" in md
    assert "**07:10 Фаундер**: First question" in md
    assert "**Ассистент**: First answer" in md
    assert "**07:20 Фаундер**: Second question" in md
    assert "**Ассистент**: Second answer" in md
    assert "**12:30 Фаундер**: Third question" in md
    assert "**Ассистент**: Third answer" in md
    assert "Current question" in md
    assert "Please forward to admin" not in md
    assert "Thread:" not in md
    assert "Trace:" not in md


def test_set_tool_context_stores_current_user_message_and_thread():
    _current_context.clear()

    set_tool_context(
        user_data={"tg_id": 183866240},
        trace_id="trace-current",
        current_user_message="Current user message",
        current_thread_id="183866240_2",
    )

    assert _current_context["trace_id"] == "trace-current"
    assert _current_context["current_user_message"] == "Current user message"
    assert _current_context["current_thread_id"] == "183866240_2"


@pytest.mark.asyncio
async def test_send_to_admin_exports_only_current_thread(monkeypatch):
    module = importlib.import_module("apps.bot.app.agent.tools.send_to_admin")
    _current_context.clear()

    current_records = [
        _history_record(
            user_message="current thread question",
            assistant_response="current thread answer",
            created_at=datetime(2026, 6, 6, 8, 10, 11, tzinfo=timezone.utc),
            thread_id="183866240_2",
            trace_id="trace-current-thread",
        )
    ]
    captured = {}
    db_notifications = []
    sent_documents = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            captured["message_chat_id"] = chat_id
            captured["message_text"] = text

        async def send_document(self, chat_id, document, caption):
            sent_documents.append(
                {"chat_id": chat_id, "path": document.path, "caption": caption}
            )

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def add(self, notification):
            db_notifications.append(notification)

        async def commit(self):
            return None

    async def load_user_thread_history(user_tg_id, thread_id):
        captured["history_args"] = (user_tg_id, thread_id)
        return current_records

    async def load_latest_user_thread_history(user_tg_id):
        raise AssertionError("latest thread fallback should not be used")

    def format_history_markdown(**kwargs):
        captured["formatted_records"] = kwargs["records"]
        return "history markdown"

    fake_bot_instance = ModuleType("apps.bot.app.bot_instance")
    fake_bot_instance.bot = FakeBot()

    monkeypatch.setitem(sys.modules, "apps.bot.app.bot_instance", fake_bot_instance)
    monkeypatch.setattr(module.settings, "admin_telegram_chat_id", "123", raising=False)
    monkeypatch.setattr(module, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(module, "load_user_thread_history", load_user_thread_history)
    monkeypatch.setattr(module, "load_latest_user_thread_history", load_latest_user_thread_history)
    monkeypatch.setattr(module, "_format_history_markdown", format_history_markdown)

    set_tool_context(
        user_data={
            "tg_id": 183866240,
            "first_name": "Ivan",
            "last_name": None,
            "username": "ivan",
            "language_code": "ru",
        },
        trace_id="trace-current",
        current_user_message="current question",
        current_thread_id="183866240_2",
    )

    await module.send_to_admin.ainvoke({"comment": "send to admin"})

    assert captured["history_args"] == (183866240, "183866240_2")
    assert captured["formatted_records"] == current_records
    assert all(record.thread_id == "183866240_2" for record in captured["formatted_records"])
    assert captured["message_chat_id"] == 123
    assert len(sent_documents) == 1
    assert len(db_notifications) == 1


@pytest.mark.asyncio
async def test_send_to_admin_falls_back_to_latest_thread_when_context_has_no_thread(monkeypatch):
    module = importlib.import_module("apps.bot.app.agent.tools.send_to_admin")
    _current_context.clear()

    latest_records = [
        _history_record(
            user_message="latest question",
            assistant_response="latest answer",
            created_at=datetime(2026, 6, 6, 9, 10, 11, tzinfo=timezone.utc),
            thread_id="183866240_3",
            trace_id="trace-latest-thread",
        )
    ]
    captured = {}

    class FakeBot:
        async def send_message(self, chat_id, text):
            return None

        async def send_document(self, chat_id, document, caption):
            captured["document_path"] = document.path

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def add(self, notification):
            return None

        async def commit(self):
            return None

    async def load_user_thread_history(user_tg_id, thread_id):
        raise AssertionError("current thread loader should not be used")

    async def load_latest_user_thread_history(user_tg_id):
        captured["latest_user_tg_id"] = user_tg_id
        return latest_records

    def format_history_markdown(**kwargs):
        captured["formatted_records"] = kwargs["records"]
        return "history markdown"

    fake_bot_instance = ModuleType("apps.bot.app.bot_instance")
    fake_bot_instance.bot = FakeBot()

    monkeypatch.setitem(sys.modules, "apps.bot.app.bot_instance", fake_bot_instance)
    monkeypatch.setattr(module.settings, "admin_telegram_chat_id", "123", raising=False)
    monkeypatch.setattr(module, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(module, "load_user_thread_history", load_user_thread_history)
    monkeypatch.setattr(module, "load_latest_user_thread_history", load_latest_user_thread_history)
    monkeypatch.setattr(module, "_format_history_markdown", format_history_markdown)

    set_tool_context(
        user_data={"tg_id": 183866240},
        trace_id="trace-latest",
        current_user_message="current question",
    )

    await module.send_to_admin.ainvoke({"comment": "send to admin"})

    assert captured["latest_user_tg_id"] == 183866240
    assert captured["formatted_records"] == latest_records
    assert all(record.thread_id == "183866240_3" for record in captured["formatted_records"])
