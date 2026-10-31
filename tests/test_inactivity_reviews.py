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

from apps.bot.app.services import inactivity_reviews as reviews
from packages.shared.models.database import InactivityReview, DialogueHistory, UserProfile

UTC = timezone.utc
NOW = datetime.now(UTC)


@pytest_asyncio.fixture
async def database(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync: InactivityReview.metadata.create_all(sync, tables=[
            InactivityReview.__table__, DialogueHistory.__table__, UserProfile.__table__,
        ]))
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(reviews, "async_session_factory", sessions)
    monkeypatch.setattr(reviews.settings, "admin_telegram_chat_id", "-123")
    yield sessions
    await engine.dispose()


def turn(user_id, text, when, thread=None, saved_at=None):
    return DialogueHistory(
        id=uuid.uuid4(), user_tg_id=user_id, thread_id=thread or str(user_id),
        trace_id=str(uuid.uuid4()), user_message=text, assistant_response=f"Ответ: {text}",
        user_message_at=when, created_at=saved_at or when,
    )


async def rows(database):
    async with database() as session:
        return list((await session.scalars(
            select(InactivityReview).order_by(InactivityReview.completed_at, InactivityReview.user_tg_id)
        )).all())


@pytest.fixture
def delivery(monkeypatch):
    sender = AsyncMock()
    module = ModuleType("apps.bot.app.bot_instance")
    module.bot = SimpleNamespace(send_document=sender)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    monkeypatch.setattr(reviews, "generate_review", AsyncMock(return_value="Обсуждали продукт. Нужны цифры. Вопрос открыт."))
    return sender


@pytest.mark.asyncio
@pytest.mark.parametrize("seconds,expected", [(3599, 0), (3600, 0), (3601, 1)])
async def test_strict_inactivity_threshold(database, seconds, expected):
    async with database() as session:
        session.add(turn(1, "last", NOW - timedelta(seconds=seconds)))
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == expected


@pytest.mark.asyncio
async def test_full_history_uses_user_time_and_preserves_all_sessions(database):
    first = NOW - timedelta(days=30)
    last = NOW - timedelta(minutes=61)
    async with database() as session:
        session.add(UserProfile(tg_id=1, first_name="Анна", username="anna", updated_at=last))
        session.add_all([
            turn(1, "old history", first),
            turn(1, "latest reply", last, "1_1", saved_at=NOW),
            turn(1, "earlier receipt", last - timedelta(minutes=1), "1_1", saved_at=NOW + timedelta(seconds=1)),
            turn(2, "active user", NOW - timedelta(minutes=1)),
        ])
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == 1
    assert await reviews.enqueue_inactive_reviews(NOW + timedelta(minutes=10)) == 0
    report = (await rows(database))[0]
    assert reviews.as_utc(report.first_seen_at) == first
    assert reviews.as_utc(report.last_user_message_at) == last
    assert report.transcript_markdown.index("old history") < report.transcript_markdown.index("earlier receipt")
    assert report.transcript_markdown.index("earlier receipt") < report.transcript_markdown.index("latest reply")
    assert "Сессия 2" in report.transcript_markdown
    assert "active user" not in report.transcript_markdown
    report.review_text = "Краткое ревью. Нужны цифры. Вопрос открыт."
    text = reviews.format_review_document(report)
    assert "https://t.me/anna" in text and "**Telegram ID:** 1" in text
    assert "Последнее сообщение пользователя:" in text
    assert "Завершение по неактивности обнаружено:" in text
    assert last.astimezone(reviews.MOSCOW).strftime("%d.%m.%Y %H:%M:%S МСК") in text


@pytest.mark.asyncio
async def test_legacy_timestamp_and_missing_username(database):
    record = turn(1, "legacy", NOW - timedelta(hours=2))
    record.user_message_at = None
    async with database() as session:
        session.add(record)
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == 1
    report = (await rows(database))[0]
    text = reviews.format_review_document(report)
    assert "нет публичного username" in text and "Имя неизвестно" in text
    assert reviews.as_utc(report.last_user_message_at) == NOW - timedelta(hours=2)


@pytest.mark.asyncio
async def test_recent_arrival_defers_closure_before_response_is_saved(database):
    async with database() as session:
        session.add(turn(1, "old", NOW - timedelta(hours=2)))
        session.add(UserProfile(tg_id=1, updated_at=NOW))
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == 0


@pytest.mark.asyncio
async def test_delivery_restart_and_resumed_chat(database, delivery):
    async with database() as session:
        session.add(turn(1, "first visit", NOW - timedelta(hours=2)))
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == 1
    assert await reviews.process_next_review(NOW)
    assert not await reviews.process_next_review(NOW + timedelta(minutes=10))
    assert await reviews.enqueue_inactive_reviews(NOW + timedelta(minutes=10)) == 0
    delivery.assert_awaited_once()
    doc = delivery.await_args.kwargs["document"]
    assert doc.filename.startswith("conversation_review_1_")
    assert "first visit" in doc.data.decode("utf-8")
    assert (await rows(database))[0].sent_at is not None

    # The user returned. A new inactivity episode gets a new full-history file.
    async with database() as session:
        session.add(turn(1, "returned", NOW - timedelta(minutes=30), "1_1"))
        await session.commit()
    assert await reviews.enqueue_inactive_reviews(NOW) == 0
    assert await reviews.enqueue_inactive_reviews(NOW + timedelta(minutes=31)) == 1
    reports = await rows(database)
    assert len(reports) == 2
    assert "first visit" in reports[-1].transcript_markdown and "returned" in reports[-1].transcript_markdown


@pytest.mark.asyncio
async def test_failed_delivery_retries_and_summary_is_reused(database, delivery, monkeypatch):
    async with database() as session:
        session.add_all([turn(i, f"User {i}", NOW - timedelta(hours=2)) for i in [1, 2]])
        await session.commit()
    await reviews.enqueue_inactive_reviews(NOW)
    delivery.side_effect = [OSError("offline"), None, None]
    assert await reviews.process_next_review(NOW)
    assert await reviews.process_next_review(NOW)
    assert not await reviews.process_next_review(NOW)
    reports = await rows(database)
    assert reports[0].sent_at is None and reports[0].last_error == "offline"
    assert reports[1].sent_at is not None
    assert await reviews.process_next_review(NOW + timedelta(minutes=11))
    assert reviews.generate_review.await_count == 2
    assert all(report.sent_at is not None for report in await rows(database))


@pytest.mark.asyncio
async def test_pending_report_is_superseded_when_user_returns(database, delivery):
    async with database() as session:
        session.add(turn(1, "old", NOW - timedelta(hours=2)))
        await session.commit()
    await reviews.enqueue_inactive_reviews(NOW)
    async with database() as session:
        session.add(turn(1, "new", NOW))
        await session.commit()
    # Delivery itself checks for new messages even before the next full scan.
    assert await reviews.process_next_review(NOW)
    assert (await rows(database))[0].superseded_at is not None
    delivery.assert_not_awaited()
    assert await reviews.enqueue_inactive_reviews(NOW) == 0
    assert await reviews.enqueue_inactive_reviews(NOW + timedelta(minutes=61)) == 1


@pytest.mark.asyncio
async def test_user_returns_during_summary_generation(database, delivery, monkeypatch):
    async with database() as session:
        session.add(turn(1, "old", NOW - timedelta(hours=2)))
        await session.commit()
    await reviews.enqueue_inactive_reviews(NOW)
    monkeypatch.setattr(reviews, "current_review_state", AsyncMock(side_effect=["ready", "superseded"]))
    assert await reviews.process_next_review(NOW)
    delivery.assert_not_awaited()
    assert (await rows(database))[0].superseded_at is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [
    '["Обсуждали продукт.", "Нужны цифры.", "Разговор открыт."]',
    '["Обсуждали продукт.", "Нужны цифры.", "Вопрос открыт.", "Связаться позже."]',
    "not JSON", '["Only one."]', '[1, 2, 3]', None,
])
async def test_summary_validates_three_or_four_sentences(monkeypatch, content):
    monkeypatch.setattr(reviews, "get_llm_provider", AsyncMock(return_value="openai"))
    monkeypatch.setattr(reviews, "get_llm_model", AsyncMock(return_value="test"))
    ainvoke = AsyncMock(return_value=SimpleNamespace(content=content))
    if content is None:
        ainvoke.side_effect = TimeoutError("timeout")
    monkeypatch.setattr(reviews, "create_llm", lambda **kw: SimpleNamespace(ainvoke=ainvoke))
    result = await reviews.generate_review("История")
    if content and content.startswith('["Обсуждали'):
        assert result == " ".join(json.loads(content))
    else:
        assert result == reviews.FALLBACK_REVIEW


@pytest.mark.asyncio
async def test_missing_chat_keeps_report_pending(database, monkeypatch):
    async with database() as session:
        session.add(turn(1, "old", NOW - timedelta(hours=2)))
        await session.commit()
    await reviews.enqueue_inactive_reviews(NOW)
    monkeypatch.setattr(reviews.settings, "admin_telegram_chat_id", "")
    assert not await reviews.process_next_review(NOW)
    assert (await rows(database))[0].sent_at is None


@pytest.mark.asyncio
async def test_empty_history_sends_nothing(database, delivery):
    assert await reviews.enqueue_inactive_reviews(NOW) == 0
    assert not await reviews.process_next_review(NOW)
    delivery.assert_not_awaited()


@pytest.mark.asyncio
async def test_arrival_before_response_defers_pending_report(database, delivery):
    async with database() as session:
        session.add(turn(1, "old", NOW - timedelta(hours=2)))
        await session.commit()
    await reviews.enqueue_inactive_reviews(NOW)
    async with database() as session:
        session.add(UserProfile(tg_id=1, updated_at=NOW))
        await session.commit()
    assert await reviews.process_next_review(NOW)
    assert not await reviews.process_next_review(NOW)
    report = (await rows(database))[0]
    assert report.sent_at is None and report.superseded_at is None
    delivery.assert_not_awaited()


@pytest.mark.asyncio
async def test_unchanged_profile_refreshes_activity_on_arrival(database, monkeypatch):
    from apps.bot.app.services import language_service

    old = NOW - timedelta(hours=2)
    async with database() as session:
        session.add(UserProfile(tg_id=1, first_name="Анна", updated_at=old))
        session.add(turn(1, "old", old))
        await session.commit()
    monkeypatch.setattr(language_service, "async_session_factory", database)
    user = SimpleNamespace(id=1, first_name="Анна", last_name=None, username=None, language_code=None)
    profile = await language_service.upsert_user_profile(user)
    assert reviews.as_utc(profile.updated_at) > old
    assert await reviews.enqueue_inactive_reviews(datetime.now(UTC)) == 0
