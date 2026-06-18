from datetime import datetime, timezone
import importlib
import sys
from types import ModuleType
from types import SimpleNamespace

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


@pytest.mark.asyncio
async def test_send_to_admin_sends_pdf_dossier_after_history(monkeypatch, tmp_path):
    module = importlib.import_module("apps.bot.app.agent.tools.send_to_admin")
    _current_context.clear()

    pdf_path = tmp_path / "dossier.pdf"
    pdf_path.write_bytes(b"%PDF")
    sent_documents = []
    db_notifications = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            return None

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
        return [
            _history_record(
                user_message="question",
                assistant_response="answer",
                created_at=datetime(2026, 6, 6, 8, 10, 11, tzinfo=timezone.utc),
                thread_id=thread_id,
            )
        ]

    class FakePdfDossierService:
        def __init__(self, settings):
            self.settings = settings

        async def generate(self, **kwargs):
            return SimpleNamespace(
                success=True,
                status="done",
                pdf_path=str(pdf_path),
                pdf_url="https://example.com/dossier.pdf",
                metadata={
                    "status": "done",
                    "pdf_url": "https://example.com/dossier.pdf",
                    "payload": {"schema_version": "1.0"},
                },
                error=None,
            )

    fake_bot_instance = ModuleType("apps.bot.app.bot_instance")
    fake_bot_instance.bot = FakeBot()

    monkeypatch.setitem(sys.modules, "apps.bot.app.bot_instance", fake_bot_instance)
    monkeypatch.setattr(module.settings, "admin_telegram_chat_id", "123", raising=False)
    monkeypatch.setattr(module, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(module, "load_user_thread_history", load_user_thread_history)
    monkeypatch.setattr(module, "_format_history_markdown", lambda **kwargs: "history markdown")
    monkeypatch.setattr(module, "PdfDossierService", FakePdfDossierService)

    set_tool_context(
        user_data={"tg_id": 183866240, "username": "ivan"},
        trace_id="trace-pdf",
        current_user_message="current question",
        current_thread_id="183866240",
    )

    await module.send_to_admin.ainvoke({"comment": "send to admin"})

    assert len(sent_documents) == 2
    assert sent_documents[0]["path"].endswith(".md")
    assert sent_documents[1]["path"] == str(pdf_path)
    assert not pdf_path.exists()
    assert db_notifications[0].payload["pdf_dossier"]["status"] == "done"
    assert db_notifications[0].payload["pdf_dossier"]["pdf_url"] == "https://example.com/dossier.pdf"


@pytest.mark.asyncio
async def test_send_to_admin_reports_pdf_failure_to_admin_chat(monkeypatch):
    module = importlib.import_module("apps.bot.app.agent.tools.send_to_admin")
    _current_context.clear()

    sent_messages = []
    db_notifications = []

    class FakeBot:
        async def send_message(self, chat_id, text):
            sent_messages.append({"chat_id": chat_id, "text": text})

        async def send_document(self, chat_id, document, caption):
            return None

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
        return []

    class FakePdfDossierService:
        def __init__(self, settings):
            self.settings = settings

        async def generate(self, **kwargs):
            return SimpleNamespace(
                success=False,
                status="failed",
                pdf_path=None,
                pdf_url=None,
                metadata={"status": "failed", "error": "validation failed"},
                error="validation failed",
            )

    fake_bot_instance = ModuleType("apps.bot.app.bot_instance")
    fake_bot_instance.bot = FakeBot()

    monkeypatch.setitem(sys.modules, "apps.bot.app.bot_instance", fake_bot_instance)
    monkeypatch.setattr(module.settings, "admin_telegram_chat_id", "123", raising=False)
    monkeypatch.setattr(module, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(module, "load_user_thread_history", load_user_thread_history)
    monkeypatch.setattr(module, "_format_history_markdown", lambda **kwargs: "history markdown")
    monkeypatch.setattr(module, "PdfDossierService", FakePdfDossierService)

    set_tool_context(
        user_data={"tg_id": 183866240, "username": "ivan"},
        trace_id="trace-pdf-failed",
        current_user_message="current question",
        current_thread_id="183866240",
    )

    await module.send_to_admin.ainvoke({"comment": "send to admin"})

    assert any("PDF не создан" in message["text"] for message in sent_messages)
    assert db_notifications[0].payload["pdf_dossier"]["status"] == "failed"
    assert db_notifications[0].delivered is True


@pytest.mark.asyncio
async def test_send_to_admin_without_admin_chat_persists_without_pdf_delivery(monkeypatch):
    module = importlib.import_module("apps.bot.app.agent.tools.send_to_admin")
    _current_context.clear()

    db_notifications = []
    created_pdf_services = []

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def add(self, notification):
            db_notifications.append(notification)

        async def commit(self):
            return None

    class FakePdfDossierService:
        def __init__(self, settings):
            created_pdf_services.append(settings)

    monkeypatch.setattr(module.settings, "admin_telegram_chat_id", "", raising=False)
    monkeypatch.setattr(module, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(module, "PdfDossierService", FakePdfDossierService)

    set_tool_context(
        user_data={"tg_id": 183866240, "username": "ivan"},
        trace_id="trace-no-chat",
        current_user_message="current question",
        current_thread_id="183866240",
    )

    await module.send_to_admin.ainvoke({"comment": "send to admin"})

    assert len(db_notifications) == 1
    assert db_notifications[0].delivered is False
    assert created_pdf_services == []
