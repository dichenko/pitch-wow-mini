# Spec Delta: langsmith-observability

## Capability

```text
langsmith-observability
```

## ADDED Requirements

### Requirement: LangSmith tracing shall be supported

The system SHALL support optional LangSmith tracing for all LangChain/LangGraph agent executions.

Tracing SHALL be controlled through env variables and must not break the bot when disabled.

Required env:

```env
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_PROJECT=ai-assistant-template
LANGSMITH_WORKSPACE_ID=
LANGSMITH_TAGS=telegram,production
LANGSMITH_SAMPLE_RATE=1.0
```

#### Scenario: LangSmith disabled

- GIVEN `LANGSMITH_TRACING=false`
- WHEN user sends a message to the bot
- THEN the agent SHALL work normally
- AND no LangSmith network call SHALL be required

#### Scenario: LangSmith enabled

- GIVEN `LANGSMITH_TRACING=true`
- AND `LANGSMITH_API_KEY` is configured
- WHEN the agent handles a user message
- THEN the full LangChain/LangGraph run SHALL be traced in LangSmith
- AND the trace SHALL be stored under `LANGSMITH_PROJECT`

### Requirement: LangSmith project name shall be project-specific

The system SHALL use a project-specific LangSmith project name.

Recommended default:

```env
LANGSMITH_PROJECT=${PROJECT_SLUG}
```

#### Scenario: Multiple assistants use LangSmith

- GIVEN multiple assistant projects are deployed
- WHEN each project has a different `PROJECT_SLUG`
- THEN their traces SHALL be separated into different LangSmith projects

### Requirement: LangSmith trace metadata shall include local trace_id

Every LangSmith root run SHALL include metadata that links it to local logs and DB records.

Required metadata:

```json
{
  "trace_id": "...",
  "project_slug": "...",
  "telegram_user_id": "...",
  "telegram_username": "...",
  "bot_mode": "polling|webhook",
  "prompt_version": 1,
  "tools_instruction_version": 1,
  "llm_provider": "openai|anthropic|...",
  "llm_model": "..."
}
```

#### Scenario: Debugging user request

- GIVEN an admin has a local `trace_id`
- WHEN developer opens LangSmith
- THEN developer SHALL be able to find the corresponding LangSmith run by metadata

### Requirement: LangSmith tags shall identify environment and assistant

Every LangSmith run SHALL include tags.

Recommended tags:

```text
project:<PROJECT_SLUG>
env:<APP_ENV>
channel:telegram
bot-mode:<BOT_MODE>
```

Additional tags from `LANGSMITH_TAGS` SHALL be appended.

#### Scenario: Tags attached to trace

- GIVEN the agent processes a user message with LangSmith enabled
- WHEN the LangSmith run is created
- THEN the run SHALL include tags `project:<PROJECT_SLUG>`, `env:<APP_ENV>`, `channel:telegram`, `bot-mode:<BOT_MODE>`

### Requirement: LangSmith shall capture tool calls

The system SHALL ensure LangChain tool calls are visible in LangSmith traces.

#### Scenario: Agent calls tool

- GIVEN LangSmith tracing is enabled
- WHEN the agent calls `save_lead`
- THEN LangSmith trace SHALL show this tool call as a child run/span
- AND local `tool_call_logs` SHALL also store the call

### Requirement: LangSmith shall capture prompt versions

The system SHALL attach active prompt version numbers to traces.

Required fields:

- `system_prompt_version`;
- `tools_instruction_version`;
- `assembled_prompt_hash`.

Do NOT send secrets to metadata.

#### Scenario: Prompt versions in trace

- GIVEN LangSmith tracing is enabled
- WHEN the agent processes a user message
- THEN the LangSmith trace metadata SHALL include `system_prompt_version`, `tools_instruction_version` and `assembled_prompt_hash`

### Requirement: LangSmith integration shall avoid leaking secrets

The system SHALL NOT send secrets, raw env values, session cookies, admin login tokens or DB credentials into LangSmith metadata, tags, inputs, outputs or error messages.

#### Scenario: Tool receives secret

- GIVEN a tool internally uses an API key
- WHEN tracing is enabled
- THEN the API key SHALL NOT be included in tool input/output metadata

### Requirement: LangSmith shall be visible in admin debug page

The debug page `/admin/debug` SHALL show non-secret LangSmith status:

- tracing enabled/disabled;
- project name;
- endpoint host;
- workspace configured yes/no;
- last successful trace timestamp if available;
- last tracing error if available, without secrets.

#### Scenario: Admin views LangSmith debug info

- GIVEN an authenticated admin opens the debug page
- WHEN the page loads
- THEN LangSmith tracing status, project name and endpoint host SHALL be displayed without any secret values

### Requirement: LangSmith failures shall not break user conversations

LangSmith integration SHALL be best-effort.

#### Scenario: LangSmith API unavailable

- GIVEN tracing is enabled
- WHEN LangSmith API is unavailable or returns error
- THEN user conversation SHALL continue
- AND app logs SHALL record tracing error
- AND admin debug page SHALL show last tracing error

### Requirement: LangSmith shall capture censor LLM pass

The system SHALL trace the censor LLM call as part of the same trace when censor is enabled.

#### Scenario: Censor enabled with LangSmith

- GIVEN `LANGSMITH_TRACING=true` and censor is enabled
- WHEN the censor LLM reviews a draft response
- THEN the censor LLM call SHALL appear as a child run/span in the same LangSmith trace as the main agent run
- AND the censor run metadata SHALL include:
  - `trace_id`
  - `censor_enabled`: true
  - `censor_prompt_version`
  - `main_agent_run_id` (if available)

#### Scenario: Censor disabled with LangSmith

- GIVEN `LANGSMITH_TRACING=true` and censor is disabled
- WHEN the agent handles a user message
- THEN no censor LLM call SHALL appear in the LangSmith trace

#### Scenario: Censor LLM failure with LangSmith

- GIVEN censor is enabled and censor LLM fails
- WHEN the error is recorded
- THEN the censor error SHALL be logged in LangSmith metadata if tracing is enabled
- AND the error SHALL NOT include secrets or API keys
