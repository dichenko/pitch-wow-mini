"""Bot service entry point."""

import logging

from aiogram import Dispatcher
from fastapi import FastAPI

from apps.bot.app.bot_instance import bot
from apps.bot.app.config import get_settings
from apps.bot.app.filters import is_private_message
from apps.bot.app.handlers import admin, message, restart, start, voice
from apps.bot.app.services.admin_service import bootstrap_root_admin
from apps.bot.app.services.seed_service import seed_defaults
from packages.shared.utils.logging import setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()

setup_logging("DEBUG" if settings.app_env == "dev" else "INFO")

dp = Dispatcher()
dp.message.filter(is_private_message)

# Register handlers
dp.include_router(start.router)
dp.include_router(admin.router)
dp.include_router(restart.router)
dp.include_router(voice.router)
dp.include_router(message.router)  # message handler last (catch-all)

app = FastAPI(title="AI Assistant Bot", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Bot service starting up")
    await seed_defaults()
    await bootstrap_root_admin()
    if settings.bot_mode == "webhook":
        webhook_url = f"{settings.bot_public_url}/webhook"
        await bot.set_webhook(
            webhook_url,
            secret_token=settings.telegram_webhook_secret or None,
        )
        logger.info(f"Webhook set to {webhook_url}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("Bot service shutting down")
    await bot.session.close()


@app.get("/health")
async def health() -> dict:
    return {"status": "OK", "service": "bot"}


async def main() -> None:
    if settings.bot_mode == "polling":
        logger.info("Starting in polling mode")
        await dp.start_polling(bot)
    else:
        logger.info("Starting in webhook mode via FastAPI")
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
