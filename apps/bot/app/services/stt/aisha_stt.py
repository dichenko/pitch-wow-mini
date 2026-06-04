"""Aisha STT provider — fallback speech-to-text (primarily Uzbek)."""

import logging

import httpx

from apps.bot.app.config import get_settings
from apps.bot.app.services.stt.base import BaseSttProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class AishaSttProvider(BaseSttProvider):
    """Aisha STT fallback provider, primarily for Uzbek language.

    TODO: API format may need adjustment once API key is available for testing.
    See: https://aisha.group/ru/api-documentation
    """

    async def transcribe(self, audio_path: str) -> str | None:
        if not settings.aisha_api_key or not settings.aisha_base_url:
            logger.warning("Aisha STT not configured (AISHA_API_KEY / AISHA_BASE_URL), skipping")
            return None

        try:
            async with httpx.AsyncClient(
                timeout=settings.aisha_stt_timeout_ms / 1000.0
            ) as client:
                with open(audio_path, "rb") as audio_file:
                    files = {"audio": ("audio.wav", audio_file, "audio/wav")}
                    data = {
                        "language": settings.aisha_stt_language or "uz",
                    }
                    headers = {
                        "Authorization": f"Bearer {settings.aisha_api_key}",
                    }

                    # TODO: Verify endpoint format with actual API documentation
                    response = await client.post(
                        f"{settings.aisha_base_url.rstrip('/')}/stt/transcribe",
                        files=files,
                        data=data,
                        headers=headers,
                    )
                    response.raise_for_status()
                    result = response.json()
                    text = result.get("text", "").strip()
                    return text if text else None

        except Exception as e:
            logger.error(f"Aisha STT error: {e}")
            return None
