## 1. Agent Checkpointer

- [x] 1.1 Add `MemorySaver` from `langgraph.checkpoint.memory` to `agent.py`
- [x] 1.2 Create shared checkpointer instance (module-level, one per bot process)
- [x] 1.3 Pass `checkpointer=checkpointer` to `create_react_agent()`
- [x] 1.4 Return agent without hardcoding thread_id (caller provides it via config)

## 2. Message Handler

- [x] 2.1 Replace `"configurable": {"thread_id": trace_id}` with `"configurable": {"thread_id": str(user.id)}`
- [x] 2.2 Keep `trace_id` as UUID for logging/tracing (separate from thread_id)

## 3. /restart Command

- [x] 3.1 Create `apps/bot/app/handlers/restart.py`
- [x] 3.2 Handle `/restart` command — clear checkpointer state for user's thread_id
- [x] 3.3 Send confirmation message after clearing history
- [x] 3.4 Use `memory_storage` internal dict of MemorySaver to delete thread state (or use `checkpointer.put()` with empty checkpoint)

## 4. /start Command Update

- [x] 4.1 Update `apps/bot/app/handlers/start.py` to clear conversation history before greeting
- [x] 4.2 Send welcome message after clearing

## 5. Router Registration

- [x] 5.1 Import and register `restart.router` in `apps/bot/app/main.py`

## 6. Testing

- [x] 6.1 Test that same user gets same thread_id across messages
- [x] 6.2 Test `/restart` clears conversation history
- [x] 6.3 Test `/start` clears conversation history
- [x] 6.4 Test conversation context is preserved between messages (agent sees prior messages)
- [x] 6.5 Test different users have isolated conversation histories
