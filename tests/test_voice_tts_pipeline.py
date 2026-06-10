from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.bot.app.handlers import message as message_module
from apps.bot.app.handlers import voice as voice_module
from apps.bot.app.services.language_service import LANGUAGE_SELECTION_TEXT
from apps.bot.app.speech.base import SpeechProviderError, SpeechToTextResult, TextToSpeechResult


class FakeUser:
    id = 100
    first_name = "Test"
    last_name = None
    username = "tester"
    language_code = "en"


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

    async def answer(self, text, **kwargs):
        self.answers.append(text)

    async def answer_voice(self, audio):
        self.voice_answers.append(audio)


class FakeSttProvider:
    def __init__(self, text="transcript", result_language="ru"):
        self.text = text
        self.result_language = result_language
        self.calls = []

    async def transcribe(self, file_path, language):
        self.calls.append(language)
        return SpeechToTextResult(
            text=self.text,
            provider="mock",
            model="mock-stt",
            language=self.result_language,
        )


class FailingTtsProvider:
    async def synthesize(self, text, language, instructions=None):
        raise SpeechProviderError("tts unavailable")


class RecordingTtsProvider:
    def __init__(self, output_path):
        self.output_path = output_path
        self.calls = []

    async def synthesize(self, text, language, instructions=None):
        self.calls.append(
            {"text": text, "language": language, "instructions": instructions}
        )
        Path(self.output_path).write_bytes(b"voice")
        return TextToSpeechResult(
            file_path=str(self.output_path),
            mime_type="audio/ogg",
            format="opus",
            provider="mock",
            model="mock-tts",
        )


@pytest.mark.asyncio
async def test_voice_pipeline_sends_text_before_tts_fallback(monkeypatch, tmp_path):
    stt_provider = FakeSttProvider("распознанный текст", result_language="ru")

    _patch_voice_basics(monkeypatch, tmp_path, language="ru")
    monkeypatch.setattr(
        voice_module,
        "create_speech_providers",
        lambda settings: SimpleNamespace(
            stt_for_language=lambda language: stt_provider,
            tts_for_language=lambda language: FailingTtsProvider(),
        ),
    )

    async def process_user_text(message, user_text, response_language=None):
        assert user_text == "распознанный текст"
        assert response_language == "ru"
        await message.answer("текстовый ответ")
        return "текстовый ответ"

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert message.answers == [
        "текстовый ответ",
        "Я подготовил ответ текстом, но сейчас не смог озвучить его голосом.",
    ]
    assert stt_provider.calls == ["ru"]
    assert message.voice_answers == []
    assert not (tmp_path / "input.ogg").exists()
    assert not (tmp_path / "normalized.wav").exists()


@pytest.mark.parametrize(
    ("profile_language", "transcript"),
    [
        ("ru", "Salom, maslahat qancha turadi?"),
        ("uz", "Спасибо, сколько стоит консультация?"),
        ("en", "Привет, how much does it cost?"),
    ],
)
@pytest.mark.asyncio
async def test_voice_pipeline_routes_by_profile_language_only(
    monkeypatch,
    tmp_path,
    profile_language,
    transcript,
):
    openai_stt = FakeSttProvider(transcript, result_language="ru")
    aisha_stt = FakeSttProvider(transcript, result_language="uz")
    tts_provider = RecordingTtsProvider(tmp_path / "tts.ogg")
    stt_routes = []
    tts_routes = []

    _patch_voice_basics(monkeypatch, tmp_path, language=profile_language)
    monkeypatch.setattr(voice_module, "ensure_ogg", _identity_ogg)
    monkeypatch.setattr(
        voice_module,
        "create_speech_providers",
        lambda settings: SimpleNamespace(
            stt_for_language=lambda language: _route_stt(
                stt_routes,
                language,
                openai_stt,
                aisha_stt,
            ),
            tts_for_language=lambda language: _record_route(
                tts_routes,
                language,
                tts_provider,
            ),
        ),
    )

    async def process_user_text(message, user_text, response_language=None):
        assert user_text == transcript
        assert response_language == profile_language
        await message.answer("text response")
        return "text response"

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert stt_routes == [profile_language]
    assert tts_routes == [profile_language]
    assert tts_provider.calls[0]["language"] == profile_language
    if profile_language == "uz":
        assert aisha_stt.calls == ["uz"]
        assert openai_stt.calls == []
    else:
        assert openai_stt.calls == [profile_language]
        assert aisha_stt.calls == []
    assert message.answers == ["text response"]
    assert len(message.voice_answers) == 1


@pytest.mark.asyncio
async def test_voice_pipeline_asks_language_before_download(monkeypatch, tmp_path):
    _patch_voice_basics(monkeypatch, tmp_path, language=None)
    message = FakeMessage()

    await voice_module.handle_voice(message)

    assert message.answers == [LANGUAGE_SELECTION_TEXT]
    assert message.voice_answers == []
    assert not (tmp_path / "input.ogg").exists()


def _patch_voice_basics(monkeypatch, tmp_path, language):
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    monkeypatch.setattr(
        voice_module,
        "settings",
        SimpleNamespace(
            voice_enabled=True,
            voice_max_audio_size_mb=25,
            voice_max_duration_sec=120,
        ),
    )
    monkeypatch.setattr(voice_module, "create_temp_audio_path", lambda suffix: next(paths))
    monkeypatch.setattr(voice_module, "_normalize_for_stt", _write_normalized)
    monkeypatch.setattr(voice_module, "_probe_duration", _short_duration)
    monkeypatch.setattr(voice_module, "get_tts_prompt", _empty_tts_prompt)

    async def require_preferred_language(message):
        if language is None:
            await message.answer(LANGUAGE_SELECTION_TEXT)
            return None
        return language

    monkeypatch.setattr(
        voice_module,
        "require_preferred_language",
        require_preferred_language,
    )


async def _write_normalized(input_path, output_path):
    Path(output_path).write_bytes(b"normalized")


async def _short_duration(file_path):
    return 1.0


async def _empty_tts_prompt(language):
    return ""


async def _identity_ogg(file_path):
    return file_path


def _route_stt(routes, language, openai_stt, aisha_stt):
    routes.append(language)
    return aisha_stt if language == "uz" else openai_stt


def _record_route(routes, language, provider):
    routes.append(language)
    return provider
