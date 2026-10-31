"""Poll every ten minutes for users silent for more than an hour."""

import asyncio
import logging
from datetime import datetime, timezone

from apps.bot.app.config import get_settings
from apps.bot.app.services.inactivity_reviews import enqueue_inactive_reviews, process_next_review
from packages.shared.utils.logging import setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_worker() -> None:
    setup_logging("DEBUG" if settings.app_env == "dev" else "INFO")
    logger.info("Inactivity review worker started poll_interval_sec=%s timeout_minutes=%s enabled=%s",
                settings.inactivity_review_poll_interval_sec, settings.inactivity_timeout_minutes,
                settings.inactivity_reviews_enabled)
    try:
        while True:
            started_at = asyncio.get_running_loop().time()
            if settings.inactivity_reviews_enabled:
                try:
                    queued = await enqueue_inactive_reviews(datetime.now(timezone.utc))
                    if queued:
                        logger.info("Inactivity reviews queued count=%s", queued)
                    while await process_next_review(datetime.now(timezone.utc)):
                        pass
                except Exception:
                    # Database/migration outages must not permanently stop scheduling.
                    logger.exception("Inactivity review worker iteration failed")
            elapsed = asyncio.get_running_loop().time() - started_at
            await asyncio.sleep(max(0, settings.inactivity_review_poll_interval_sec - elapsed))
    finally:
        from apps.bot.app.bot_instance import bot

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
