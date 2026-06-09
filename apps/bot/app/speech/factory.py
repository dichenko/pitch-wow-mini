"""Speech provider factory and language routing."""

from apps.bot.app.config import BotSettings, get_settings
from apps.bot.app.speech.aisha_provider import AishaSpeechProvider
from apps.bot.app.speech.azure_provider import AzureSpeechProvider
from apps.bot.app.speech.base import SpeechProviders
from apps.bot.app.speech.openai_provider import OpenAISpeechProvider
from apps.bot.app.speech.yandex_provider import YandexSpeechKitProvider


def create_speech_providers(settings: BotSettings | None = None) -> SpeechProviders:
    resolved_settings = settings or get_settings()
    return SpeechProviders(
        openai=OpenAISpeechProvider(resolved_settings),
        aisha=AishaSpeechProvider(resolved_settings),
        yandex=YandexSpeechKitProvider(resolved_settings),
        azure=AzureSpeechProvider(resolved_settings),
    )
