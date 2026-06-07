from types import SimpleNamespace

from aiogram.enums import ChatType

from apps.bot.app.filters import is_private_message


def test_private_message_filter_allows_private_chat():
    message = SimpleNamespace(chat=SimpleNamespace(type=ChatType.PRIVATE))

    assert is_private_message(message) is True


def test_private_message_filter_allows_private_chat_string_value():
    message = SimpleNamespace(chat=SimpleNamespace(type="private"))

    assert is_private_message(message) is True


def test_private_message_filter_rejects_group_chat():
    message = SimpleNamespace(chat=SimpleNamespace(type="group"))

    assert is_private_message(message) is False


def test_private_message_filter_rejects_supergroup_chat():
    message = SimpleNamespace(chat=SimpleNamespace(type="supergroup"))

    assert is_private_message(message) is False


def test_private_message_filter_rejects_channel_chat():
    message = SimpleNamespace(chat=SimpleNamespace(type="channel"))

    assert is_private_message(message) is False
