## 1. Database

- [x] 1.1 Add a SQLAlchemy `DialogueHistory` model with fields from the database spec.
- [x] 1.2 Add an Alembic migration creating `dialogue_history` and indexes for `(user_tg_id, thread_id, created_at)`.
- [x] 1.3 Verify migration upgrade/downgrade paths are valid.

## 2. Settings

- [x] 2.1 Add `get_llm_history_messages()` to `apps/bot/app/services/settings_service.py` with default `20` and runtime fallback for malformed DB values.
- [x] 2.2 Extend `save_llm_settings()` to persist `llm_history_messages`.
- [x] 2.3 Add `LLM_HISTORY_MESSAGES` input to `/admin/settings` page rendering and save handling.
- [x] 2.4 Validate submitted history count as a bounded non-negative integer and show an admin form error on invalid input.
- [x] 2.5 Include `llm_history_messages` in `settings.updated` audit metadata.

## 3. History Service

- [x] 3.1 Create a bot history service that loads latest dialogue records by `user_tg_id`, `thread_id`, and configured limit.
- [x] 3.2 Convert loaded records to provider-neutral LangChain chat messages (`HumanMessage` / `AIMessage`) in chronological order.
- [x] 3.3 Add a function to persist one completed dialogue record after final user-visible response is available.
- [x] 3.4 Ensure failed agent/censor processing does not persist incomplete dialogue records.

## 4. LLM Request Integration

- [x] 4.1 Update `process_user_text()` to load history before invoking the main agent.
- [x] 4.2 Update the main agent invocation so current request messages are `history + current user message`.
- [x] 4.3 Adjust or verify LangGraph checkpointer behavior so explicit DB history is not duplicated by process-local memory.
- [x] 4.4 Update `apply_censor()` signature and call path so the censor/reviewer LLM receives the same recent history plus current user message and draft response.
- [x] 4.5 Persist the final response after censor has returned, using the same trace ID, provider/model metadata, user ID, and thread ID.
- [x] 4.6 Confirm `/start` and `/restart` continue to exclude previous-thread history through the existing thread reset mechanism.

## 5. Provider Coverage

- [x] 5.1 Add/adjust tests proving OpenAI requests receive history through the common message-building path.
- [x] 5.2 Add/adjust tests proving Anthropic requests receive history through the common message-building path.
- [x] 5.3 Add/adjust tests proving Mistral requests receive history through the common message-building path.
- [x] 5.4 Add/adjust tests proving the censor LLM request receives recent history when censor is enabled.

## 6. Regression Tests

- [x] 6.1 Add admin settings tests for rendering, saving, validation errors, default value, and audit metadata for `LLM_HISTORY_MESSAGES`.
- [x] 6.2 Add history service tests for ordering, limit behavior, zero-history behavior, and thread isolation.
- [x] 6.3 Add message handler tests proving final responses are persisted once and failed responses are not persisted.
- [x] 6.4 Run the full test suite and fix regressions.
