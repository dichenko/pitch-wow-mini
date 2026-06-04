## Context

The bot uses `create_react_agent` from LangGraph which creates a new agent on every message. Each invocation passes `"thread_id": trace_id` where `trace_id` is a random UUID4 — meaning every message starts with zero context. The agent has no checkpointer, so no conversation state is persisted between messages.

The `/start` command currently only sends a welcome message. There is no `/restart` command. Both should clear the user's conversation history so the next message starts fresh.

## Goals / Non-Goals

**Goals:**
- Add `MemorySaver` checkpointer to the LangGraph agent for in-memory conversation state
- Use `user_tg_id` as `thread_id` for multi-turn conversation continuity
- Add `/restart` command that clears the checkpointer state for that user
- Update `/start` to clear history before greeting
- Trace ID remains separate for logging/tracing purposes

**Non-Goals:**
- Do NOT persist checkpoints to database (MemorySaver is in-memory; restarting bot clears all history)
- Do NOT add conversation history UI in admin panel
- Do NOT limit conversation length or add token window management
- Do NOT change LangSmith tracing behavior

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Use `MemorySaver` from `langgraph.checkpoint.memory` | Zero dependencies, no DB migration, works out of the box. Conversations are ephemeral (lost on bot restart) — acceptable for template. |
| 2 | Single shared `MemorySaver` instance per bot process | All users share one checkpointer. Thread isolation is by `thread_id`. MemorySaver is thread-safe. |
| 3 | `thread_id = str(user.tg_id)` | Stable per-user ID. Ensures same user always gets same thread across messages. |
| 4 | `/restart` deletes checkpoint by calling `checkpointer.delete_thread(thread_id)` | LangGraph MemorySaver does not expose a public `delete_thread` directly, but `aget_tuple` + removing from internal storage clears state. Alternatively clear by setting `thread_id` to a new UUID for that user session and force-recreating the config. |
| 5 | `/start` also clears history before greeting | Unified behavior: both commands reset conversation. |
| 6 | Keep `trace_id` as UUID4, separate from `thread_id` | Trace ID is for logging/tracing per-request. Thread ID is for conversation persistence across requests. |
| 7 | `restart.py` as separate handler file | Follows existing pattern: `start.py`, `admin.py`, `message.py`, `voice.py`. |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| MemorySaver grows unbounded with long conversations | MemorySaver keeps all state per thread. For template use, acceptable. Production deployments can replace with `SqliteSaver` or `PostgresSaver`. |
| All history lost on bot restart | Documented as expected behavior. Template is for rapid deployment; persistence can be added per-project. |
| Multiple bot instances (scaling) lose shared state | MemorySaver is per-process. Single-instance deployment is the template's target. |
