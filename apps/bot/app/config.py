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

    # LLM
    text_llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_text_model: str = "gpt-4.1-mini"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"

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
    voice_max_audio_size_mb: int = 25
    voice_max_duration_sec: int = 120

    # OpenAI STT
    openai_stt_model: str = "gpt-4o-transcribe"
    openai_stt_language: str = ""
    openai_stt_timeout_ms: int = 60000

    # Aisha STT
    aisha_api_key: str = ""
    aisha_base_url: str = ""
    aisha_stt_timeout_ms: int = 60000
    aisha_stt_language: str = "uz"


def get_settings() -> BotSettings:
    return BotSettings()  # type: ignore[call-arg]
