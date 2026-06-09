"""Lightweight language detection for supported voice replies."""

import re

from apps.bot.app.speech.base import Language

RUSSIAN_STOP_WORDS = {
    "в",
    "и",
    "как",
    "мне",
    "на",
    "не",
    "по",
    "привет",
    "сколько",
    "что",
    "это",
}
ENGLISH_STOP_WORDS = {
    "and",
    "hello",
    "how",
    "is",
    "please",
    "the",
    "what",
    "you",
}
UZBEK_LATIN_MARKERS = {
    "assalomu",
    "bilan",
    "emas",
    "ha",
    "men",
    "nima",
    "qanday",
    "rahmat",
    "salom",
    "siz",
    "yo'q",
}


def detect_language_from_text(text: str) -> Language | None:
    """Detect one of the supported languages from transcribed text.

    Returns None when confidence is too low. Voice TTS is best-effort, so an
    uncertain detector should skip TTS instead of selecting a wrong provider.
    """
    normalized = text.strip().lower()
    if not normalized:
        return None

    if re.search(r"[ўқғҳ]", normalized):
        return "uz"

    words = set(re.findall(r"[a-zа-яёўқғҳ']+", normalized))
    uz_score = len(words & UZBEK_LATIN_MARKERS)
    ru_score = len(words & RUSSIAN_STOP_WORDS)
    en_score = len(words & ENGLISH_STOP_WORDS)

    if uz_score >= 1:
        return "uz"

    has_cyrillic = bool(re.search(r"[а-яё]", normalized))
    has_latin = bool(re.search(r"[a-z]", normalized))

    if has_cyrillic and ru_score >= 1:
        return "ru"
    if has_cyrillic and not has_latin:
        return "ru"

    if has_latin and en_score >= 1:
        return "en"

    scores: dict[Language, int] = {"ru": ru_score, "uz": uz_score, "en": en_score}
    language, score = max(scores.items(), key=lambda item: item[1])
    if score > 0 and list(scores.values()).count(score) == 1:
        return language
    return None
