"""Mock speech provider for tests."""

from pathlib import Path

from apps.bot.app.speech.base import SpeechToTextResult, TextToSpeechResult, normalize_language
from apps.bot.app.speech.temp_files import create_temp_audio_path


class MockSpeechProvider:
    def __init__(self, text: str = "mock transcript", audio: bytes = b"mock-audio"):
        self.text = text
        self.audio = audio

    async def transcribe(self, file_path: str, language: str) -> SpeechToTextResult:
        normalized = normalize_language(language)
        return SpeechToTextResult(
            text=self.text,
            provider="mock",
            model="mock-stt",
            language=normalized,
        )

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        output_path = create_temp_audio_path(suffix=".mp3")
        Path(output_path).write_bytes(self.audio)
        return TextToSpeechResult(
            file_path=str(output_path),
            mime_type="audio/mpeg",
            format="mp3",
            provider="mock",
            model="mock-tts",
            voice="mock",
        )
