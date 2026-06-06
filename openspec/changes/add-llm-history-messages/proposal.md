## Why

The bot currently relies on in-process LangGraph memory for conversation continuity, so context is lost after process restarts and there is no admin-controlled limit for how much prior dialogue is sent to the LLM. We need deterministic, database-backed history injection so each LLM request can include the latest configured number of user/assistant exchanges.

## What Changes

- Add an admin setting `LLM_HISTORY_MESSAGES` stored as `llm_history_messages` in `app_settings`, defaulting to `20`.
- Add persistence for completed dialogue records, where one record is one user question plus the final LLM response sent to the user.
- Before each LLM request for a user message, load the latest configured number of dialogue records for the Telegram user and include them as chat history.
- Ensure the history injection is provider-neutral and works when the selected provider is OpenAI, Anthropic, or Mistral.
- Keep `/start` and `/restart` semantics: after reset, new requests must not include history from the previous conversation thread.
- Add validation so invalid admin values fall back or are rejected safely instead of breaking message processing.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `admin-settings`: add editable `LLM_HISTORY_MESSAGES` setting with default `20`.
- `langchain-tools`: require main agent LLM requests to include recent database-backed dialogue history across OpenAI, Anthropic, and Mistral.
- `database`: add storage for dialogue history records and indexes needed for efficient per-user retrieval.

## Non-goals

- No semantic summarization or vector retrieval of older messages.
- No per-user or per-provider history length configuration.
- No changes to STT provider behavior.
- No custom provider-specific history formatting.

## Impact

- Affected bot code: `apps/bot/app/handlers/message.py`, `apps/bot/app/agent/agent.py`, `apps/bot/app/services/censor_service.py`, and new/updated history service code.
- Affected settings code: `apps/bot/app/services/settings_service.py`, `apps/admin/app/routers/settings.py`, `apps/admin/app/templates/settings/settings.html`.
- Affected database code: shared SQLAlchemy models and Alembic migrations.
- Affected tests: settings save/rendering, history retrieval/windowing, provider-neutral agent invocation for OpenAI/Anthropic/Mistral.
