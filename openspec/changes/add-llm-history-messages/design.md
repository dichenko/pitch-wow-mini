## Context

The bot currently builds the main user-facing LLM call in `apps/bot/app/handlers/message.py` by invoking a LangGraph ReAct agent with only the current user text. LangGraph `MemorySaver` preserves state while the bot process is alive, but that state is not database-backed and is lost on restart. The censor/reviewer LLM call in `apps/bot/app/services/censor_service.py` is separate and receives only the current user message plus draft response.

LLM provider selection is centralized through `apps/bot/app/services/llm_factory.py`, which returns LangChain chat models for OpenAI, Anthropic, and Mistral. Admin settings are stored in `app_settings` via `settings_service.py` and edited through `/admin/settings`.

There is no current database table that stores completed user/assistant dialogue pairs.

## Goals / Non-Goals

**Goals:**

- Persist each completed main dialogue turn as one record: user question plus final assistant response.
- Add `LLM_HISTORY_MESSAGES` as an admin-editable setting with default `20`.
- Load the latest N records for the current Telegram user and current conversation thread before each LLM request related to that user message.
- Inject the loaded history as provider-neutral LangChain chat messages so OpenAI, Anthropic, and Mistral use the same context path.
- Apply the same history service to the main agent request and the censor/reviewer request when censor is enabled.
- Preserve `/start` and `/restart` reset semantics by scoping history records to the current thread ID.

**Non-Goals:**

- Summarizing older history.
- Vector search or semantic retrieval.
- Per-user history configuration.
- Replacing LangGraph checkpointer behavior beyond avoiding duplicate long-lived memory where needed.

## Decisions

**1. Store dialogue turns in a new table**

Use a `dialogue_history` table with fields for `id`, `thread_id`, `user_tg_id`, `trace_id`, `user_message`, `assistant_response`, optional provider/model metadata, and `created_at`.

Alternative considered: reuse `censor_runs` or logs. Rejected because those tables do not always represent the final user-visible answer and do not store uncensored/non-censor flows consistently.

**2. Count one row as one history item**

`LLM_HISTORY_MESSAGES=20` means up to 20 completed rows, each expanded into two messages: one `HumanMessage` and one `AIMessage`.

Alternative considered: count individual chat messages. Rejected because the user explicitly defines one record as question plus LLM answer.

**3. Build history before the agent invocation**

`process_user_text()` should load history records using the current `thread_id`, pass them into the main agent invocation, pass the same history into the censor/reviewer call when enabled, and persist the new record after the final response is sent or ready to send.

Alternative considered: let LangGraph `MemorySaver` remain the only context source. Rejected because it is process-local and not admin-windowed.

**4. Keep provider handling centralized**

History injection should happen before provider-specific models are called by LangChain. The input should be a list of LangChain-compatible messages, so OpenAI (`ChatOpenAI`), Anthropic (`ChatAnthropic`), and Mistral (`ChatMistralAI`) all receive the same message sequence.

Alternative considered: implement provider-specific history formatting in `llm_factory.py`. Rejected because LangChain already normalizes chat messages and provider-specific branches would duplicate logic.

**5. Scope persisted history by thread ID**

History retrieval should filter by both `user_tg_id` and `thread_id`. Existing `/start` and `/restart` increment the user's thread ID, so old rows remain stored but are excluded from new requests.

Alternative considered: physically delete old rows on reset. Rejected because retaining rows is useful for audit/debugging and avoids destructive behavior.

**6. Validate setting as a bounded non-negative integer**

The service should expose `get_llm_history_messages()` returning an integer default of `20`. Admin save should reject invalid values. Runtime fallback should guard against malformed DB data.

Alternative considered: store only in `.env`. Rejected because the request requires admin settings.

## Risks / Trade-offs

- [Risk] Large history windows can exceed model context limits. -> Mitigation: default to 20 and validate to a reasonable upper bound during implementation.
- [Risk] LangGraph memory plus explicit DB history may duplicate context. -> Mitigation: when explicit DB history is provided, invoke the agent with the intended message list and adjust/verify checkpointer behavior so prior process-local state does not duplicate the same turns.
- [Risk] Persisting user messages increases personal data retention. -> Mitigation: store only required dialogue fields, keep reset non-destructive, and leave retention policy as a future change.
- [Risk] Persisting after censor means history contains final user-visible responses, not raw draft responses. -> Mitigation: this matches the user-facing conversation and avoids teaching future turns from unapproved drafts.

## Migration Plan

1. Add an Alembic migration for `dialogue_history`.
2. Add SQLAlchemy model and indexes for efficient lookup by `(user_tg_id, thread_id, created_at)`.
3. Add settings service helpers and admin form field for `llm_history_messages`.
4. Add history service functions for loading, formatting, and saving dialogue turns.
5. Update message processing to load history, invoke the agent with history plus current user text, apply censor with the same history context, then persist final response.
6. Rollback removes the code path and migration if needed; existing `app_settings` rows are harmless if unused.

## Open Questions

- What upper bound should admin validation enforce for `LLM_HISTORY_MESSAGES`? Proposed implementation default: allow `0..100`, where `0` disables history injection.
