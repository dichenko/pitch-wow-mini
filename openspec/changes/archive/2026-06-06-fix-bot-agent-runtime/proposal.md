## Why

The deployed bot answers every user message with the generic error because `create_react_agent()` is called with `prompt=...`, but the pinned `langgraph==0.2.53` runtime expects `state_modifier`/`messages_modifier` instead. The bot container also reports `unhealthy` in `BOT_MODE=polling` because the HTTP health endpoint is only served when FastAPI/uvicorn runs.

## What Changes

- Update agent creation to pass the assembled system prompt using the LangGraph API supported by the pinned dependency set.
- Add regression coverage that fails if the agent factory passes an unsupported keyword to `create_react_agent`.
- Make bot service health behavior mode-aware:
  - `BOT_MODE=polling`: bot SHALL process Telegram polling without requiring an HTTP server on port 8000.
  - `BOT_MODE=webhook`: bot SHALL run the FastAPI HTTP server and expose `/health`.
- Update Docker healthcheck so polling deployments do not become unhealthy solely because no HTTP server is listening.

## Non-goals

- No change to Telegram bot token, API keys, provider selection, or prompt content.
- No migration from polling to webhook now; polling remains the current production mode.
- No broad LangGraph dependency upgrade unless compatibility cannot be achieved with the pinned version.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `langchain-tools`: Agent creation SHALL use a LangGraph prompt/system-message parameter compatible with the pinned runtime.
- `docker-deployment`: Bot healthchecks SHALL reflect whether the bot is running in polling or webhook mode.

## Impact

- `apps/bot/app/agent/agent.py` - fix `create_react_agent` argument usage.
- `tests/` - add focused regression coverage for agent factory compatibility.
- `apps/bot/app/main.py` and/or `infra/docker-compose.yml` - make healthcheck behavior align with `BOT_MODE`.
- Deployment verification - confirm polling bot processes messages and container health no longer reports false unhealthy state.
