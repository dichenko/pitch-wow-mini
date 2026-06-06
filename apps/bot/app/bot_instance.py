"""Bot instance — created once and shared across modules.

Prevents re-execution of main.py when imported from tools.
"""

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apps.bot.app.config import get_settings

settings = get_settings()

bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
