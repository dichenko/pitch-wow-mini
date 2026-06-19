"""Bot service configuration."""

from packages.shared.utils.settings import AppSettings


class BotSettings(AppSettings):
    """Settings specific to the bot service."""

    # Public URLs
    bot_public_url: str = "https://bot.example.com"
    admin_public_url: str = "https://admin.example.com"

    # Host ports
    bot_host_port: int = 18001
    admin_host_port: int = 18002

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    bot_mode: str = "polling"  # polling | webhook

    # Admin access
    root_admin_tg_id: int = 0
    admin_login_token_ttl_minutes: int = 15

    # Admin notifications
    admin_telegram_chat_id: str = ""

    # Artifact Generator
    artifact_worker_poll_interval_sec: int = 5
    artifact_generator_temperature: float = 0.3
    artifact_generator_max_retries: int = 3

    # LLM
    text_llm_provider: str = "openai"
    llm_history_messages: int = 20
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_text_model: str = "gpt-4.1-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Mistral
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"

    # LangSmith
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "ai-assistant-template"
    langsmith_workspace_id: str = ""
    langsmith_tags: str = "telegram,production"
    langsmith_sample_rate: float = 1.0

    # Session
    session_secret: str = ""
    session_cookie_name: str = "assistant_admin_session"
    session_cookie_secure: bool = True
    session_cookie_samesite: str = "lax"

    # Censor
    censor_enabled: bool = False

    # Voice recognition
    voice_enabled: bool = False
    voice_temp_dir: str = "/tmp/assistant-audio"
    speech_temp_dir: str = "/tmp/assistant-audio"
    voice_max_audio_size_mb: int = 25
    voice_max_duration_sec: int = 120

    # OpenAI STT
    openai_stt_model: str = "gpt-4o-transcribe"
    openai_stt_language: str = ""
    openai_stt_timeout_ms: int = 60000

    # OpenAI TTS
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "marin"
    openai_tts_fallback_voice: str = "cedar"
    openai_tts_response_format: str = "opus"
    openai_tts_timeout_ms: int = 60000
    openai_tts_max_chars: int = 4096
    openai_tts_speed: float = 1.0
    openai_tts_instructions: str = ""

    # Aisha STT
    aisha_api_key: str = ""
    aisha_base_url: str = ""
    aisha_stt_timeout_ms: int = 60000
    aisha_stt_language: str = "uz"

    # Aisha TTS
    aisha_tts_timeout_ms: int = 60000
    aisha_tts_max_chars: int = 1000
    aisha_tts_language: str = "uz"
    aisha_tts_model: str = "Gulnoza"
    aisha_tts_mood: str = "Neutral"
    aisha_tts_speed: float = 1.0

    # Yandex SpeechKit TTS
    yandex_speechkit_api_key: str = ""
    yandex_tts_base_url: str = "https://tts.api.cloud.yandex.net"
    yandex_tts_model: str = "yandex-speechkit-tts-v1"
    yandex_tts_language: str = "ru-RU"
    yandex_tts_voice: str = "alena"
    yandex_tts_emotion: str = "good"
    yandex_tts_speed: float = 1.15
    yandex_tts_format: str = "oggopus"
    yandex_tts_timeout_ms: int = 60000
    yandex_tts_max_chars: int = 5000

    # Azure Speech TTS
    azure_speech_key: str = ""
    azure_speech_region: str = "westeurope"
    azure_speech_endpoint: str = ""
    azure_tts_language: str = "ru-RU"
    azure_tts_voice: str = "ru-RU-SvetlanaNeural"
    azure_tts_output_format: str = "ogg-24khz-16bit-mono-opus"
    azure_tts_rate: str = "20%"
    azure_tts_pitch: str = ""
    azure_tts_range: str = ""
    azure_tts_timeout_ms: int = 60000
    azure_tts_max_chars: int = 5000


def get_settings() -> BotSettings:
    return BotSettings()  # type: ignore[call-arg]
