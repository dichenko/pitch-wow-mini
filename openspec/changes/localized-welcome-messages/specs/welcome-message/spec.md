## MODIFIED Requirements

### Requirement: Welcome message shall be sent on /start and /restart without LLM

The system SHALL send the active welcome message for the user's selected language when a user sends `/start` or `/restart`, without invoking the LLM.

#### Scenario: First /start sends localized welcome

- **WHEN** user sends `/start` and the user's preferred language is known
- **THEN** the bot SHALL send the active welcome message for that language directly
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: /restart sends localized welcome and clears history

- **WHEN** user sends `/restart` and the user's preferred language is known
- **THEN** the bot SHALL clear the conversation thread
- **THEN** the bot SHALL send the active welcome message for that language
- **THEN** the welcome message SHALL be persisted as an assistant message in `dialogue_history`

#### Scenario: No active localized welcome message

- **WHEN** no welcome message version is marked active for the user's selected language
- **THEN** the bot SHALL send a safe default greeting in that language
- **THEN** no dialogue history record SHALL be created for the missing DB welcome version

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

## ADDED Requirements

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
