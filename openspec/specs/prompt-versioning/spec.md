# Spec: prompt-versioning

## Purpose

Versioned management of system prompts, tools instructions, and censor prompts stored in the database. Supports creating new versions, viewing history, restoring previous versions (as new versions), and automatic seeding of defaults on first startup. Prompt assembly combines guardrails with active versions.

## Requirements

### Requirement: System prompt shall be editable from admin panel

The system SHALL store the active system prompt in DB as `prompt_versions` with `kind = system_prompt`.

#### Scenario: Admin opens prompt page

- **WHEN** admin with at least `read` role opens "System Prompt"
- **THEN** admin SHALL see the active prompt content and metadata (version, author, created date)

#### Scenario: Admin saves prompt

- **WHEN** admin with `write` or `superadmin` role edits and saves system prompt
- **THEN** system SHALL create a new prompt version, mark it active, and keep all previous versions

### Requirement: Old system prompts shall be preserved

The system SHALL never overwrite old prompt versions. Each version record includes: `id`, `kind`, `content`, `version_number`, `is_active`, `created_by_admin_id`, `created_by_tg_id`, `created_by_username`, `created_at`, `change_note`.

#### Scenario: History preserved after multiple edits

- **WHEN** a system prompt has been edited three times and admin views version history
- **THEN** all three previous versions SHALL be present with their content, author and timestamp intact

### Requirement: Last three system prompts shall be restorable

The admin panel SHALL show the last three previous versions with restore buttons. Restore creates a new active version copied from the selected source; the source is not modified.

#### Scenario: Admin restores previous system prompt

- **WHEN** admin with `write` or `superadmin` role clicks restore on one of the last three versions
- **THEN** system SHALL create a new active version copied from selected old version
- **THEN** record who restored it and when, leaving old versions unchanged

### Requirement: Tools instruction shall be editable and versioned

The system SHALL store tools instruction separately using the same versioning mechanism with `kind = tools_instruction`.

#### Scenario: Admin edits tools instruction

- **WHEN** admin with `write` or `superadmin` role saves tools instruction
- **THEN** system SHALL create a new active tools instruction version

#### Scenario: Admin restores previous tools instruction

- **WHEN** admin with `write` or `superadmin` role restores one of the last three versions
- **THEN** system SHALL create a new active version copied from selected version

### Requirement: Censor prompt shall be editable and versioned

The system SHALL store the censor prompt separately using the same versioning mechanism with `kind = censor_prompt`.

#### Scenario: Admin edits censor prompt

- **WHEN** admin with `write` or `superadmin` role saves censor prompt
- **THEN** system SHALL create a new active censor prompt version

#### Scenario: Admin restores previous censor prompt

- **WHEN** admin with `write` or `superadmin` role restores one of the last three censor prompt versions
- **THEN** system SHALL create a new active version copied from selected version

### Requirement: Prompt assembly shall include guardrails, system prompt, and tools instruction

The system SHALL concatenate prompts in order: `core guardrails` + `active system prompt` + `"# Tools usage instruction"` header + `active tools instruction`.

Core guardrails are non-editable (from `core_guardrails.py`). System prompt and tools instruction are loaded from DB.

#### Scenario: User sends message

- **WHEN** active system prompt and active tools instruction exist and bot handles a user message
- **THEN** LangChain agent SHALL receive the assembled system message

### Requirement: Censor prompt shall be used in pipeline

When censor is enabled, the censor LLM SHALL receive the active censor prompt together with the original user message and the draft response.

#### Scenario: Censor prompt used in pipeline

- **WHEN** censor is enabled, active censor prompt exists, and the main agent produces a draft response
- **THEN** the censor LLM SHALL receive the active censor prompt, original user message, and draft response
- **THEN** return the final response text

### Requirement: Missing prompts shall have safe defaults

The system SHALL seed default prompt versions during first startup if required prompt versions are missing.

Defaults SHALL include generic helpful assistant system prompt, tools instruction describing available tools, censor prompt as response reviewer, and localized welcome messages for Russian, Uzbek, and English. Default `censor_enabled` SHALL be `"false"`.

#### Scenario: Empty DB

- **WHEN** prompt_versions table is empty and app starts
- **THEN** system SHALL insert default active system prompt, tools instruction, and censor prompt with `created_by_username = "system"`
- **THEN** system SHALL insert default active `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en` versions with `created_by_username = "system"`

### Requirement: Assembled prompt hash shall be computed

For every request, a SHA-256 hash of the assembled prompt SHALL be computed and included in metadata for LangSmith and debugging.

#### Scenario: Prompt hash in metadata

- **WHEN** the bot assembles the prompt
- **THEN** a SHA-256 hex digest of the full assembled prompt SHALL be stored in metadata

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
