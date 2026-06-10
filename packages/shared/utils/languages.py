"""Shared supported-language constants without app-specific dependencies."""

from typing import Literal

Language = Literal["ru", "uz", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("ru", "uz", "en")
DEFAULT_LANGUAGE: Language = "ru"

LANGUAGE_LABELS: dict[Language, str] = {
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O'zbekcha",
    "en": "🇬🇧 English",
}


def normalize_preferred_language(language: str | None) -> Language | None:
    if language in SUPPORTED_LANGUAGES:
        return language  # type: ignore[return-value]
    return None
