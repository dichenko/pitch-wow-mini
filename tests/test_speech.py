from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.bot.app.config import BotSettings
from apps.bot.app.speech.aisha_provider import AishaSpeechProvider
from apps.bot.app.speech.azure_provider import AzureSpeechProvider
from apps.bot.app.speech.base import SpeechProviderError, normalize_language
from apps.bot.app.speech.factory import create_speech_providers
from apps.bot.app.speech.language_detection import detect_language_from_text
from apps.bot.app.speech.openai_provider import OpenAISpeechProvider
from apps.bot.app.speech.temp_files import cleanup_temp_file, create_temp_audio_path, ensure_ogg
from apps.bot.app.speech.yandex_provider import YandexSpeechKitProvider


class FakeResponse:
    def __init__(self, status_code=200, *, json_data=None, content=b"audio", text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.content = content
        self.text = text

    def json(self):
        return self._json_data


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []
        self.gets = []

    async def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        self.gets.append({"url": url, **kwargs})
        return self.responses.pop(0)


def test_normalize_language_falls_back_to_ru():
    assert normalize_language(None) == "ru"
    assert normalize_language("de") == "ru"
    assert normalize_language("uz") == "uz"


def test_factory_routes_stt_and_tts_by_language():
    settings = BotSettings()
    providers = create_speech_providers(settings)

    assert providers.stt_for_language("uz") is providers.aisha
    assert providers.stt_for_language("ru") is providers.openai
    assert providers.stt_for_language("en") is providers.openai
    assert providers.tts_for_language("uz") is providers.aisha
    assert providers.tts_for_language("ru") is providers.yandex
    assert providers.tts_for_language("en") is providers.openai


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Привет, сколько стоит консультация?", "ru"),
        ("Hello, how much does it cost?", "en"),
        ("Salom, maslahat qancha turadi?", "uz"),
        ("Ассалому алайкум, сизга раҳмат", "uz"),
        ("12345", None),
    ],
)
def test_detect_language_from_text(text, expected):
    assert detect_language_from_text(text) == expected


@pytest.mark.asyncio
async def test_openai_stt_omits_language_for_auto_detection(tmp_path):
    audio_path = tmp_path / "audio.wav"
    audio_path.write_bytes(b"audio")
    client = FakeHttpClient([FakeResponse(json_data={"text": "Hello"})])
    settings = BotSettings(openai_api_key="secret", openai_stt_language="ru")
    provider = OpenAISpeechProvider(settings=settings, client=client)

    result = await provider.transcribe(str(audio_path), None)

    assert result.text == "Hello"
    assert "language" not in client.posts[0]["data"]


@pytest.mark.asyncio
async def test_openai_tts_rejects_too_long_text_before_api_call():
    client = FakeHttpClient([])
    settings = BotSettings(openai_api_key="secret", openai_tts_max_chars=5)
    provider = OpenAISpeechProvider(settings=settings, client=client)

    with pytest.raises(SpeechProviderError):
        await provider.synthesize("too long text", "en")

    assert client.posts == []


@pytest.mark.asyncio
async def test_aisha_tts_sends_payload_and_downloads_audio(monkeypatch, tmp_path):
    output_path = tmp_path / "aisha.wav"
    monkeypatch.setattr(
        "apps.bot.app.speech.aisha_provider.create_temp_audio_path",
        lambda suffix: output_path,
    )
    client = FakeHttpClient(
        [
            FakeResponse(json_data={"audio_path": "media/audio.wav"}),
            FakeResponse(content=b"wav-bytes"),
        ]
    )
    settings = BotSettings(
        aisha_api_key="secret",
        aisha_base_url="https://back.aisha.group",
    )
    provider = AishaSpeechProvider(settings=settings, client=client)

    result = await provider.synthesize("Hello **markdown** https://example.com", "uz")

    post = client.posts[0]
    assert post["url"] == "https://back.aisha.group/api/v1/tts/post/"
    assert post["headers"]["X-Api-Key"] == "secret"
    assert post["headers"]["Accept-Language"] == "uz"
    assert post["files"]["transcript"] == (None, "Hello markdown")
    assert post["files"]["language"] == (None, "uz")
    assert post["files"]["model"] == (None, "Gulnoza")
    assert client.gets[0]["url"] == "https://back.aisha.group/media/audio.wav"
    assert output_path.read_bytes() == b"wav-bytes"
    assert result.provider == "aisha"
    assert result.format == "wav"


@pytest.mark.asyncio
async def test_yandex_tts_sends_expected_params(monkeypatch, tmp_path):
    output_path = tmp_path / "yandex.ogg"
    monkeypatch.setattr(
        "apps.bot.app.speech.yandex_provider.create_temp_audio_path",
        lambda suffix: output_path,
    )
    client = FakeHttpClient([FakeResponse(content=b"ogg-bytes")])
    settings = BotSettings(yandex_speechkit_api_key="secret")
    provider = YandexSpeechKitProvider(settings=settings, client=client)

    result = await provider.synthesize("Цена 10₽ и скидка 5%", "ru")

    post = client.posts[0]
    assert post["url"] == "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    assert post["headers"]["Authorization"] == "Api-Key secret"
    assert post["data"]["voice"] == "alena"
    assert post["data"]["emotion"] == "good"
    assert post["data"]["speed"] == "1.15"
    assert post["data"]["format"] == "oggopus"
    assert "рублей" in post["data"]["text"]
    assert "процентов" in post["data"]["text"]
    assert output_path.read_bytes() == b"ogg-bytes"
    assert result.provider == "yandex"
    assert result.format == "opus"


def test_azure_ssml_escapes_user_text():
    settings = BotSettings()
    provider = AzureSpeechProvider(settings=settings)

    ssml = provider.build_ssml("5 < 7 & safe")

    assert "5 &lt; 7 &amp; safe" in ssml
    assert "<voice name=\"ru-RU-SvetlanaNeural\">" in ssml


@pytest.mark.asyncio
async def test_temp_file_created_and_cleaned_up(tmp_path):
    path = create_temp_audio_path(suffix=".mp3", temp_dir=tmp_path)
    path.write_bytes(b"audio")

    assert path.parent == tmp_path
    assert path.exists()

    await cleanup_temp_file(path, reason="test")
    assert not path.exists()


@pytest.mark.asyncio
async def test_ensure_ogg_converts_wav(monkeypatch, tmp_path):
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"wav")

    class Process:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def fake_create_subprocess_exec(*args, **kwargs):
        Path(args[-1]).write_bytes(b"ogg")
        return Process()

    monkeypatch.setattr(
        "apps.bot.app.speech.temp_files.asyncio.create_subprocess_exec",
        fake_create_subprocess_exec,
    )

    output_path = await ensure_ogg(input_path)

    assert output_path == Path(str(input_path) + ".ogg")
    assert output_path.read_bytes() == b"ogg"
