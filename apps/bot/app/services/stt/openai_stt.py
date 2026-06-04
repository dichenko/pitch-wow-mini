"""OpenAI STT provider — primary speech-to-text."""

import logging

import httpx

from apps.bot.app.config import get_settings
from apps.bot.app.services.stt.base import BaseSttProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAISttProvider(BaseSttProvider):
    """OpenAI Whisper/gpt-4o-transcribe STT provider."""

    async def transcribe(self, audio_path: str) -> str | None:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not configured, skipping OpenAI STT")
            return None

        try:
            async with httpx.AsyncClient(
                timeout=settings.openai_stt_timeout_ms / 1000.0
            ) as client:
                with open(audio_path, "rb") as audio_file:
                    files = {"file": ("audio.wav", audio_file, "audio/wav")}
                    data = {
                        "model": settings.openai_stt_model,
                    }
                    if settings.openai_stt_language:
                        data["language"] = settings.openai_stt_language

                    headers = {
                        "Authorization": f"Bearer {settings.openai_api_key}",
                    }

                    response = await client.post(
                        f"{settings.openai_base_url}/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    result = response.json()
                    text = result.get("text", "").strip()
                    return text if text else None

        except Exception as e:
            logger.error(f"OpenAI STT error: {e}")
            return None
