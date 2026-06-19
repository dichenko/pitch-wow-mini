"""Artifact delivery service."""

import logging
import os
import tempfile
from uuid import UUID

from aiogram.types import FSInputFile

from apps.bot.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_artifact_markdown_to_admin(
    *,
    job_id: UUID,
    user_tg_id: int,
    markdown: str,
) -> None:
    """Send generated artifact Markdown to the configured admin Telegram chat."""
    if not settings.admin_telegram_chat_id:
        logger.info(
            "ADMIN_TELEGRAM_CHAT_ID is empty; skipping artifact delivery job_id=%s",
            job_id,
        )
        return

    tmp_path = None
    try:
        from apps.bot.app.bot_instance import bot

        safe_job_id = str(job_id).replace("-", "")
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            prefix=f"pitch_wow_artifacts_{user_tg_id}_{safe_job_id}_",
            encoding="utf-8",
            delete=False,
        ) as tmp:
            tmp.write(markdown)
            tmp_path = tmp.name

        await bot.send_document(
            int(settings.admin_telegram_chat_id),
            document=FSInputFile(
                tmp_path,
                filename=f"pitch_wow_artifacts_{user_tg_id}_{job_id}.md",
            ),
            caption=f"Pitch Wow artifacts generated for {user_tg_id}",
            parse_mode=None,
        )
    except Exception:
        logger.exception("Failed to deliver artifact Markdown job_id=%s", job_id)
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
