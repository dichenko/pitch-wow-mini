## Context

Production is currently running the bot in `BOT_MODE=polling`. In this mode `apps.bot.app.main` starts aiogram polling directly and does not start uvicorn, so no process listens on port 8000. Docker still runs a healthcheck against `http://localhost:8000/health`, which makes the bot container unhealthy even while polling is running.

Separately, user messages fail before LLM invocation. The deployed dependency set pins `langgraph==0.2.53`; its `create_react_agent` signature accepts `state_modifier` or `messages_modifier`, not `prompt`. The current code passes `prompt=system_prompt`, causing `TypeError` and the generic Telegram error response.

## Goals / Non-Goals

**Goals:**

- Restore normal user message processing in the pinned LangGraph runtime.
- Keep polling as the current production mode.
- Preserve webhook readiness for future deployments.
- Make Docker health status meaningful in both polling and webhook modes.

**Non-Goals:**

- Do not switch production to webhook as part of this change.
- Do not change provider settings, API keys, prompt content, or conversation memory semantics.
- Do not introduce a broad dependency upgrade unless the pinned runtime cannot support the needed behavior.

## Decisions

**1. Use `state_modifier=system_prompt` for LangGraph 0.2.53**

Rationale: The deployed runtime supports `state_modifier` and this is the narrowest compatibility fix. It preserves the existing assembled prompt string and avoids dependency churn.

Alternative considered: upgrade LangGraph and keep `prompt=system_prompt`. This would require validating a wider dependency set and risks changing runtime behavior beyond the incident fix.

**2. Keep HTTP server startup tied to `BOT_MODE=webhook`**

Rationale: Polling mode does not need an inbound HTTP server for Telegram updates. Webhook mode does need FastAPI/uvicorn for `/webhook` and `/health`.

Alternative considered: always run uvicorn in parallel with polling. This adds concurrency/lifecycle complexity only to satisfy healthcheck and is unnecessary for the current deployment.

**3. Make bot healthcheck mode-aware**

Rationale: Docker health should verify the thing the selected mode actually runs. In webhook mode, HTTP `/health` is correct. In polling mode, a lightweight process check or mode-aware Python check avoids false unhealthy status from a deliberately absent HTTP server.

Alternative considered: remove the bot healthcheck. That would stop false negatives but lose useful status for webhook deployments.

## Risks / Trade-offs

- [Risk] A process-only polling healthcheck can report healthy even if Telegram polling is wedged. -> Mitigation: keep logs as primary diagnosis for polling errors and add tests around message processing.
- [Risk] Future LangGraph upgrades may prefer `prompt` over `state_modifier`. -> Mitigation: keep a focused regression test that validates the chosen keyword against the pinned dependency set.
- [Risk] Healthcheck shell/Python quoting can be fragile in Compose YAML. -> Mitigation: keep the command short and validate it inside the built bot image.
