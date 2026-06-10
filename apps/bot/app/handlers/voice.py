"""Voice message handler with profile-language STT and best-effort TTS."""

import asyncio
import logging
import uuid
from pathlib import Path

from aiogram import Router
from aiogram.types import FSInputFile, Message

from apps.bot.app.config import get_settings
from apps.bot.app.services.language_service import require_preferred_language
from apps.bot.app.services.settings_service import get_tts_prompt
from apps.bot.app.speech import SpeechProviderError, create_speech_providers
from apps.bot.app.speech.temp_files import (
    cleanup_temp_file,
    create_temp_audio_path,
    ensure_ogg,
    validate_file_size,
)

logger = logging.getLogger(__name__)
router = Router()
settings = get_settings()

TTS_FALLBACK_MESSAGES = {
    "ru": "Я подготовил ответ текстом, но сейчас не смог озвучить его голосом.",
    "uz": "Javobni matn shaklida tayyorladim, lekin hozir uni ovoz bilan yubora olmadim.",
    "en": "I prepared the text answer, but could not send it as voice right now.",
}

VOICE_DISABLED_MESSAGES = {
    "ru": "Голосовые сообщения отключены. Пожалуйста, отправьте ваше сообщение текстом.",
    "uz": "Ovozli xabarlar o'chirilgan. Iltimos, xabaringizni matn shaklida yuboring.",
    "en": "Voice messages are disabled. Please send your message as text.",
}

FILE_TOO_LARGE_MESSAGES = {
    "ru": "Файл слишком большой (макс. {max_size} МБ). Пожалуйста, отправьте более короткое голосовое сообщение.",
    "uz": "Fayl juda katta (maks. {max_size} MB). Iltimos, qisqaroq ovozli xabar yuboring.",
    "en": "The file is too large (max. {max_size} MB). Please send a shorter voice message.",
}

DURATION_TOO_LONG_MESSAGES = {
    "ru": "Голосовое сообщение слишком длинное (макс. {max_duration} сек). Пожалуйста, отправьте более короткое сообщение.",
    "uz": "Ovozli xabar juda uzun (maks. {max_duration} soniya). Iltimos, qisqaroq xabar yuboring.",
    "en": "The voice message is too long (max. {max_duration} seconds). Please send a shorter message.",
}

VOICE_RECOGNITION_ERROR_MESSAGES = {
    "ru": "Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом.",
    "uz": "Ovozli xabarni taniy olmadim, iltimos, matn shaklida yuboring.",
    "en": "Could not recognize the voice message. Please send it as text.",
}


@router.message(lambda m: m.voice or m.audio)
async def handle_voice(message: Message) -> None:
    if not message.from_user:
        return

    language = await require_preferred_language(message)
    if language is None:
        return

    if not settings.voice_enabled:
        await message.answer(VOICE_DISABLED_MESSAGES[language])
        return

    trace_id = str(uuid.uuid4())
    media = message.voice or message.audio
    if not media:
        return

    input_path: Path | None = None
    normalized_path: Path | None = None
    tts_original_path: Path | None = None
    tts_voice_path: Path | None = None

    file_size_mb = media.file_size / (1024 * 1024) if media.file_size else 0
    if file_size_mb > settings.voice_max_audio_size_mb:
        await message.answer(
            FILE_TOO_LARGE_MESSAGES[language].format(
                max_size=settings.voice_max_audio_size_mb
            )
        )
        return

    try:
        input_path = create_temp_audio_path(suffix=".ogg")
        normalized_path = create_temp_audio_path(suffix=".wav")

        file = await message.bot.get_file(media.file_id)
        if not file.file_path:
            raise SpeechProviderError("Telegram did not return a file path")
        await message.bot.download_file(file.file_path, input_path)

        validate_file_size(input_path, max_size_mb=settings.voice_max_audio_size_mb)
        await _normalize_for_stt(input_path, normalized_path)

        duration = await _probe_duration(normalized_path)
        if duration > settings.voice_max_duration_sec:
            await message.answer(
                DURATION_TOO_LONG_MESSAGES[language].format(
                    max_duration=settings.voice_max_duration_sec
                )
            )
            return

        providers = create_speech_providers(settings)
        stt_provider = providers.stt_for_language(language)
        stt_result = await stt_provider.transcribe(str(normalized_path), language)

        if not stt_result.text.strip():
            raise SpeechProviderError("STT returned empty text")

        from apps.bot.app.handlers.message import process_user_text

        response_text = await process_user_text(
            message=message,
            user_text=stt_result.text,
            response_language=language,
        )
        if not response_text:
            return

        try:
            tts_prompt = (await get_tts_prompt(language)).strip() or None
            tts_provider = providers.tts_for_language(language)
            tts_result = await tts_provider.synthesize(
                response_text,
                language,
                instructions=tts_prompt,
            )
            tts_original_path = Path(tts_result.file_path)
            tts_voice_path = await ensure_ogg(tts_original_path)
            audio = FSInputFile(tts_voice_path, filename="voice.ogg")
            await message.answer_voice(audio)
            logger.info(
                "TTS voice sent trace_id=%s provider=%s model=%s language=%s format=%s",
                trace_id,
                tts_result.provider,
                tts_result.model,
                language,
                tts_result.format,
            )
        except Exception as exc:
            logger.error(
                "TTS failed trace_id=%s language=%s error=%s",
                trace_id,
                language,
                exc,
                exc_info=True,
            )
            await message.answer(TTS_FALLBACK_MESSAGES[language])

    except Exception as exc:
        logger.error(
            "Voice processing error trace_id=%s language=%s error=%s",
            trace_id,
            language,
            exc,
            exc_info=True,
        )
        await message.answer(VOICE_RECOGNITION_ERROR_MESSAGES[language])
    finally:
        await cleanup_temp_file(input_path, reason="telegram_voice_input_cleanup")
        await cleanup_temp_file(normalized_path, reason="telegram_voice_normalized_cleanup")
        await cleanup_temp_file(tts_original_path, reason="telegram_tts_original_cleanup")
        await cleanup_temp_file(tts_voice_path, reason="telegram_tts_voice_cleanup")


async def _normalize_for_stt(input_path: Path, output_path: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
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
        raise SpeechProviderError(f"ffmpeg failed to normalize audio: {detail}")


async def _probe_duration(file_path: Path) -> float:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    try:
        return float(stdout.decode("utf-8").strip())
    except ValueError:
        return 0.0
