## MODIFIED Requirements

### Requirement: Database shall store prompt versions

The system SHALL create and maintain a `prompt_versions` table.

Fields: `id` (UUID PK), `kind` (TEXT NOT NULL, CHECK system_prompt/tools_instruction/censor_prompt/welcome_message/welcome_message_ru/welcome_message_uz/welcome_message_en), `version_number` (INTEGER NOT NULL), `content` (TEXT NOT NULL), `is_active` (BOOLEAN NOT NULL DEFAULT FALSE), `created_by_admin_id` (UUID NULL REFERENCES admins), `created_by_tg_id` (BIGINT NULL), `created_by_username` (TEXT NULL), `change_note` (TEXT NULL), `restored_from_version_id` (UUID NULL REFERENCES prompt_versions), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

Constraints: UNIQUE(kind, version_number), partial unique index on (kind WHERE is_active=true) for one active per kind.

#### Scenario: Prompt version saved

- **WHEN** an admin saves a new system prompt
- **THEN** a new record SHALL be inserted with an incremented `version_number` and `is_active = TRUE`
- **THEN** all previous versions of the same kind SHALL have `is_active = FALSE`

#### Scenario: Localized welcome prompt version saved

- **WHEN** an admin saves a localized welcome message for one language
- **THEN** a new `prompt_versions` row SHALL be inserted for that language-specific welcome kind
- **THEN** all previous versions of that same language-specific welcome kind SHALL have `is_active = FALSE`
- **THEN** active prompt versions for other languages SHALL NOT be modified

## ADDED Requirements

### Requirement: Database migration shall allow localized welcome prompt kinds

The system SHALL update database constraints so `prompt_versions.kind` accepts `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en`.

#### Scenario: Localized kind accepted

- **WHEN** code inserts a prompt version with kind `welcome_message_ru`, `welcome_message_uz`, or `welcome_message_en`
- **THEN** the database SHALL accept the row when all other constraints are valid

#### Scenario: Unsupported kind rejected

- **WHEN** code inserts a prompt version with an unsupported kind
- **THEN** the database SHALL reject the row
