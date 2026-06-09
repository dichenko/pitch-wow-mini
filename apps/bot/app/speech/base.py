"""Shared speech contracts and language helpers."""

from dataclasses import dataclass
from typing import Literal, Protocol

Language = Literal["ru", "uz", "en"]
ProviderName = Literal["openai", "aisha", "yandex", "azure", "mock"]
AudioFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]

SUPPORTED_LANGUAGES: tuple[Language, ...] = ("ru", "uz", "en")
DEFAULT_LANGUAGE: Language = "ru"


def normalize_language(language: str | None) -> Language:
    """Return a supported language, falling back to Russian."""
    if language in SUPPORTED_LANGUAGES:
        return language  # type: ignore[return-value]
    return DEFAULT_LANGUAGE


class SpeechProviderError(RuntimeError):
    """Raised when a speech provider cannot complete an operation safely."""


class AudioValidationError(SpeechProviderError):
    """Raised when an audio file violates configured limits."""


@dataclass(frozen=True)
class SpeechToTextResult:
    text: str
    provider: ProviderName
    model: str
    language: Language


@dataclass(frozen=True)
class TextToSpeechResult:
    file_path: str
    mime_type: str
    format: AudioFormat
    provider: ProviderName
    model: str
    voice: str | None = None


class SpeechToTextProvider(Protocol):
    async def transcribe(
        self,
        file_path: str,
        language: str | None = None,
    ) -> SpeechToTextResult:
        ...


class TextToSpeechProvider(Protocol):
    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        ...


@dataclass(frozen=True)
class SpeechProviders:
    openai: SpeechToTextProvider
    aisha: SpeechToTextProvider
    yandex: TextToSpeechProvider
    azure: TextToSpeechProvider

    def stt_for_language(self, language: str) -> SpeechToTextProvider:
        normalized = normalize_language(language)
        if normalized == "uz":
            return self.aisha
        return self.openai

    def tts_for_language(self, language: str) -> TextToSpeechProvider:
        normalized = normalize_language(language)
        if normalized == "uz":
            return self.aisha  # type: ignore[return-value]
        if normalized == "ru":
            return self.yandex
        return self.openai  # type: ignore[return-value]
