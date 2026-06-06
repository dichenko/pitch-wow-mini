## MODIFIED Requirements

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

## ADDED Requirements

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
