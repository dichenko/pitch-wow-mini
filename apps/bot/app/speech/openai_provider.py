"""OpenAI STT/TTS speech provider."""

from pathlib import Path
from typing import Any

import httpx

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.speech.base import (
    SpeechProviderError,
    SpeechToTextResult,
    TextToSpeechResult,
    normalize_language,
)
from apps.bot.app.speech.http_utils import response_error, retry_http
from apps.bot.app.speech.temp_files import create_temp_audio_path
from apps.bot.app.speech.text import prepare_text_for_tts

TTS_MIME_TYPES = {
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "aac": "audio/aac",
    "flac": "audio/flac",
    "wav": "audio/wav",
    "pcm": "audio/pcm",
}


class OpenAISpeechProvider:
    """OpenAI provider for Russian/English STT and English TTS."""

    def __init__(self, settings: BotSettings | None = None, client: Any | None = None):
        self.settings = settings or get_settings()
        self.client = client

    async def transcribe(self, file_path: str, language: str) -> SpeechToTextResult:
        if not self.settings.openai_api_key:
            raise SpeechProviderError("OpenAI API key is not configured")

        normalized = normalize_language(language)
        data = {"model": self.settings.openai_stt_model}
        stt_language = self.settings.openai_stt_language or normalized
        if stt_language:
            data["language"] = stt_language

        async def post() -> httpx.Response:
            with open(file_path, "rb") as audio_file:
                files = {"file": ("audio.wav", audio_file, "audio/wav")}
                return await self._post(
                    f"{self.settings.openai_base_url.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    files=files,
                    data=data,
                    timeout=self.settings.openai_stt_timeout_ms / 1000.0,
                )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        payload = response.json()
        text = str(payload.get("text", "")).strip()
        if not text:
            raise SpeechProviderError("OpenAI STT returned empty text")
        return SpeechToTextResult(
            text=text,
            provider="openai",
            model=self.settings.openai_stt_model,
            language=normalized,
        )

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        if not self.settings.openai_api_key:
            raise SpeechProviderError("OpenAI API key is not configured")

        prepared = prepare_text_for_tts(text)
        if not prepared:
            raise SpeechProviderError("OpenAI TTS received empty text")
        if len(prepared) > self.settings.openai_tts_max_chars:
            raise SpeechProviderError("OpenAI TTS text exceeds configured character limit")

        response_format = self.settings.openai_tts_response_format
        resolved_instructions = instructions or self.settings.openai_tts_instructions or ""
        payload: dict[str, Any] = {
            "model": self.settings.openai_tts_model,
            "voice": self.settings.openai_tts_voice,
            "input": prepared,
            "response_format": response_format,
            "speed": self.settings.openai_tts_speed,
        }
        if resolved_instructions:
            payload["instructions"] = resolved_instructions

        async def post() -> httpx.Response:
            return await self._post(
                f"{self.settings.openai_base_url.rstrip('/')}/audio/speech",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json=payload,
                timeout=self.settings.openai_tts_timeout_ms / 1000.0,
            )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        if not response.content:
            raise SpeechProviderError("OpenAI TTS returned empty audio")

        output_path = create_temp_audio_path(suffix=f".{response_format}")
        Path(output_path).write_bytes(response.content)
        return TextToSpeechResult(
            file_path=str(output_path),
            mime_type=TTS_MIME_TYPES.get(response_format, "application/octet-stream"),
            format=response_format,
            provider="openai",
            model=self.settings.openai_tts_model,
            voice=self.settings.openai_tts_voice,
        )

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)
