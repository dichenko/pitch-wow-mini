## MODIFIED Requirements

### Requirement: /restart command shall clear conversation history

The bot SHALL support a `/restart` command.

The `/restart` command SHALL clear the user's conversation history so the next message starts a fresh conversation.

The `/restart` command SHALL send the active welcome message to the user and persist it to dialogue history.

#### Scenario: User sends /restart

- **WHEN** a user sends `/restart`
- **THEN** the user's conversation history SHALL be cleared
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context

### Requirement: /start command shall clear conversation history

The `/start` command SHALL clear the user's conversation history before sending the welcome message.

The `/start` command SHALL send the active welcome message to the user and persist it to dialogue history.

#### Scenario: User sends /start with existing history

- **WHEN** a user with existing conversation history sends `/start`
- **THEN** the conversation history SHALL be cleared
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context

#### Scenario: First /start

- **WHEN** a new user sends `/start` for the first time
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context
