## MODIFIED Requirements

### Requirement: Missing prompts shall have safe defaults

The system SHALL seed default prompt versions during first startup if required prompt versions are missing.

Defaults SHALL include generic helpful assistant system prompt, tools instruction describing available tools, censor prompt as response reviewer, and localized welcome messages for Russian, Uzbek, and English. Default `censor_enabled` SHALL be `"false"`.

#### Scenario: Empty DB

- **WHEN** prompt_versions table is empty and app starts
- **THEN** system SHALL insert default active system prompt, tools instruction, and censor prompt with `created_by_username = "system"`
- **THEN** system SHALL insert default active `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en` versions with `created_by_username = "system"`

## ADDED Requirements

### Requirement: Localized welcome prompts shall be versioned independently

The system SHALL version localized welcome prompts using the same append-only prompt versioning mechanism as other prompt types.

#### Scenario: Russian welcome version saved

- **WHEN** a new Russian welcome message is saved
- **THEN** the system SHALL create a new active `welcome_message_ru` prompt version
- **THEN** previous `welcome_message_ru` versions SHALL remain stored and inactive
- **THEN** Uzbek and English welcome versions SHALL NOT be modified

#### Scenario: Uzbek welcome version saved

- **WHEN** a new Uzbek welcome message is saved
- **THEN** the system SHALL create a new active `welcome_message_uz` prompt version
- **THEN** previous `welcome_message_uz` versions SHALL remain stored and inactive
- **THEN** Russian and English welcome versions SHALL NOT be modified

#### Scenario: English welcome version saved

- **WHEN** a new English welcome message is saved
- **THEN** the system SHALL create a new active `welcome_message_en` prompt version
- **THEN** previous `welcome_message_en` versions SHALL remain stored and inactive
- **THEN** Russian and Uzbek welcome versions SHALL NOT be modified

#### Scenario: Localized welcome restored

- **WHEN** admin restores a previous localized welcome prompt version
- **THEN** the restored content SHALL become a new active version for the same prompt kind
- **THEN** the source version SHALL remain unchanged
