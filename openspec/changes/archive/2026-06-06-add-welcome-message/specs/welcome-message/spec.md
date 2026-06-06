## ADDED Requirements

### Requirement: Welcome message shall be sent on /start and /restart without LLM

The system SHALL send the active welcome message immediately when a user sends `/start` or `/restart`, without invoking the LLM.

#### Scenario: First /start sends welcome

- **WHEN** user sends `/start` for the first time
- **THEN** the bot SHALL send the active welcome message text directly
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: /restart sends welcome and clears history

- **WHEN** user sends `/restart`
- **THEN** the bot SHALL clear the conversation thread
- **THEN** the bot SHALL send the active welcome message
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: No active welcome message

- **WHEN** no welcome message version is marked active in the database
- **THEN** the bot SHALL send a default greeting: "Привет! Я AI-ассистент. Чем могу помочь?"
- **THEN** no dialogue history record SHALL be created

### Requirement: Welcome message shall enter LLM context on next request

The system SHALL include the welcome message in the LLM conversation history on the user's next message after receiving the welcome.

#### Scenario: Welcome appears in LLM context

- **WHEN** user sends `/start` and receives welcome message, then sends a text message
- **THEN** the LLM SHALL receive the welcome message as part of the conversation history

### Requirement: Welcome message shall be versioned

The system SHALL manage welcome messages using the `PromptVersion` model with `kind="welcome_message"`, supporting the same versioning features as system prompts.

#### Scenario: Admin creates new welcome version

- **WHEN** admin edits welcome message and saves
- **THEN** a new `PromptVersion` with `kind="welcome_message"` SHALL be created
- **THEN** the new version SHALL become active

#### Scenario: Admin restores previous version

- **WHEN** admin restores a previous welcome message version from history
- **THEN** a new `PromptVersion` SHALL be created with the content of the restored version

### Requirement: Default welcome message shall be seeded on first startup

The system SHALL create a default welcome message version if none exists in the database.

#### Scenario: First startup seeds default

- **WHEN** the bot starts and no `welcome_message` version exists
- **THEN** a default welcome message version SHALL be created with sensible text
