"""Small HTTP helpers shared by speech providers."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from apps.bot.app.speech.base import SpeechProviderError

TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
RETRY_DELAYS = (0, 2, 5)


def response_error(response: httpx.Response) -> SpeechProviderError:
    body = response.text[:1000] if response.text else ""
    return SpeechProviderError(
        f"Speech provider returned HTTP {response.status_code}: {body}"
    )


async def retry_http(operation: Callable[[], Awaitable[Any]]) -> Any:
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS):
        if delay:
            await asyncio.sleep(delay)
        try:
            response = await operation()
            status_code = getattr(response, "status_code", None)
            if status_code in TRANSIENT_STATUSES and attempt < len(RETRY_DELAYS) - 1:
                last_error = response_error(response)
                continue
            return response
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt == len(RETRY_DELAYS) - 1:
                break

    raise SpeechProviderError(f"Speech provider request failed: {last_error}")
