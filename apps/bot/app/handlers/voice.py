"""Voice message handler — STT pipeline with OpenAI primary and Aisha fallback."""

import logging
import os
import uuid

from aiogram import Router
from aiogram.types import Message

from apps.bot.app.config import get_settings
from apps.bot.app.services.stt.aisha_stt import AishaSttProvider
from apps.bot.app.services.stt.openai_stt import OpenAISttProvider

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()


@router.message(lambda m: m.voice or m.audio)
async def handle_voice(message: Message) -> None:
    if not settings.voice_enabled:
        await message.answer(
            "Голосовые сообщения отключены. Пожалуйста, отправьте ваше сообщение текстом."
        )
        return

    if not message.from_user:
        return

    trace_id = str(uuid.uuid4())
    voice = message.voice or message.audio
    if not voice:
        return

    # Check file size
    file_size_mb = voice.file_size / (1024 * 1024) if voice.file_size else 0
    if file_size_mb > settings.voice_max_audio_size_mb:
        await message.answer(
            f"Файл слишком большой (макс. {settings.voice_max_audio_size_mb} МБ). "
            "Пожалуйста, отправьте более короткое голосовое сообщение."
        )
        return

    # Download file
    os.makedirs(settings.voice_temp_dir, exist_ok=True)
    file_id = voice.file_id
    temp_path = os.path.join(settings.voice_temp_dir, f"{trace_id}_raw.ogg")
    normalized_path = os.path.join(settings.voice_temp_dir, f"{trace_id}_normalized.wav")

    try:
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(file.file_path, temp_path)

        # Normalize with ffmpeg
        import subprocess

        subprocess.run(
            ["ffmpeg", "-y", "-i", temp_path, "-ar", "16000", "-ac", "1", normalized_path],
            check=True,
            capture_output=True,
        )

        # Check duration
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", normalized_path],
            capture_output=True, text=True,
        )
        try:
            duration = float(result.stdout.strip())
        except ValueError:
            duration = 0.0

        if duration > settings.voice_max_duration_sec:
            await message.answer(
                f"Голосовое сообщение слишком длинное (макс. {settings.voice_max_duration_sec} сек). "
                "Пожалуйста, отправьте более короткое сообщение."
            )
            return

        # Try OpenAI STT first
        openai_provider = OpenAISttProvider()
        transcribed_text = await openai_provider.transcribe(normalized_path)

        # Fallback to Aisha STT if OpenAI fails
        if not transcribed_text:
            logger.info(f"OpenAI STT failed for trace_id={trace_id}, trying Aisha fallback")
            aisha_provider = AishaSttProvider()
            transcribed_text = await aisha_provider.transcribe(normalized_path)

        if not transcribed_text:
            await message.answer(
                "Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом"
            )
            logger.warning(f"Both STT providers failed for trace_id={trace_id}")
            return

        # Process transcribed text as regular message
        from apps.bot.app.handlers.message import handle_message as process_text

        # Create a pseudo-message context
        message.text = transcribed_text
        await process_text(message)

    except Exception as e:
        logger.error(f"Voice processing error trace_id={trace_id}: {e}", exc_info=True)
        await message.answer(
            "Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом"
        )
    finally:
        # Cleanup temp files
        for path in (temp_path, normalized_path):
            if os.path.exists(path):
                os.remove(path)
