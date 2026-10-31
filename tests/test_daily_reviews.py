import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.bot.app.services import daily_reviews as reviews
from packages.shared.models.database import AppSetting, DailyUserReview, DialogueHistory, UserProfile

UTC = timezone.utc
CUTOFF = datetime(2026, 10, 31, 20, 55, tzinfo=UTC)


@pytest_asyncio.fixture
async def database(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: AppSetting.metadata.create_all(sync, tables=[
            AppSetting.__table__, DailyUserReview.__table__,
            DialogueHistory.__table__, UserProfile.__table__,
        ]))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(reviews, "async_session_factory", sessions)
    monkeypatch.setattr(reviews.settings, "admin_telegram_chat_id", "-123")
    yield sessions
    await engine.dispose()


def turn(user_id, text, when, thread=None):
    return DialogueHistory(
        id=uuid.uuid4(), user_tg_id=user_id, thread_id=thread or str(user_id),
        trace_id=str(uuid.uuid4()), user_message=text, assistant_response=f"Ответ: {text}",
        created_at=when,
    )


async def queued_rows(database):
    async with database() as session:
        return list((await session.scalars(
            select(DailyUserReview).order_by(DailyUserReview.window_end, DailyUserReview.user_tg_id)
        )).all())


@pytest.mark.parametrize("offset,expected_days", [(-1, -1), (0, 0), (1, 0)])
def test_cutoff_uses_2355_moscow_and_exact_boundary(offset, expected_days):
    assert reviews.latest_review_cutoff(CUTOFF + timedelta(seconds=offset)) == (
        CUTOFF + timedelta(days=expected_days)
    )


@pytest.mark.asyncio
async def test_window_filters_users_and_combines_sessions_without_duplicates(database):
    async with database() as session:
        session.add(UserProfile(tg_id=1, first_name="Анна", username="anna"))
        session.add_all([
            turn(1, "outside", CUTOFF - timedelta(days=1, seconds=1)),
            turn(1, "at start", CUTOFF - timedelta(days=1)),
            turn(1, "next session", CUTOFF - timedelta(minutes=1), "1_1"),
            turn(1, "at end", CUTOFF),
            turn(2, "other user", CUTOFF - timedelta(hours=1)),
        ])
        await session.commit()

    assert await reviews.enqueue_due_reviews(CUTOFF) == 2
    assert await reviews.enqueue_due_reviews(CUTOFF + timedelta(seconds=30)) == 0
    rows = await queued_rows(database)
    assert len(rows) == 2
    first = rows[0]
    assert first.first_name == "Анна" and first.username == "anna"
    assert "at start" in first.transcript_markdown
    assert "next session" in first.transcript_markdown
    assert "Сессия 2" in first.transcript_markdown
    assert "outside" not in first.transcript_markdown
    assert "at end" not in first.transcript_markdown
    assert "other user" not in first.transcript_markdown
    assert "31.10.2026 23:54:00 МСК" in first.transcript_markdown
    assert rows[1].first_name is None

    # Restart/catch-up: the saved cursor excludes earlier users, includes the exact cutoff.
    assert await reviews.enqueue_due_reviews(CUTOFF + timedelta(days=2)) == 1
    rows = await queued_rows(database)
    assert len(rows) == 3 and "at end" in rows[2].transcript_markdown


@pytest.mark.asyncio
async def test_empty_window_advances_cursor_without_reports(database):
    assert await reviews.enqueue_due_reviews(CUTOFF) == 0
    assert await queued_rows(database) == []
    async with database() as session:
        cursor = await session.get(AppSetting, reviews.CURSOR_KEY)
        assert datetime.fromisoformat(cursor.value) == CUTOFF


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [
    '["Обсуждали продукт.", "Договорились продолжить.", "Разговор открыт."]',
    "not JSON", '["Only one sentence."]', '[1, 2, 3]', None,
])
async def test_summary_validates_three_sentences_and_falls_back(monkeypatch, content):
    monkeypatch.setattr(reviews, "get_llm_provider", AsyncMock(return_value="openai"))
    monkeypatch.setattr(reviews, "get_llm_model", AsyncMock(return_value="test"))
    ainvoke = AsyncMock(return_value=SimpleNamespace(content=content))
    if content is None:
        ainvoke.side_effect = TimeoutError("model timeout")
    monkeypatch.setattr(reviews, "create_llm", lambda **kw: SimpleNamespace(ainvoke=ainvoke))
    result = await reviews.generate_daily_review("Диалог пользователя")
    if content and content.startswith('["Обсуждали'):
        assert result == " ".join(json.loads(content))
    else:
        assert result == reviews.FALLBACK_REVIEW


@pytest.mark.asyncio
async def test_file_delivery_retries_only_failed_user_and_reuses_summary(database, monkeypatch):
    now = datetime.now(UTC)
    async with database() as session:
        for user_id in [1, 2]:
            session.add(DailyUserReview(
                user_tg_id=user_id, window_start=CUTOFF - timedelta(days=1),
                window_end=CUTOFF, first_name="Анна" if user_id == 1 else None,
                username="anna" if user_id == 1 else None,
                transcript_markdown=f"Full dialogue {user_id}", next_attempt_at=now,
            ))
        await session.commit()

    summary = AsyncMock(return_value="Обсуждали продукт. Нужны цифры. Разговор открыт.")
    monkeypatch.setattr(reviews, "generate_daily_review", summary)
    sent = []
    fail_first = True

    async def send_document(**kwargs):
        nonlocal fail_first
        document = kwargs["document"]
        if document.filename.startswith("daily_review_1_") and fail_first:
            fail_first = False
            raise OSError("Telegram unavailable")
        sent.append(kwargs)

    module = ModuleType("apps.bot.app.bot_instance")
    module.bot = SimpleNamespace(send_document=send_document)
    monkeypatch.setitem(sys.modules, module.__name__, module)

    assert await reviews.process_next_review(now)
    assert await reviews.process_next_review(now)
    assert not await reviews.process_next_review(now)
    rows = await queued_rows(database)
    assert rows[0].sent_at is None and rows[0].last_error == "Telegram unavailable"
    assert rows[1].sent_at is not None
    assert len(sent) == 1

    # A later poll (including after a process restart) sends only the failed user's file.
    assert await reviews.process_next_review(now + timedelta(minutes=10))
    assert not await reviews.process_next_review(now + timedelta(minutes=10))
    assert summary.await_count == 2
    assert len(sent) == 2
    document = sent[-1]["document"]
    text = document.data.decode("utf-8")
    assert "Анна" in text and "@anna" in text and "**Telegram ID:** 1" in text
    assert "Разговор открыт." in text and "Full dialogue 1" in text
    assert "Full dialogue 2" not in text
    assert sent[-1]["chat_id"] == -123 and sent[-1]["parse_mode"] is None


@pytest.mark.asyncio
async def test_missing_admin_chat_retains_queue(database, monkeypatch):
    monkeypatch.setattr(reviews.settings, "admin_telegram_chat_id", "")
    assert not await reviews.process_next_review(datetime.now(UTC))
