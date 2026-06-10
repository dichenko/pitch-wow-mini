## ADDED Requirements

### Requirement: Database shall store Telegram user profiles

The system SHALL create and maintain a `user_profiles` table for Telegram users.

Fields SHALL include: `tg_id` (BIGINT primary key), `preferred_language` (TEXT NULL with allowed values `uz`, `ru`, `en`), `first_name` (TEXT NULL), `last_name` (TEXT NULL), `username` (TEXT NULL), `language_code` (TEXT NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()), and `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

#### Scenario: User profile created

- **WHEN** the bot first sees a Telegram user
- **THEN** the system SHALL upsert a `user_profiles` record for that `tg_id`
- **THEN** Telegram display metadata SHALL be stored when available

#### Scenario: Preferred language persisted

- **WHEN** user selects a language from the language keyboard
- **THEN** the system SHALL update `user_profiles.preferred_language` to `uz`, `ru`, or `en`
- **THEN** `updated_at` SHALL be refreshed

#### Scenario: Preferred language loaded

- **WHEN** text or voice handlers process a user update
- **THEN** the system SHALL load `preferred_language` from `user_profiles` by Telegram user ID
- **THEN** missing or unsupported values SHALL be treated as no selected language

#### Scenario: Invalid language rejected at persistence boundary

- **WHEN** code attempts to persist a preferred language outside `uz`, `ru`, or `en`
- **THEN** the database constraint or repository validation SHALL reject the value

### Requirement: Dialogue history shall remain language-neutral

The system SHALL continue storing completed dialogue turns in `dialogue_history` without making language a required field.

#### Scenario: Dialogue stored after language selection

- **WHEN** a user with a stored preferred language receives a final assistant response
- **THEN** the system SHALL insert `dialogue_history` as before
- **THEN** language routing SHALL be recoverable from `user_profiles.preferred_language`
