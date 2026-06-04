"""/start command handler."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from apps.bot.app.agent.agent import reset_user_thread

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.from_user:
        reset_user_thread(message.from_user.id)
    await message.answer(
        "Привет! Я AI-ассистент. Чем могу помочь?\n\n"
        "Для администраторов: используйте /admin для входа в панель управления."
    )
