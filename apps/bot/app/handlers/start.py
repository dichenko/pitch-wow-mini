"""/start command handler."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я AI-ассистент. Чем могу помочь?\n\n"
        "Для администраторов: используйте /admin для входа в панель управления."
    )
