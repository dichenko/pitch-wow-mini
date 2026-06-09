"""Azure Speech TTS provider."""

import html
from pathlib import Path
from typing import Any

import httpx

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.speech.base import SpeechProviderError, TextToSpeechResult
from apps.bot.app.speech.http_utils import response_error, retry_http
from apps.bot.app.speech.temp_files import create_temp_audio_path
from apps.bot.app.speech.text import prepare_text_for_tts, truncate_text


class AzureSpeechProvider:
    """Azure TTS adapter kept as an alternative provider."""

    def __init__(self, settings: BotSettings | None = None, client: Any | None = None):
        self.settings = settings or get_settings()
        self.client = client

    def build_ssml(self, text: str) -> str:
        escaped_text = html.escape(text, quote=False)
        prosody_attrs = f' rate="{html.escape(self.settings.azure_tts_rate)}"'
        if self.settings.azure_tts_pitch:
            prosody_attrs += f' pitch="{html.escape(self.settings.azure_tts_pitch)}"'
        if self.settings.azure_tts_range:
            prosody_attrs += f' range="{html.escape(self.settings.azure_tts_range)}"'
        return (
            f'<speak version="1.0" xml:lang="{html.escape(self.settings.azure_tts_language)}">'
            f'<voice name="{html.escape(self.settings.azure_tts_voice)}">'
            f"<prosody{prosody_attrs}>{escaped_text}</prosody>"
            "</voice></speak>"
        )

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        if not self.settings.azure_speech_key or not self.settings.azure_speech_endpoint:
            raise SpeechProviderError("Azure Speech TTS is not configured")

        prepared = truncate_text(
            prepare_text_for_tts(text),
            self.settings.azure_tts_max_chars,
        )
        if not prepared:
            raise SpeechProviderError("Azure TTS received empty text")

        ssml = self.build_ssml(prepared)

        async def post() -> httpx.Response:
            return await self._post(
                self.settings.azure_speech_endpoint,
                headers={
                    "Ocp-Apim-Subscription-Key": self.settings.azure_speech_key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": self.settings.azure_tts_output_format,
                    "User-Agent": "assistant-bot",
                },
                content=ssml.encode("utf-8"),
                timeout=self.settings.azure_tts_timeout_ms / 1000.0,
            )

        response = await retry_http(post)
        if response.status_code >= 400:
            raise response_error(response)
        if not response.content:
            raise SpeechProviderError("Azure TTS returned empty audio")

        suffix = ".ogg" if "opus" in self.settings.azure_tts_output_format else ".wav"
        output_path = create_temp_audio_path(suffix=suffix)
        Path(output_path).write_bytes(response.content)
        return TextToSpeechResult(
            file_path=str(output_path),
            mime_type="audio/ogg" if suffix == ".ogg" else "audio/wav",
            format="opus" if suffix == ".ogg" else "wav",
            provider="azure",
            model=self.settings.azure_tts_output_format,
            voice=self.settings.azure_tts_voice,
        )

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        if self.client is not None:
            return await self.client.post(url, **kwargs)
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)
