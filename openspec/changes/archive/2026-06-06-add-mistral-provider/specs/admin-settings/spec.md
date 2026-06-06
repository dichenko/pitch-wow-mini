## MODIFIED Requirements

### Requirement: Settings page shall allow LLM provider selection

The admin panel SHALL provide a Settings page at `/admin/settings`.

Settings page SHALL allow:

- select LLM provider for the main agent: `openai`, `anthropic`, or `mistral`;
- enter model name for the main agent;
- select LLM provider for the censor/reviewer: `openai`, `anthropic`, or `mistral`;
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
| `llm_provider` | `openai`, `anthropic`, `mistral` | `openai` |
| `llm_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |
| `censor_provider` | `openai`, `anthropic`, `mistral` | `openai` |
| `censor_model` | any model name string | from `.env` (`OPENAI_TEXT_MODEL`) |

#### Scenario: Settings read from DB

- **WHEN** the main agent or censor is about to invoke the LLM
- **THEN** the system SHALL read `llm_provider` / `llm_model` or `censor_provider` / `censor_model` from `app_settings`
- **THEN** if the setting is not set, SHALL fall back to the corresponding `.env` value

#### Scenario: Provider change takes effect immediately

- **WHEN** admin changes the `llm_provider` from `openai` to `mistral` and saves
- **THEN** the next user message SHALL be processed by Mistral instead of OpenAI
