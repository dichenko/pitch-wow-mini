## Why

Users currently receive no immediate feedback while the bot is processing their message through language checks, prompt assembly, the LangChain agent, censoring, and response delivery. Sending Telegram's "typing" chat action immediately after each user message makes the bot visibly responsive during potentially slow processing.

## What Changes

- Send a Telegram `typing` chat action after the bot receives a processable user message.
- Cover both regular text messages and voice/audio messages that enter the bot's processing flow.
- Treat typing activity as best-effort: failures to send chat action must not block message processing or user-facing replies.
- Add tests that verify typing activity is sent before long-running processing begins.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `assistant-template`: The Telegram request pipeline shall emit typing activity after receiving user input and before running long-running processing.

## Impact

- Affected code: bot message and voice handlers, shared processing entry points, and related tests.
- Affected APIs: Telegram Bot API chat action via aiogram.
- Dependencies: no new runtime dependency expected; aiogram already provides chat action support.
- Systems: bot service behavior in polling and webhook modes.

## Non-goals

- Continuous or repeated typing indicators during very long requests.
- Typing indicators for admin panel actions or background jobs.
- Changes to final message content, language selection, censoring, STT, TTS, or LangChain agent behavior.
