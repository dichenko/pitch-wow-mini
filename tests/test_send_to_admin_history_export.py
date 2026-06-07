from datetime import datetime, timezone

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


def test_format_history_markdown_includes_all_db_records_with_roles_and_time():
    records = [
        _history_record(
            user_message="Первый вопрос",
            assistant_response="Первый ответ",
            created_at=datetime(2026, 6, 6, 7, 10, 11, tzinfo=timezone.utc),
            trace_id="trace-1",
        ),
        _history_record(
            user_message="Второй вопрос",
            assistant_response="Второй ответ",
            created_at=datetime(2026, 6, 6, 7, 20, 22, tzinfo=timezone.utc),
            trace_id="trace-2",
        ),
        _history_record(
            user_message="Третий вопрос",
            assistant_response="Третий ответ",
            created_at=datetime(2026, 6, 6, 7, 30, 33, tzinfo=timezone.utc),
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
        current_user_message="Текущий вопрос",
        current_comment="Передайте администратору",
    )

    assert "**Записей из БД:** 3" in md
    for expected in (
        "Первый вопрос",
        "Первый ответ",
        "Второй вопрос",
        "Второй ответ",
        "Третий вопрос",
        "Третий ответ",
        "Текущий вопрос",
        "Передайте администратору",
    ):
        assert expected in md

    assert "2026-06-06 · 07:10:11 UTC · Пользователь" in md
    assert "2026-06-06 · 07:10:11 UTC · Ассистент" in md
    assert "- **Thread:** `183866240_1`" in md
    assert "- **Trace:** `trace-3`" in md
    assert "## Текущий запрос" in md
    assert "## Передано администратору" in md


def test_set_tool_context_stores_current_user_message():
    _current_context.clear()

    set_tool_context(
        user_data={"tg_id": 183866240},
        trace_id="trace-current",
        current_user_message="Сообщение текущего хода",
    )

    assert _current_context["trace_id"] == "trace-current"
    assert _current_context["current_user_message"] == "Сообщение текущего хода"
