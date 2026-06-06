## 1. Agent Runtime Compatibility

- [x] 1.1 Update `apps/bot/app/agent/agent.py` to pass the assembled system prompt via a LangGraph 0.2.53-compatible keyword.
- [x] 1.2 Add a focused unit test that patches `create_react_agent` and asserts no unsupported `prompt` keyword is passed.
- [x] 1.3 Add or update coverage confirming the assembled system prompt is still provided to the agent factory.

## 2. Mode-Aware Bot Health

- [x] 2.1 Update the bot Docker healthcheck so `BOT_MODE=polling` does not require `localhost:8000/health`.
- [x] 2.2 Preserve HTTP `/health` healthcheck behavior for `BOT_MODE=webhook`.
- [x] 2.3 Validate the polling healthcheck command inside the bot image or with an equivalent local command.

## 3. Verification

- [x] 3.1 Run the Python test suite.
- [x] 3.2 Run `openspec validate fix-bot-agent-runtime --strict`.
- [x] 3.3 Verify on deployment that user messages no longer fail with `create_react_agent() got an unexpected keyword argument 'prompt'`.
- [x] 3.4 Verify the bot container health is not falsely unhealthy in `BOT_MODE=polling`.
