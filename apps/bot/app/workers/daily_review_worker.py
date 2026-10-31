"""Daily administrator reviews at 23:55 Moscow time."""

import asyncio
import logging
from datetime import datetime, timezone

from apps.bot.app.config import get_settings
from apps.bot.app.services.daily_reviews import enqueue_due_reviews, process_next_review
from packages.shared.utils.logging import setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_worker() -> None:
    setup_logging("DEBUG" if settings.app_env == "dev" else "INFO")
    logger.info("Daily review worker started schedule=%02d:%02d Europe/Moscow enabled=%s",
                settings.daily_review_hour, settings.daily_review_minute, settings.daily_reviews_enabled)
    try:
        while True:
            if settings.daily_reviews_enabled:
                try:
                    queued = await enqueue_due_reviews(datetime.now(timezone.utc))
                    if queued:
                        logger.info("Daily reviews queued count=%s", queued)
                    while await process_next_review(datetime.now(timezone.utc)):
                        pass
                except Exception:
                    # Database/migration outages must not permanently stop scheduling.
                    logger.exception("Daily review worker iteration failed")
            await asyncio.sleep(settings.daily_review_poll_interval_sec)
    finally:
        from apps.bot.app.bot_instance import bot

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_worker())
