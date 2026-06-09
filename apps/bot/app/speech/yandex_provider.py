"""Yandex SpeechKit TTS provider."""

from pathlib import Path
from typing import Any

import httpx

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.speech.base import SpeechProviderError, TextToSpeechResult
from apps.bot.app.speech.http_utils import response_error, retry_http
from apps.bot.app.speech.temp_files import create_temp_audio_path
from apps.bot.app.speech.text import prepare_russian_text_for_tts, truncate_text


class YandexSpeechKitProvider:
    """Yandex SpeechKit provider for Russian TTS."""

    def __init__(self, settings: BotSettings | None = None, client: Any | None = None):
        self.settings = settings or get_settings()
        self.client = client

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        if not self.settings.yandex_speechkit_api_key:
            raise SpeechProviderError("Yandex SpeechKit API key is not configured")

        prepared = truncate_text(
            prepare_russian_text_for_tts(text),
            self.settings.yandex_tts_max_chars,
        )
        if not prepared:
            raise SpeechProviderError("Yandex TTS received empty text")

        data = {
            "text": prepared,
            "lang": self.settings.yandex_tts_language,
            "voice": self.settings.yandex_tts_voice,
            "emotion": self.settings.yandex_tts_emotion,
            "speed": str(self.settings.yandex_tts_speed),
            "format": self.settings.yandex_tts_format,
        }

        async def post() -> httpx.Response:
            return await self._post(
                f"{self.settings.yandex_tts_base_url.rstrip('/')}/speech/v1/tts:synthesize",
                headers={"Authorization": f"Api-Key {self.settings.yandex_speechkit_api_key}"},
                data=data,
                timeout=self.settings.yandex_tts_timeout_ms / 1000.0,
            )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        if not response.content:
            raise SpeechProviderError("Yandex TTS returned empty audio")

        output_path = create_temp_audio_path(suffix=".ogg")
        Path(output_path).write_bytes(response.content)
        return TextToSpeechResult(
            file_path=str(output_path),
            mime_type="audio/ogg",
            format="opus",
            provider="yandex",
            model=self.settings.yandex_tts_model,
            voice=self.settings.yandex_tts_voice,
        )

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)
