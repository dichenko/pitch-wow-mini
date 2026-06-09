"""Speech provider layer for STT/TTS integrations."""

from apps.bot.app.speech.base import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Language,
    SpeechProviderError,
    SpeechProviders,
    SpeechToTextProvider,
    SpeechToTextResult,
    TextToSpeechProvider,
    TextToSpeechResult,
    normalize_language,
)
from apps.bot.app.speech.factory import create_speech_providers
from apps.bot.app.speech.language_detection import detect_language_from_text

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "Language",
    "SpeechProviderError",
    "SpeechProviders",
    "SpeechToTextProvider",
    "SpeechToTextResult",
    "TextToSpeechProvider",
    "TextToSpeechResult",
    "create_speech_providers",
    "detect_language_from_text",
    "normalize_language",
]
