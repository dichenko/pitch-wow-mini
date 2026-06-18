# AI Assistant Template

A reusable template for rapid deployment of Telegram AI assistants powered by LangChain/LangGraph, with an admin panel for prompt management, observability via LangSmith, and optional censor/voice recognition.

## Tech Stack

- **Python 3.12** with async/await
- **aiogram 3** — Telegram bot framework
- **FastAPI** — bot health endpoint + admin web service
- **LangChain + LangGraph** — AI agent with tool calling
- **PostgreSQL 16** — async via SQLAlchemy 2 + asyncpg
- **Alembic** — database migrations
- **Jinja2 + HTMX** — admin panel UI
- **Docker Compose** — containerized deployment
- **Caddy** — host-level reverse proxy

## Project Structure

```text
├── apps/
│   ├── bot/              # Telegram bot service
│   └── admin/            # Admin web panel
├── packages/
│   └── shared/           # Shared models, schemas, utilities
├── infra/
│   ├── docker-compose.yml
│   └── Caddyfile.example
├── migrations/           # Alembic migrations
├── scripts/              # Init and utility scripts
├── tests/                # Test suite
└── .env.example          # Environment template
```

## Quick Start

### 1. Initialize Project

```bash
python scripts/init_project_env.py
```

This copies `.env.example` to `.env`, generates a unique `PROJECT_SLUG`, random ports, and `SESSION_SECRET`.

### 2. Configure Environment

Edit `.env` and fill in required values:

- `TELEGRAM_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `OPENAI_API_KEY` — your OpenAI API key
- `ROOT_ADMIN_TG_ID` — your Telegram user ID (get it from [@userinfobot](https://t.me/userinfobot))
- `POSTGRES_PASSWORD` — change from default

### 3. Run Migrations

```bash
cd infra
docker compose run --rm bot alembic -c migrations/alembic.ini upgrade head
```

### 4. Start Services

```bash
cd infra
docker compose up -d --build
```

### 5. Access Admin Panel

1. Send `/admin` to your Telegram bot
2. Click the one-time login link
3. You'll be redirected to the admin dashboard

## Local Development

```bash
# Install dependencies
pip install -r apps/bot/requirements.txt
pip install -r apps/admin/requirements.txt

# Run bot (polling mode)
python -m apps.bot.app.main

# Run admin panel
python -m apps.admin.app.main
```

## VPS Deployment

### 1. Install Caddy on the host

```bash
# Ubuntu/Debian
sudo apt install -y caddy
```

### 2. Configure Caddyfile

Use the snippet from `init_project_env.py` output or `infra/Caddyfile.example`:

```caddyfile
bot.yourproject.example.com {
    reverse_proxy 127.0.0.1:18001
}

admin.yourproject.example.com {
    reverse_proxy 127.0.0.1:18002
}
```

### 3. Start services

```bash
cd infra
docker compose up -d --build
```

Ports are bound to `127.0.0.1` only — external access goes through Caddy.

## Configuration

### Environment Variables

See `.env.example` for all available variables. Key groups:

| Group | Variables | Description |
|-------|-----------|-------------|
| App | `APP_ENV`, `PROJECT_SLUG` | Environment and project identity |
| Telegram | `TELEGRAM_BOT_TOKEN`, `BOT_MODE` | Bot token, polling/webhook mode |
| Admin | `ROOT_ADMIN_TG_ID`, `ADMIN_TELEGRAM_CHAT_ID` | Root admin and notification chat |
| LLM | `OPENAI_API_KEY`, `OPENAI_TEXT_MODEL` | Language model configuration |
| LangSmith | `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` | Optional observability |
| Session | `SESSION_SECRET`, `SESSION_COOKIE_*` | Admin session security |
| Censor | `CENSOR_ENABLED` | Optional response reviewer |
| Voice | `VOICE_ENABLED`, `OPENAI_STT_*`, `AISHA_*` | Voice recognition pipeline |

## How It Works

### Admin Access

1. Admin sends `/admin` in the Telegram bot
2. Bot generates a secure one-time token (`secrets.token_urlsafe(32)`)
3. Token hash (SHA-256) is stored in DB with expiration
4. Admin receives a login link: `https://admin.example.com/admin/login?token=<raw>`
5. Opening the link validates the token, creates a signed session cookie, redirects to dashboard

### Roles

| Role | Permissions |
|------|-------------|
| `read` | View prompts, view admins |
| `write` | + Edit prompts, restore versions |
| `superadmin` | + Manage admins, change roles |

Root admin (`ROOT_ADMIN_TG_ID`) always has `superadmin` privileges.

### Prompt Versioning

All prompts (system prompt, tools instruction, censor prompt) are versioned:
- Every save creates a new version (append-only)
- Old versions are preserved
- Restore creates a new version copied from the selected version
- Last 3 previous versions shown with restore buttons

### send_to_admin Tool

The only REQUIRED default tool. LLM provides only `comment`; the backend auto-attaches:
- `tg_id`, `first_name`, `last_name`, `username`, `telegram_link`, `language_code`
- `trace_id`, `timestamp`

Delivers to `ADMIN_TELEGRAM_CHAT_ID` if configured, always saves to DB.

### LangSmith Observability

Optional, controlled by `LANGSMITH_TRACING`:
- Full agent trace with metadata (trace_id, prompt versions, user info)
- Tags: `project:<slug>`, `env:<env>`, `channel:telegram`
- Secrets never sent to LangSmith
- Best-effort: failures logged locally, conversations continue

### Censor / Response Reviewer

Optional LLM post-pass that reviews agent responses before sending to users:
- Toggleable from admin panel
- Uses its own versioned prompt
- On failure: falls back to draft response (never blocks the user)

### Voice Recognition

Optional pipeline for voice/audio messages:
- OpenAI STT (primary) → Aisha STT (fallback, Uzbek)
- ffmpeg audio normalization
- Size/duration limits
- Temp files cleaned up after processing

## Adding a New Tool

1. Create `apps/bot/app/agent/tools/your_tool.py`:

```python
from langchain_core.tools import tool

@tool
async def your_tool(param: str) -> str:
    """Description for the LLM."""
    # Implementation
    return "Result"
```

2. Register in `apps/bot/app/agent/tools/__init__.py`:

```python
from apps.bot.app.agent.tools.your_tool import your_tool

def get_all_tools() -> list:
    return [
        send_to_admin,  # REQUIRED
        your_tool,      # Your new tool
    ]
```

## Running Tests

```bash
pytest tests/ -v
```

## License

This template is provided as-is for building AI assistant projects.
