"""Admin service configuration."""

from packages.shared.utils.settings import AppSettings


class AdminSettings(AppSettings):
    """Settings specific to the admin web service."""

    # Public URLs
    bot_public_url: str = "https://bot.example.com"
    admin_public_url: str = "https://admin.example.com"

    # Host ports
    bot_host_port: int = 18001
    admin_host_port: int = 18002

    # Admin access
    root_admin_tg_id: int = 0
    admin_login_token_ttl_minutes: int = 15

    # Session
    session_secret: str = "change_me_in_production"
    session_cookie_name: str = "assistant_admin_session"
    session_cookie_secure: bool = True
    session_cookie_samesite: str = "lax"

    # LLM (for debug page display and settings)
    text_llm_provider: str = "openai"
    openai_text_model: str = "gpt-4.1-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"

    # Telegram (for debug page display)
    bot_mode: str = "polling"
    admin_telegram_chat_id: str = ""

    # LangSmith (for debug page display)
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "ai-assistant-template"
    langsmith_workspace_id: str = ""


def get_settings() -> AdminSettings:
    return AdminSettings()  # type: ignore[call-arg]
