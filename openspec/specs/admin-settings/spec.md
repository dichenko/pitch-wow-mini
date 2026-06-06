# Spec: admin-settings

## Purpose

Global system settings page in the admin panel. Allows configuring LLM providers and models independently for the main agent and the censor/reviewer agent. Settings are persisted in the `app_settings` database table with `.env` fallbacks.
## Requirements
### Requirement: Settings page shall allow LLM provider selection

The admin panel SHALL provide a Settings page at `/admin/settings`.

Settings page SHALL allow:

- select LLM provider for the main agent: `openai`, `anthropic`, or `mistral`;
- enter model name for the main agent;
- select LLM provider for the censor/reviewer: `openai`, `anthropic`, or `mistral`;
- enter model name for the censor;
- enter `LLM_HISTORY_MESSAGES`, the number of recent dialogue records included in LLM requests;
- save all settings.

`write` and `superadmin` SHALL be allowed to edit settings. `read` SHALL be allowed to view settings read-only.

#### Scenario: Admin views settings

- **WHEN** admin with at least `read` role opens the Settings page
- **THEN** the current LLM provider and model for both main agent and censor SHALL be displayed
- **THEN** the current `LLM_HISTORY_MESSAGES` value SHALL be displayed

#### Scenario: Write admin saves settings

- **WHEN** admin with `write` or `superadmin` role changes LLM provider, model, or `LLM_HISTORY_MESSAGES` and saves
- **THEN** the selections SHALL be persisted in `app_settings` table
- **THEN** the next LLM invocation SHALL use the new provider, model, and history record count

#### Scenario: Invalid history count rejected

- **WHEN** admin submits a non-integer or negative `LLM_HISTORY_MESSAGES` value
- **THEN** the settings SHALL NOT be saved
- **THEN** the settings page SHALL show a validation error

### Requirement: LLM settings shall be stored in app_settings table

The system SHALL store LLM configuration in `app_settings` with the following keys:

| Key | Values | Default |
|-----|--------|---------|
| `llm_provider` | `openai`, `anthropic`, `mistral` | `openai` |
| `llm_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |
| `censor_provider` | `openai`, `anthropic`, `mistral` | `openai` |
| `censor_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |
| `llm_history_messages` | non-negative integer string | `20` |

#### Scenario: Settings read from DB

- **WHEN** the main agent or censor is about to invoke the LLM
- **THEN** the system SHALL read `llm_provider` / `llm_model` or `censor_provider` / `censor_model` from `app_settings`
- **THEN** the system SHALL read `llm_history_messages` from `app_settings`
- **THEN** if the setting is not set, SHALL fall back to the corresponding `.env` or default value

#### Scenario: Provider change takes effect immediately

- **WHEN** admin changes the `llm_provider` from `openai` to `mistral` and saves
- **THEN** the next user message SHALL be processed by Mistral instead of OpenAI

#### Scenario: History count change takes effect immediately

- **WHEN** admin changes `LLM_HISTORY_MESSAGES` from `20` to `5` and saves
- **THEN** the next user message SHALL include at most 5 prior dialogue records in each LLM request

### Requirement: Settings page shall require CSRF protection

All POST requests that save admin settings SHALL include a valid CSRF token.

The settings page SHALL render a hidden CSRF token whose value matches the CSRF cookie that the server expects on the subsequent save request.

#### Scenario: Settings form renders synchronized CSRF token

- **WHEN** an authenticated admin opens `/admin/settings`
- **THEN** the response SHALL include a `csrf_token` cookie
- **THEN** the settings form SHALL include a hidden `csrf_token` field with the same token value

#### Scenario: POST without CSRF token

- **WHEN** an admin sends a POST to `/admin/settings/save` without a matching CSRF token
- **THEN** the system SHALL reject the request with 403

#### Scenario: POST with synchronized CSRF token

- **WHEN** an admin opens `/admin/settings` and submits the rendered settings form without modifying its CSRF field
- **THEN** CSRF validation SHALL pass
- **THEN** settings validation and persistence SHALL continue according to the admin's role and submitted values

### Requirement: Settings changes shall be audited

The system SHALL log an audit event `settings.updated` when settings are saved.

#### Scenario: Settings save logged

- **WHEN** admin saves settings
- **THEN** an audit log entry SHALL be created with action `settings.updated` and metadata containing the changed keys

