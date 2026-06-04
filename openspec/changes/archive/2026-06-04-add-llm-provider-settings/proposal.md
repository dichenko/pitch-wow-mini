## Why

Currently the main agent and censor are hardcoded to OpenAI (`ChatOpenAI`). Teams using Anthropic Claude or needing different providers per agent cannot switch without modifying source code. Adding provider selection in the admin panel makes the template truly multi-LLM without code changes.

## What Changes

- Add Anthropic Claude support via `langchain-anthropic` as an alternative LLM provider
- Make LLM provider configurable separately for main agent and censor agent
- Add a new Settings page (`/admin/settings`) in the admin panel for provider and model selection
- Store provider selections in `app_settings` table
- Both agents read provider configuration from DB at runtime, falling back to `.env` defaults

## Capabilities

### New Capabilities

- `admin-settings`: Admin panel page for global system settings. Allows selecting LLM provider (OpenAI / Anthropic) and model name for the main agent and the censor/reviewer independently.

### Modified Capabilities

- `admin-panel`: Navigation SHALL include a new "Settings" section. Section list extended from 6 to 7 items.
- `langchain-tools`: Main agent SHALL support multiple LLM providers. Provider and model SHALL be read from `app_settings` at runtime, falling back to `.env` defaults. OpenAIShall remain the default for existing deployments.
- `prompt-versioning`: Censor LLM SHALL use its own configurable provider (separate from main agent), read from `app_settings`, falling back to `.env`.

## Impact

- `apps/bot/app/agent/agent.py` — LLM instantiation from settings instead of hardcoded `ChatOpenAI`
- `apps/bot/app/services/censor_service.py` — LLM instantiation from settings
- `apps/bot/app/config.py` — add Anthropic env vars (`ANTHROPIC_API_KEY`, etc.)
- `apps/admin/app/routers/` — new `settings.py` router
- `apps/admin/app/templates/` — new settings page template
- `apps/admin/app/main.py` — register new router
- `packages/shared/models/database.py` — no schema changes needed (uses `app_settings`)
- `.env.example` — add Anthropic variables
- `requirements.txt` / `Dockerfile` — add `langchain-anthropic`
