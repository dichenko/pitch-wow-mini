## Why

The bot currently processes each message in isolation — every user input gets a fresh random `thread_id`, so the LangGraph agent has no memory of previous exchanges. Users can't clear their conversation context because there's no persistent history to clear. Adding LangGraph checkpointing with per-user thread_id enables multi-turn conversations, and `/restart` lets users reset the dialogue.

## What Changes

- Add LangGraph `MemorySaver` checkpointer to the ReAct agent for conversation continuity
- Use user's `tg_id` as `thread_id` instead of random UUID per message
- Add `/restart` command that clears the checkpointer state for the user
- Update `/start` to also clear conversation history before greeting
- Message handler no longer generates random `trace_id` as `thread_id` (trace_id stays for logging)

## Capabilities

### Modified Capabilities

- `langchain-tools`: Agent SHALL use a LangGraph checkpointer with per-user `thread_id` for multi-turn conversation. `/start` and `/restart` commands SHALL clear the user's conversation history.

## Impact

- `apps/bot/app/agent/agent.py` — add `MemorySaver` checkpointer, accept `thread_id` in config
- `apps/bot/app/handlers/message.py` — use `user_tg_id` as `thread_id`, pass checkpointer config
- `apps/bot/app/handlers/start.py` — clear history before greeting
- `apps/bot/app/handlers/` — new `restart.py` handler with `/restart` command
- `apps/bot/app/main.py` — register restart handler, pass checkpointer to agent creation
