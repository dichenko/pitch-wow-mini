"""Shared bot event filters."""

from aiogram.enums import ChatType
from aiogram.types import Message


def is_private_message(message: Message) -> bool:
    """Allow message handlers only in private Telegram chats."""
    chat_type = getattr(getattr(message, "chat", None), "type", None)
    return chat_type in (ChatType.PRIVATE, ChatType.PRIVATE.value)
