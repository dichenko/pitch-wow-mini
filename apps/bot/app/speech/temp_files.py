"""Temporary audio file helpers for speech pipelines."""

import asyncio
import logging
import tempfile
from pathlib import Path

from apps.bot.app.config import get_settings
from apps.bot.app.speech.base import AudioValidationError, SpeechProviderError

logger = logging.getLogger(__name__)


def create_temp_audio_path(*, suffix: str, temp_dir: str | Path | None = None) -> Path:
    settings = get_settings()
    target_dir = Path(temp_dir or settings.speech_temp_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="assistant-audio-",
        suffix=suffix,
        dir=target_dir,
        delete=False,
    )
    path = Path(handle.name)
    handle.close()
    return path


async def cleanup_temp_file(file_path: str | Path | None, *, reason: str = "cleanup") -> None:
    if not file_path:
        return

    path = Path(file_path)
    try:
        if path.exists():
            path.unlink()
            logger.debug("Removed temp audio file path=%s reason=%s", path, reason)
    except Exception as exc:
        logger.warning(
            "Failed to remove temp audio file path=%s reason=%s error=%s",
            path,
            reason,
            exc,
        )


def validate_file_size(file_path: str | Path, *, max_size_mb: int) -> None:
    path = Path(file_path)
    size_bytes = path.stat().st_size
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise AudioValidationError(
            f"Audio file is too large: {size_bytes} bytes, max {max_bytes} bytes"
        )


async def ensure_ogg(file_path: str | Path) -> Path:
    path = Path(file_path)
    if path.suffix.casefold() in (".ogg", ".opus"):
        return path

    output_path = Path(str(path) + ".ogg")
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-c:a",
        "libopus",
        "-b:a",
        "16k",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="ignore")[:1000] if stderr else ""
        raise SpeechProviderError(f"ffmpeg failed to convert audio to ogg: {detail}")
    return output_path
