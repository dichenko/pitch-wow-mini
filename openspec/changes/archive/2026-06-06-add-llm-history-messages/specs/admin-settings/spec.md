## MODIFIED Requirements

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
