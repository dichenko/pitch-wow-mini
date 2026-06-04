# Spec: admin-settings

## Purpose

Global system settings page in the admin panel. Allows configuring LLM providers and models independently for the main agent and the censor/reviewer agent. Settings are persisted in the `app_settings` database table with `.env` fallbacks.

## Requirements

### Requirement: Settings page shall allow LLM provider selection

The admin panel SHALL provide a Settings page at `/admin/settings`.

Settings page SHALL allow:

- select LLM provider for the main agent: `openai` or `anthropic`;
- enter model name for the main agent;
- select LLM provider for the censor/reviewer: `openai` or `anthropic`;
- enter model name for the censor;
- save all settings.

`write` and `superadmin` SHALL be allowed to edit settings. `read` SHALL be allowed to view settings read-only.

#### Scenario: Admin views settings

- **WHEN** admin with at least `read` role opens the Settings page
- **THEN** the current LLM provider and model for both main agent and censor SHALL be displayed

#### Scenario: Write admin saves settings

- **WHEN** admin with `write` or `superadmin` role changes LLM provider or model and saves
- **THEN** the selections SHALL be persisted in `app_settings` table
- **THEN** the next agent invocation SHALL use the new provider and model

### Requirement: LLM settings shall be stored in app_settings table

The system SHALL store LLM configuration in `app_settings` with the following keys:

| Key | Values | Default |
|-----|--------|---------|
| `llm_provider` | `openai`, `anthropic` | `openai` |
| `llm_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |
| `censor_provider` | `openai`, `anthropic` | `openai` |
| `censor_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |

#### Scenario: Settings read from DB

- **WHEN** the main agent or censor is about to invoke the LLM
- **THEN** the system SHALL read `llm_provider` / `llm_model` or `censor_provider` / `censor_model` from `app_settings`
- **THEN** if the setting is not set, SHALL fall back to the corresponding `.env` value

#### Scenario: Provider change takes effect immediately

- **WHEN** admin changes the `llm_provider` from `openai` to `anthropic` and saves
- **THEN** the next user message SHALL be processed by Anthropic Claude instead of OpenAI

### Requirement: Settings page shall require CSRF protection

All POST requests to `/admin/settings` SHALL include a valid CSRF token.

#### Scenario: POST without CSRF token

- **WHEN** an admin sends a POST to `/admin/settings` without a matching CSRF token
- **THEN** the system SHALL reject the request with 403

### Requirement: Settings changes shall be audited

The system SHALL log an audit event `settings.updated` when settings are saved.

#### Scenario: Settings save logged

- **WHEN** admin saves settings
- **THEN** an audit log entry SHALL be created with action `settings.updated` and metadata containing the changed keys
