## 1. Typing Activity Helper

- [x] 1.1 Add a reusable async helper in the bot handler layer that sends Telegram `typing` chat action for the current chat.
- [x] 1.2 Make the helper best-effort by catching and logging chat action failures without raising.

## 2. Handler Integration

- [x] 2.1 Call the typing helper at the start of text message processing before prompt/history/agent work begins.
- [x] 2.2 Call the typing helper in the voice/audio handler before media download, normalization, and STT processing begin.
- [x] 2.3 Ensure typing activity does not change language selection, STT, TTS, censoring, history saving, or final response behavior.

## 3. Tests

- [x] 3.1 Add an async text-processing test that verifies `typing` chat action is sent before the agent is invoked.
- [x] 3.2 Add an async voice-processing test that verifies `typing` chat action is sent before STT/media processing begins.
- [x] 3.3 Add a best-effort test that verifies a chat action failure does not prevent normal message processing.

## 4. Verification

- [x] 4.1 Run the focused bot handler tests affected by text and voice processing.
- [x] 4.2 Run `openspec status --change "send-typing-activity-on-user-message"` and confirm the change remains apply-ready.
