# Spec: database

## Purpose

PostgreSQL database schema for the AI assistant template. Defines all tables including admins, login tokens, prompt versions, audit log, admin notifications, censor runs, application settings, and tool call logs.
## Requirements
### Requirement: Database shall store admins

The system SHALL create and maintain an `admins` table.

Fields: `id` (UUID PK), `tg_id` (BIGINT UNIQUE NOT NULL), `username` (TEXT NULL), `display_name` (TEXT NULL), `role` (TEXT NOT NULL, CHECK read/write/superadmin), `is_active` (BOOLEAN NOT NULL DEFAULT TRUE), `created_by_admin_id` (UUID NULL REFERENCES admins), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()), `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT now() ON UPDATE), `deactivated_by_admin_id` (UUID NULL), `deactivated_at` (TIMESTAMPTZ NULL).

Index on `tg_id`.

#### Scenario: Admin record created

- **WHEN** a new admin is added by a superadmin
- **THEN** the `admins` table SHALL contain the new record with `is_active = TRUE`

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

### Requirement: Database shall store admin login tokens

The system SHALL create and maintain an `admin_login_tokens` table.

Fields: `id` (UUID PK), `admin_tg_id` (BIGINT NOT NULL), `token_hash` (TEXT UNIQUE NOT NULL), `expires_at` (TIMESTAMPTZ NOT NULL), `used_at` (TIMESTAMPTZ NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()), `ip_address` (INET NULL), `user_agent` (TEXT NULL).

Indexes on `token_hash`, `expires_at`.

#### Scenario: Login token created

- **WHEN** an admin requests a login link via `/admin` and the token is generated
- **THEN** a record SHALL be inserted with only the SHA-256 hash and an expiry timestamp

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

### Requirement: Database shall store audit log

The system SHALL create and maintain an `admin_audit_log` table.

Fields: `id` (UUID PK), `admin_id` (UUID NULL REFERENCES admins), `admin_tg_id` (BIGINT NULL), `action` (TEXT NOT NULL), `entity_type` (TEXT NOT NULL), `entity_id` (UUID NULL), `metadata` (JSONB NOT NULL DEFAULT '{}'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()), `ip_address` (INET NULL), `user_agent` (TEXT NULL).

Indexes on `admin_id`, `created_at`.

Audit actions: `admin.login_link_created`, `admin.login_success`, `prompt.created`, `prompt.restored`, `tools_instruction.created`, `tools_instruction.restored`, `censor_prompt.created`, `censor_prompt.restored`, `censor.toggled`, `admin.created`, `admin.role_changed`, `admin.deactivated`.

#### Scenario: Audit event recorded

- **WHEN** an admin performs an auditable action
- **THEN** a row SHALL be inserted into `admin_audit_log` with the action name and relevant metadata

### Requirement: Database shall store admin notifications

The system SHALL create and maintain an `admin_notifications` table to store `send_to_admin` payloads.

Fields: `id` (UUID PK), `trace_id` (TEXT NOT NULL), `user_tg_id` (BIGINT NOT NULL), `first_name` (TEXT NULL), `last_name` (TEXT NULL), `username` (TEXT NULL), `telegram_link` (TEXT NULL), `language_code` (TEXT NULL), `comment` (TEXT NOT NULL), `payload` (JSONB NOT NULL DEFAULT '{}'), `delivered` (BOOLEAN NOT NULL DEFAULT FALSE), `delivery_error` (TEXT NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

Indexes on `trace_id`, `created_at`.

#### Scenario: Notification persisted

- **WHEN** `send_to_admin` is invoked by the agent and the tool completes
- **THEN** a row SHALL be inserted into `admin_notifications` with the full payload

### Requirement: Database shall store censor runs

The system SHALL create and maintain a `censor_runs` table.

Fields: `id` (UUID PK), `trace_id` (TEXT NOT NULL), `user_tg_id` (BIGINT NULL), `draft_response` (TEXT NOT NULL), `final_response` (TEXT NOT NULL), `censor_prompt_version` (INTEGER NOT NULL), `censor_model` (TEXT NULL), `status` (TEXT NOT NULL, CHECK success/error/skipped), `error` (TEXT NULL), `duration_ms` (INTEGER NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

Indexes on `trace_id`, `created_at`.

#### Scenario: Censor run recorded

- **WHEN** censor is enabled and processes a response, and the censor LLM call completes
- **THEN** a row SHALL be inserted into `censor_runs` with status `success` or `error`

### Requirement: Database shall store application settings

The system SHALL create and maintain an `app_settings` table.

Fields: `key` (TEXT PK), `value` (TEXT NOT NULL), `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT now() ON UPDATE), `updated_by_admin_id` (UUID NULL REFERENCES admins).

Known settings include:

- `censor_enabled` (`"true"` or `"false"`)
- `llm_provider`
- `llm_model`
- `censor_provider`
- `censor_model`
- `llm_history_messages` (non-negative integer string, default `20`)

#### Scenario: Setting updated

- **WHEN** an admin toggles or edits a setting
- **THEN** the `app_settings` row SHALL be upserted with the new value and `updated_at` timestamp

### Requirement: Database shall store tool call logs

The system SHALL create and maintain a `tool_call_logs` table.

Fields: `id` (UUID PK), `trace_id` (TEXT NOT NULL), `user_tg_id` (BIGINT NULL), `tool_name` (TEXT NOT NULL), `tool_input` (JSONB NULL), `tool_output` (TEXT NULL), `status` (TEXT NOT NULL), `error` (TEXT NULL), `duration_ms` (INTEGER NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

Indexes on `trace_id`, `created_at`.

#### Scenario: Tool call logged to DB

- **WHEN** the agent invokes a tool and the tool call completes
- **THEN** a row SHALL be inserted into `tool_call_logs` with trace_id, user_tg_id, tool_name, tool_input, tool_output, status, duration_ms

### Requirement: Database shall store dialogue history records

The system SHALL create and maintain a `dialogue_history` table for completed user-facing dialogue turns.

Fields: `id` (UUID PK), `thread_id` (TEXT NOT NULL), `user_tg_id` (BIGINT NOT NULL), `trace_id` (TEXT NOT NULL), `user_message` (TEXT NOT NULL), `assistant_response` (TEXT NOT NULL), `llm_provider` (TEXT NULL), `llm_model` (TEXT NULL), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT now()).

Indexes SHALL support efficient retrieval of the latest records by `user_tg_id`, `thread_id`, and `created_at`.

#### Scenario: Dialogue turn persisted

- **WHEN** the bot produces a final response for a user message
- **THEN** one row SHALL be inserted into `dialogue_history` with the user's message and final assistant response

#### Scenario: Latest dialogue records loaded

- **WHEN** the bot prepares an LLM request for a user with existing dialogue history
- **THEN** the system SHALL query `dialogue_history` for the latest records matching that `user_tg_id` and `thread_id`
- **THEN** the number of loaded records SHALL NOT exceed `llm_history_messages`

#### Scenario: Failed LLM request not persisted

- **WHEN** the bot cannot produce a final assistant response for a user message
- **THEN** no completed dialogue row SHALL be inserted for that failed message

### Requirement: Database migration shall allow localized welcome prompt kinds

The system SHALL update database constraints so `prompt_versions.kind` accepts `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en`.

#### Scenario: Localized kind accepted

- **WHEN** code inserts a prompt version with kind `welcome_message_ru`, `welcome_message_uz`, or `welcome_message_en`
- **THEN** the database SHALL accept the row when all other constraints are valid

#### Scenario: Unsupported kind rejected

- **WHEN** code inserts a prompt version with an unsupported kind
- **THEN** the database SHALL reject the row

### Requirement: Dialogue history shall remain language-neutral

The system SHALL continue storing completed dialogue turns in `dialogue_history` without making language a required field.

#### Scenario: Dialogue stored after language selection

- **WHEN** a user with a stored preferred language receives a final assistant response
- **THEN** the system SHALL insert `dialogue_history` as before
- **THEN** language routing SHALL be recoverable from `user_profiles.preferred_language`

