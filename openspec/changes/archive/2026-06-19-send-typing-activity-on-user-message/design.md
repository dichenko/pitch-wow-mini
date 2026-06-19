## Context

The bot currently handles text messages in `apps/bot/app/handlers/message.py` and voice/audio messages in `apps/bot/app/handlers/voice.py`. Text processing can take noticeable time because it loads settings and history, assembles prompts, invokes the LangChain agent, optionally censors the response, saves history, and sends the final reply. Voice/audio processing can take longer because it also downloads and normalizes media, runs STT, then calls the shared text processing path.

Telegram supports chat actions such as `typing` through aiogram's bot API. This change adds immediate best-effort typing feedback after receiving processable user input without changing the response pipeline.

## Goals / Non-Goals

**Goals:**

- Send a `typing` chat action for every text message that enters `process_user_text`.
- Send a `typing` chat action for voice/audio messages before STT and shared text processing begin.
- Keep chat action failures non-fatal and invisible to users.
- Cover the behavior with focused async handler tests.

**Non-Goals:**

- Repeating chat actions while a long request is still running.
- Adding new settings, database schema, dependencies, or admin controls.
- Changing language selection, STT, TTS, censoring, history, or LangChain behavior.

## Decisions

- Add a small helper in the bot handler layer for best-effort typing activity.
  - Rationale: both text and voice handlers can use the same behavior without introducing a new service abstraction for a single Telegram API call.
  - Alternative considered: call `message.bot.send_chat_action` inline in each handler. This is simpler locally but duplicates error handling and makes test expectations drift.

- Emit typing at processing entry points, not after the agent starts.
  - Rationale: the user requested "user wrote message -> bot sent typing"; sending before prompt assembly, STT, or agent invocation gives immediate feedback.
  - Alternative considered: send typing only around the LangChain call. That misses voice/STT time and some pre-agent latency.

- Make typing best-effort.
  - Rationale: a failed chat action must not prevent the assistant from responding. The existing pipeline favors resilient user-facing behavior for optional integrations.
  - Alternative considered: propagate chat action failures. That would turn a UI hint into a conversation-breaking failure.

## Risks / Trade-offs

- Chat action may expire before very long LLM/STT work finishes -> this change intentionally sends only one immediate activity; repeated keep-alive indicators remain out of scope.
- Some test doubles may not expose `message.bot` or `send_chat_action` -> helper should tolerate missing or failing bot APIs and tests should cover best-effort behavior.
- Text generated from voice may traverse `process_user_text` after voice handling already sent typing -> duplicate typing actions are acceptable because they are transient Telegram UI hints, but implementation can avoid duplication if that proves cleaner.

## Migration Plan

- Implement the helper and handler calls.
- Add tests for text and voice entry points.
- Deploy normally with the bot service; no database migration or configuration change is required.
- Rollback by reverting the handler/helper changes.

## Open Questions

None.
