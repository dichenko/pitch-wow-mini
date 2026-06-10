## MODIFIED Requirements

### Requirement: Welcome message shall be sent on /start and /restart without LLM

The system SHALL use `/start` and `/restart` to establish the user's preferred language before normal conversation. If the user has no stored language, the bot SHALL show an inline language selection menu and SHALL NOT invoke the LLM. After a language is selected, or when a stored language already exists, the system SHALL send the active welcome message without invoking the LLM.

#### Scenario: First /start asks for language

- **WHEN** user sends `/start` and no preferred language exists for that Telegram user
- **THEN** the bot SHALL send an inline keyboard with Uzbek, Russian, and English language choices
- **THEN** the bot SHALL NOT send the normal welcome message yet
- **THEN** the bot SHALL NOT invoke the LLM

#### Scenario: Language selection sends welcome

- **WHEN** user selects a language from the `/start` inline keyboard
- **THEN** the bot SHALL persist the selected language in the user's profile
- **THEN** the bot SHALL reset the user's conversation thread
- **THEN** the bot SHALL send the active welcome message for the selected language without invoking the LLM
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: Returning /start sends localized welcome

- **WHEN** user sends `/start` and a preferred language already exists for that Telegram user
- **THEN** the bot SHALL send the active welcome message using the stored language
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: /restart preserves language and clears history

- **WHEN** user sends `/restart` and a preferred language already exists
- **THEN** the bot SHALL clear the conversation thread
- **THEN** the bot SHALL send the active welcome message using the stored language
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: No active welcome message

- **WHEN** no welcome message version is marked active in the database
- **THEN** the bot SHALL send a default greeting in the user's stored language
- **THEN** no dialogue history record SHALL be created

## ADDED Requirements

### Requirement: Language selection shall use inline buttons

The system SHALL present language choices as Telegram inline keyboard buttons with flag labels for Uzbek, Russian, and English.

#### Scenario: Language keyboard displayed

- **WHEN** the bot needs the user to choose a language
- **THEN** the keyboard SHALL include Uzbek, Russian, and English options
- **THEN** each callback payload SHALL encode one supported language code: `uz`, `ru`, or `en`

### Requirement: Bot shall require selected language before normal processing

The system SHALL require a stored preferred language before processing normal text or voice messages.

#### Scenario: Text message before language selection

- **WHEN** user sends a non-command text message without a stored preferred language
- **THEN** the bot SHALL ask the user to choose a language with the inline language keyboard
- **THEN** the bot SHALL NOT invoke the LLM

#### Scenario: Voice message before language selection

- **WHEN** user sends a voice or audio message without a stored preferred language
- **THEN** the bot SHALL ask the user to choose a language with the inline language keyboard
- **THEN** the bot SHALL NOT download, transcribe, or process the audio
