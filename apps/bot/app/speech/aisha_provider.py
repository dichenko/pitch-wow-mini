"""Aisha STT/TTS speech provider."""

from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
import logging

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.speech.base import (
    SpeechProviderError,
    SpeechToTextResult,
    TextToSpeechResult,
    normalize_language,
)
from apps.bot.app.speech.http_utils import response_error, retry_http
from apps.bot.app.speech.temp_files import create_temp_audio_path
from apps.bot.app.speech.text import prepare_text_for_tts, truncate_text

logger = logging.getLogger(__name__)


class AishaSpeechProvider:
    """Aisha provider for Uzbek STT and TTS."""

    def __init__(self, settings: BotSettings | None = None, client: Any | None = None):
        self.settings = settings or get_settings()
        self.client = client

    async def transcribe(
        self,
        file_path: str,
        language: str | None = None,
    ) -> SpeechToTextResult:
        if not self.settings.aisha_api_key or not self.settings.aisha_base_url:
            raise SpeechProviderError("Aisha STT is not configured")

        normalized = normalize_language(language)

        async def post() -> httpx.Response:
            with open(file_path, "rb") as audio_file:
                files = {"audio": ("audio.wav", audio_file, "audio/wav")}
                data = {"language": self.settings.aisha_stt_language or normalized}
                return await self._post(
                    f"{self.settings.aisha_base_url.rstrip('/')}/api/v1/stt/post/",
                    headers={"X-Api-Key": self.settings.aisha_api_key},
                    files=files,
                    data=data,
                    timeout=self.settings.aisha_stt_timeout_ms / 1000.0,
                )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        payload = response.json()
        logger.info("Aisha STT raw response: %s", payload)
        text = str(payload.get("text", "")).strip()
        if not text:
            raise SpeechProviderError("Aisha STT returned empty text")
        return SpeechToTextResult(
            text=text,
            provider="aisha",
            model="aisha-stt",
            language=normalized,
        )

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        if not self.settings.aisha_api_key or not self.settings.aisha_base_url:
            raise SpeechProviderError("Aisha TTS is not configured")

        prepared = truncate_text(
            prepare_text_for_tts(text),
            self.settings.aisha_tts_max_chars,
        )
        if not prepared:
            raise SpeechProviderError("Aisha TTS received empty text")

        data = {
            "transcript": prepared,
            "language": self.settings.aisha_tts_language,
            "model": self.settings.aisha_tts_model,
            "mood": self.settings.aisha_tts_mood,
            "speed": str(self.settings.aisha_tts_speed),
        }
        multipart_fields = {key: (None, value) for key, value in data.items()}

        async def post() -> httpx.Response:
            return await self._post(
                f"{self.settings.aisha_base_url.rstrip('/')}/api/v1/tts/post/",
                headers={
                    "X-Api-Key": self.settings.aisha_api_key,
                    "Accept-Language": self.settings.aisha_tts_language,
                },
                files=multipart_fields,
                timeout=self.settings.aisha_tts_timeout_ms / 1000.0,
            )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        payload = response.json()
        audio_path = str(payload.get("audio_path", "")).strip()
        if not audio_path:
            raise SpeechProviderError("Aisha TTS response did not include audio_path")

        audio_url = urljoin(f"{self.settings.aisha_base_url.rstrip('/')}/", audio_path.lstrip("/"))

        async def get_audio() -> httpx.Response:
            return await self._get(
                audio_url,
                headers={"X-Api-Key": self.settings.aisha_api_key},
                timeout=self.settings.aisha_tts_timeout_ms / 1000.0,
            )

        audio_response = await retry_http(get_audio)
        if audio_response.status_code >= 400:
            raise response_error(audio_response)
        if not audio_response.content:
            raise SpeechProviderError("Aisha TTS returned empty audio")

        output_path = create_temp_audio_path(suffix=".wav")
        Path(output_path).write_bytes(audio_response.content)
        return TextToSpeechResult(
            file_path=str(output_path),
            mime_type="audio/wav",
            format="wav",
            provider="aisha",
            model="aisha-tts",
            voice=self.settings.aisha_tts_model,
        )

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)

    async def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.get(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.get(url, **kwargs)
