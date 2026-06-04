"""Censor service — optional LLM post-processing of agent responses."""

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage

from apps.bot.app.config import get_settings
from apps.bot.app.db.session import async_session_factory
from apps.bot.app.services.llm_factory import create_llm
from apps.bot.app.services.prompt_service import get_active_censor_prompt
from apps.bot.app.services.settings_service import (
    get_censor_model,
    get_censor_provider,
)
from packages.shared.models.database import CensorRun, PromptVersion
from sqlalchemy import select

logger = logging.getLogger(__name__)
settings = get_settings()


async def apply_censor(
    draft_response: str,
    user_message: str,
    trace_id: str,
    user_tg_id: int,
) -> str:
    """Apply censor LLM pass if enabled. Returns final response.

    On failure, falls back to draft response (best-effort).
    """
    enabled = await is_censor_enabled()
    if not enabled:
        return draft_response

    start_time = time.time()

    try:
        censor_provider = await get_censor_provider()
        censor_model = await get_censor_model()

        censor_prompt = await get_active_censor_prompt()
        if not censor_prompt:
            censor_prompt = "Review and edit the assistant response for appropriateness."

        # Get censor prompt version
        async with async_session_factory() as session:
            result = await session.execute(
                select(PromptVersion.version_number).where(
                    PromptVersion.kind == "censor_prompt",
                    PromptVersion.is_active == True,
                )
            )
            censor_version = result.scalar_one_or_none() or 0

        llm = create_llm(provider=censor_provider, model=censor_model, temperature=0.3)

        messages = [
            SystemMessage(content=censor_prompt),
            HumanMessage(
                content=f"User message: {user_message}\n\n"
                f"Draft response: {draft_response}\n\n"
                f"Return the final edited response."
            ),
        ]

        response = await llm.ainvoke(messages)
        final_response = response.content

        duration_ms = int((time.time() - start_time) * 1000)

        # Log success
        async with async_session_factory() as session:
            run = CensorRun(
                trace_id=trace_id,
                user_tg_id=user_tg_id,
                draft_response=draft_response,
                final_response=final_response,
                censor_prompt_version=censor_version,
                censor_model=censor_model,
                status="success",
                duration_ms=duration_ms,
            )
            session.add(run)
            await session.commit()

        return final_response

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Censor LLM failed trace_id={trace_id}: {e}")

        # Log error
        try:
            async with async_session_factory() as session:
                run = CensorRun(
                    trace_id=trace_id,
                    user_tg_id=user_tg_id,
                    draft_response=draft_response,
                    final_response=draft_response,
                    censor_prompt_version=0,
                    censor_model=censor_model if 'censor_model' in dir() else "unknown",
                    status="error",
                    error=str(e),
                    duration_ms=duration_ms,
                )
                session.add(run)
                await session.commit()
        except Exception:
            pass

        # Fallback: send draft as-is
        return draft_response


async def is_censor_enabled() -> bool:
    """Check if censor is enabled in app_settings."""
    from packages.shared.models.database import AppSetting

    async with async_session_factory() as session:
        result = await session.execute(
            select(AppSetting.value).where(AppSetting.key == "censor_enabled")
        )
        value = result.scalar_one_or_none()
        return value == "true" if value else settings.censor_enabled
