from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.bot.app.handlers import message as message_module
from apps.bot.app.handlers import voice as voice_module
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

    async def answer(self, text):
        self.answers.append(text)

    async def answer_voice(self, audio):
        self.voice_answers.append(audio)


class FakeSttProvider:
    def __init__(self, text="распознанный текст"):
        self.text = text
        self.calls = []

    async def transcribe(self, file_path, language):
        self.calls.append(language)
        return SpeechToTextResult(
            text=self.text,
            provider="mock",
            model="mock-stt",
            language="ru",
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
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    stt_provider = FakeSttProvider("распознанный текст")
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
            openai=stt_provider,
            aisha=FakeSttProvider("salom"),
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
    assert stt_provider.calls == [None]
    assert message.voice_answers == []
    assert not (tmp_path / "input.ogg").exists()
    assert not (tmp_path / "normalized.wav").exists()


@pytest.mark.parametrize(
    ("transcript", "expected_language"),
    [
        ("Привет, сколько стоит консультация?", "ru"),
        ("Hello, how much does it cost?", "en"),
        ("Salom, maslahat qancha turadi?", "uz"),
    ],
)
@pytest.mark.asyncio
async def test_voice_pipeline_routes_tts_by_detected_transcript_language(
    monkeypatch,
    tmp_path,
    transcript,
    expected_language,
):
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    stt_provider = FakeSttProvider(transcript)
    tts_provider = RecordingTtsProvider(tmp_path / "tts.ogg")
    routed_languages = []

    monkeypatch.setattr(voice_module, "settings", SimpleNamespace(
        voice_enabled=True,
        voice_max_audio_size_mb=25,
        voice_max_duration_sec=120,
    ))
    monkeypatch.setattr(voice_module, "create_temp_audio_path", lambda suffix: next(paths))
    monkeypatch.setattr(voice_module, "_normalize_for_stt", _write_normalized)
    monkeypatch.setattr(voice_module, "_probe_duration", _short_duration)
    monkeypatch.setattr(voice_module, "get_tts_prompt", _empty_tts_prompt)
    monkeypatch.setattr(voice_module, "ensure_ogg", _identity_ogg)
    monkeypatch.setattr(
        voice_module,
        "create_speech_providers",
        lambda settings: SimpleNamespace(
            openai=stt_provider,
            aisha=FakeSttProvider("salom"),
            tts_for_language=lambda language: _record_route(
                routed_languages,
                language,
                tts_provider,
            ),
        ),
    )

    async def process_user_text(message, user_text, response_language=None):
        assert user_text == transcript
        assert response_language == expected_language
        await message.answer("text response")
        return "text response"

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert routed_languages == [expected_language]
    assert tts_provider.calls[0]["language"] == expected_language
    assert message.answers == ["text response"]
    assert len(message.voice_answers) == 1


@pytest.mark.asyncio
async def test_voice_pipeline_skips_tts_when_transcript_language_uncertain(
    monkeypatch,
    tmp_path,
):
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    stt_provider = FakeSttProvider("12345")
    routed_languages = []

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
            openai=stt_provider,
            aisha=FakeSttProvider("salom"),
            tts_for_language=lambda language: routed_languages.append(language),
        ),
    )

    async def process_user_text(message, user_text, response_language=None):
        assert response_language is None
        await message.answer("text response")
        return "text response"

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert routed_languages == []
    assert message.answers == ["text response"]
    assert message.voice_answers == []


@pytest.mark.asyncio
async def test_voice_pipeline_skips_tts_when_response_language_differs(
    monkeypatch,
    tmp_path,
):
    paths = iter([tmp_path / "input.ogg", tmp_path / "normalized.wav"])
    stt_provider = FakeSttProvider("Salom, maslahat qancha turadi?")
    routed_languages = []

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
            openai=stt_provider,
            aisha=FakeSttProvider("salom"),
            tts_for_language=lambda language: routed_languages.append(language),
        ),
    )

    async def process_user_text(message, user_text, response_language=None):
        assert response_language == "uz"
        await message.answer("Спасибо, я отвечу по-русски.")
        return "Спасибо, я отвечу по-русски."

    monkeypatch.setattr(message_module, "process_user_text", process_user_text)

    message = FakeMessage()
    await voice_module.handle_voice(message)

    assert routed_languages == []
    assert message.answers == [
        "Спасибо, я отвечу по-русски.",
        "Javobni matn shaklida tayyorladim, lekin hozir uni ovoz bilan yubora olmadim.",
    ]
    assert message.voice_answers == []


async def _write_normalized(input_path, output_path):
    Path(output_path).write_bytes(b"normalized")


async def _short_duration(file_path):
    return 1.0


async def _empty_tts_prompt(language):
    return ""


async def _identity_ogg(file_path):
    return file_path


def _record_route(routed_languages, language, provider):
    routed_languages.append(language)
    return provider
