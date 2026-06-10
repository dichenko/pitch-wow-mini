"""Shared localized welcome prompt constants."""

from packages.shared.utils.languages import DEFAULT_LANGUAGE, Language, normalize_preferred_language

WELCOME_PROMPT_KINDS: dict[Language, str] = {
    "ru": "welcome_message_ru",
    "uz": "welcome_message_uz",
    "en": "welcome_message_en",
}

DEFAULT_WELCOME_MESSAGES: dict[Language, str] = {
    "ru": (
        "Привет! Я AI-ассистент. Чем могу помочь?\n\n"
        "Для администраторов: используйте /admin для входа в панель управления."
    ),
    "uz": (
        "Salom! Men AI-assistentman. Sizga qanday yordam bera olaman?\n\n"
        "Administratorlar uchun: boshqaruv paneliga kirish uchun /admin buyrug'idan foydalaning."
    ),
    "en": (
        "Hello! I am an AI assistant. How can I help?\n\n"
        "For administrators: use /admin to sign in to the admin panel."
    ),
}

DEFAULT_WELCOME = DEFAULT_WELCOME_MESSAGES[DEFAULT_LANGUAGE]


def get_welcome_prompt_kind(language: str | None) -> str:
    normalized = normalize_preferred_language(language) or DEFAULT_LANGUAGE
    return WELCOME_PROMPT_KINDS[normalized]


def get_default_welcome_message(language: str | None) -> str:
    normalized = normalize_preferred_language(language) or DEFAULT_LANGUAGE
    return DEFAULT_WELCOME_MESSAGES[normalized]
