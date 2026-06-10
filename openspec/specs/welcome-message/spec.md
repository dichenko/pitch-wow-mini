# welcome-message Specification

## Purpose
TBD - created by archiving change add-welcome-message. Update Purpose after archive.
## Requirements
### Requirement: Welcome message shall be sent on /start and /restart without LLM

The system SHALL use `/start` and `/restart` to establish the user's preferred language before normal conversation. If the user has no stored language, the bot SHALL show an inline language selection menu and SHALL NOT invoke the LLM. After a language is selected, or when a stored language already exists, the system SHALL send the active welcome message for the user's selected language without invoking the LLM.

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
- **THEN** the bot SHALL send the active welcome message for that language directly
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

### Requirement: Welcome message shall enter LLM context on next request

The system SHALL include the welcome message in the LLM conversation history on the user's next message after receiving the welcome.

#### Scenario: Welcome appears in LLM context

- **WHEN** user sends `/start` and receives welcome message, then sends a text message
- **THEN** the LLM SHALL receive the welcome message as part of the conversation history

### Requirement: Welcome message shall be versioned

The system SHALL manage welcome messages using the `PromptVersion` model with separate language-specific kinds: `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en`. Each language SHALL support independent active version, history, and restore behavior.

#### Scenario: Admin creates new Russian welcome version

- **WHEN** admin edits and saves the Russian welcome message
- **THEN** a new `PromptVersion` with `kind="welcome_message_ru"` SHALL be created
- **THEN** the new version SHALL become active for Russian users

#### Scenario: Admin creates new Uzbek welcome version

- **WHEN** admin edits and saves the Uzbek welcome message
- **THEN** a new `PromptVersion` with `kind="welcome_message_uz"` SHALL be created
- **THEN** the new version SHALL become active for Uzbek users

#### Scenario: Admin creates new English welcome version

- **WHEN** admin edits and saves the English welcome message
- **THEN** a new `PromptVersion` with `kind="welcome_message_en"` SHALL be created
- **THEN** the new version SHALL become active for English users

#### Scenario: Admin restores previous localized welcome version

- **WHEN** admin restores a previous welcome message version for one language
- **THEN** a new `PromptVersion` SHALL be created with the content of the restored version for that same language
- **THEN** welcome versions for other languages SHALL NOT be modified

### Requirement: Default welcome message shall be seeded on first startup

The system SHALL create default welcome message versions for Russian, Uzbek, and English if they do not exist in the database.

#### Scenario: First startup seeds localized defaults

- **WHEN** the bot starts and no localized welcome message versions exist
- **THEN** default `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en` versions SHALL be created with sensible text

#### Scenario: Legacy welcome migrated to Russian

- **WHEN** a legacy `welcome_message` version exists and no `welcome_message_ru` version exists
- **THEN** the system SHALL preserve the legacy content as the initial Russian welcome message
- **THEN** Uzbek and English defaults SHALL still be seeded when missing

### Requirement: Welcome lookup shall be language-aware

The system SHALL retrieve welcome content by supported language code.

#### Scenario: Russian welcome requested

- **WHEN** code requests the active welcome for `ru`
- **THEN** the system SHALL read the active `welcome_message_ru` version
- **THEN** if none exists, the system SHALL return the Russian safe default

#### Scenario: Uzbek welcome requested

- **WHEN** code requests the active welcome for `uz`
- **THEN** the system SHALL read the active `welcome_message_uz` version
- **THEN** if none exists, the system SHALL return the Uzbek safe default

#### Scenario: English welcome requested

- **WHEN** code requests the active welcome for `en`
- **THEN** the system SHALL read the active `welcome_message_en` version
- **THEN** if none exists, the system SHALL return the English safe default

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

