"""Settings service — reads and writes application settings from DB."""

import logging
import uuid

from sqlalchemy import select

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from packages.shared.models.database import AppSetting

logger = logging.getLogger(__name__)
settings = get_settings()

DEFAULT_LLM_HISTORY_MESSAGES = 20
MAX_LLM_HISTORY_MESSAGES = 100


async def _get_setting(key: str, default: str) -> str:
    """Read a setting from app_settings or return default."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(AppSetting.value).where(AppSetting.key == key)
        )
        value = result.scalar_one_or_none()
        return value if value is not None else default


async def _upsert_setting(key: str, value: str, admin_id: uuid.UUID | None = None) -> None:
    """Insert or update a setting in app_settings."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
            if admin_id:
                existing.updated_by_admin_id = admin_id
        else:
            session.add(AppSetting(key=key, value=value, updated_by_admin_id=admin_id))
        await session.commit()


async def get_llm_provider() -> str:
    """Get LLM provider for the main agent. Defaults to 'openai'."""
    return await _get_setting("llm_provider", "openai")


async def get_llm_model() -> str:
    """Get LLM model for the main agent. Defaults to env OPENAI_TEXT_MODEL."""
    return await _get_setting("llm_model", settings.openai_text_model)


async def get_censor_provider() -> str:
    """Get LLM provider for the censor agent. Defaults to 'openai'."""
    return await _get_setting("censor_provider", "openai")


async def get_censor_model() -> str:
    """Get LLM model for the censor agent. Defaults to env OPENAI_TEXT_MODEL."""
    return await _get_setting("censor_model", settings.openai_text_model)


async def get_llm_history_messages() -> int:
    """Get number of dialogue history records to include in LLM requests."""
    raw_value = await _get_setting(
        "llm_history_messages",
        str(settings.llm_history_messages or DEFAULT_LLM_HISTORY_MESSAGES),
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid llm_history_messages value %r; falling back to %s",
            raw_value,
            DEFAULT_LLM_HISTORY_MESSAGES,
        )
        return DEFAULT_LLM_HISTORY_MESSAGES

    if value < 0:
        logger.warning(
            "Negative llm_history_messages value %r; falling back to %s",
            raw_value,
            DEFAULT_LLM_HISTORY_MESSAGES,
        )
        return DEFAULT_LLM_HISTORY_MESSAGES

    return min(value, MAX_LLM_HISTORY_MESSAGES)


async def save_llm_settings(
    llm_provider: str,
    llm_model: str,
    censor_provider: str,
    censor_model: str,
    llm_history_messages: int,
    admin_id: uuid.UUID | None = None,
) -> None:
    """Save all LLM settings at once."""
    await _upsert_setting("llm_provider", llm_provider, admin_id)
    await _upsert_setting("llm_model", llm_model, admin_id)
    await _upsert_setting("censor_provider", censor_provider, admin_id)
    await _upsert_setting("censor_model", censor_model, admin_id)
    await _upsert_setting("llm_history_messages", str(llm_history_messages), admin_id)
    logger.info(
        f"LLM settings saved: main={llm_provider}/{llm_model}, "
        f"censor={censor_provider}/{censor_model}, "
        f"history_messages={llm_history_messages}"
    )
