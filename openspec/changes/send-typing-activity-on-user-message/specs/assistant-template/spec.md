## MODIFIED Requirements

### Requirement: Request pipeline shall support voice, censor and send_to_admin

The bot service SHALL process every incoming Telegram update through a defined pipeline and SHALL emit Telegram typing activity after receiving processable user input.

Required pipeline order:

```text
Telegram update
-> send typing chat action for processable user input
-> normalize input
-> if voice/audio: STT pipeline (OpenAI primary, Aisha fallback)
-> message log
-> assemble prompt:
   core guardrails
   active system prompt
   active tools instruction
-> LangChain agent
-> tool calls if needed, including send_to_admin
-> draft response
-> if censor enabled: censor LLM pass
-> final response
-> send to Telegram
-> logs/traces/LangSmith
```

#### Scenario: Text message with censor enabled

- **WHEN** user sends a text message and censor is enabled
- **THEN** the bot SHALL send a Telegram `typing` chat action for that chat before long-running processing begins
- **THEN** the censor LLM SHALL review the draft response
- **THEN** the final response SHALL be the censor output

#### Scenario: Voice message processed

- **WHEN** user sends a voice message and `VOICE_ENABLED=true`
- **THEN** the bot SHALL send a Telegram `typing` chat action for that chat before STT processing begins
- **THEN** the transcribed text SHALL be processed as a regular text message through the full pipeline

#### Scenario: Typing activity fails

- **WHEN** the Telegram API call for `typing` activity fails
- **THEN** the bot SHALL continue processing the user message normally
- **THEN** the user SHALL NOT receive an error caused only by typing activity failure
