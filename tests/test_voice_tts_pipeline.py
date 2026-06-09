from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.bot.app.handlers import message as message_module
from apps.bot.app.handlers import voice as voice_module
from apps.bot.app.speech.base import SpeechProviderError, SpeechToTextResult


class FakeUser:
    id = 100
    first_name = "Test"
    last_name = None
    username = "tester"
    language_code = "ru"


class FakeMedia:
    file_id = "file-id"
    file_size = 100


class FakeBot:
    async def get_file(self, file_id):
        return SimpleNamespace(file_path="telegram/file.ogg")

    async def download_file(self, file_path, destination):
        Path(destination).write_bytes(b"input")


class FakeMessage:
    from_user = FakeUser()
    voice = FakeMedia()
    audio = None
    bot = FakeBot()

    def __init__(self):
        self.answers = []
        self.voice_answers = []

    async def answer(self, text):
        self.answers.append(text)

    async def answer_voice(self, audio):
        self.voice_answers.append(audio)


class FakeSttProvider:
    async def transcribe(self, file_path, language):
        return SpeechToTextResult(
            text="распознанный текст",
            provider="mock",
            model="mock-stt",
            language="ru",
        )


class FailingTtsProvider:
    async def synthesize(self, text, language, instructions=None):
        raise SpeechProviderError("tts unavailable")


@pytest.mark.asyncio
async def test_voice_pipeline_sends_text_before_tts_fallback(monkeypatch, tmp_path):
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    monkeypatch.setattr(voice_module, "settings", SimpleNamespace(
        voice_enabled=True,
        voice_max_audio_size_mb=25,
        voice_max_duration_sec=120,
    ))
    monkeypatch.setattr(voice_module, "create_temp_audio_path", lambda suffix: next(paths))
    monkeypatch.setattr(voice_module, "_normalize_for_stt", _write_normalized)
    monkeypatch.setattr(voice_module, "_probe_duration", _short_duration)
    monkeypatch.setattr(voice_module, "get_tts_prompt", _empty_tts_prompt)
    monkeypatch.setattr(
        voice_module,
        "create_speech_providers",
        lambda settings: SimpleNamespace(
            stt_for_language=lambda language: FakeSttProvider(),
            tts_for_language=lambda language: FailingTtsProvider(),
        ),
    )

    async def process_user_text(message, user_text):
        assert user_text == "распознанный текст"
        await message.answer("текстовый ответ")
        return "текстовый ответ"

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert message.answers == [
        "текстовый ответ",
        "Я подготовил ответ текстом, но сейчас не смог озвучить его голосом.",
    ]
    assert message.voice_answers == []
    assert not (tmp_path / "input.ogg").exists()
    assert not (tmp_path / "normalized.wav").exists()


async def _write_normalized(input_path, output_path):
    Path(output_path).write_bytes(b"normalized")


async def _short_duration(file_path):
    return 1.0


async def _empty_tts_prompt(language):
    return ""
