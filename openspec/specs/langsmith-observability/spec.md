# Spec: langsmith-observability

## Purpose

Optional LangSmith tracing integration for LangChain/LangGraph agent executions. Provides trace metadata linking to local logs, project-specific trace separation, and best-effort failure handling. Never leaks secrets.

## Requirements

### Requirement: LangSmith tracing shall be optional

The system SHALL support optional LangSmith tracing controlled through `LANGSMITH_TRACING` env variable. It SHALL NOT break the bot when disabled.

#### Scenario: LangSmith disabled

- **WHEN** `LANGSMITH_TRACING=false` and user sends a message
- **THEN** the agent SHALL work normally with no LangSmith network calls

#### Scenario: LangSmith enabled

- **WHEN** `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` is configured and the agent handles a user message
- **THEN** the full LangChain/LangGraph run SHALL be traced in LangSmith

### Requirement: LangSmith project name shall use PROJECT_SLUG

The system SHALL use `LANGSMITH_PROJECT` from env, defaulting to `PROJECT_SLUG`.

#### Scenario: Multiple assistants use LangSmith

- **WHEN** multiple assistant projects are deployed with different `PROJECT_SLUG` values
- **THEN** their traces SHALL be separated into different LangSmith projects

### Requirement: LangSmith trace metadata shall include trace_id

Every LangSmith root run SHALL include metadata: `trace_id`, `project_slug`, `app_env`, `bot_mode`, `system_prompt_version`, `tools_instruction_version`, `assembled_prompt_hash`, `llm_provider`, `llm_model`.

#### Scenario: Debugging user request

- **WHEN** an admin has a local `trace_id` and opens LangSmith
- **THEN** developer SHALL find the corresponding LangSmith run by metadata

### Requirement: LangSmith tags shall identify environment

Every LangSmith run SHALL include tags: `project:<PROJECT_SLUG>`, `env:<APP_ENV>`, `channel:telegram`, `bot-mode:<BOT_MODE>`. Additional tags from `LANGSMITH_TAGS` env SHALL be appended.

#### Scenario: Tags attached to trace

- **WHEN** the agent processes a user message with LangSmith enabled
- **THEN** the run SHALL include the standard tags

### Requirement: LangSmith shall capture tool calls

The system SHALL ensure LangChain tool calls are visible in LangSmith traces as child runs/spans.

#### Scenario: Agent calls tool

- **WHEN** LangSmith tracing is enabled and the agent calls a tool
- **THEN** LangSmith trace SHALL show this tool call as a child run/span
- **THEN** local `tool_call_logs` SHALL also store the call

### Requirement: LangSmith shall capture prompt versions

The system SHALL attach `system_prompt_version`, `tools_instruction_version`, and `assembled_prompt_hash` to traces.

#### Scenario: Prompt versions in trace

- **WHEN** LangSmith tracing is enabled and the agent processes a user message
- **THEN** the trace metadata SHALL include prompt version numbers and assembled prompt hash

### Requirement: LangSmith integration shall avoid leaking secrets

The system SHALL NOT send secrets, raw env values, session cookies, admin login tokens, or DB credentials into LangSmith metadata, tags, inputs, or outputs.

#### Scenario: Tool receives secret

- **WHEN** a tool internally uses an API key and tracing is enabled
- **THEN** the API key SHALL NOT be included in tool input/output metadata

### Requirement: LangSmith shall be visible in admin debug page

The debug page `/admin/debug` SHALL show non-secret LangSmith status: tracing enabled/disabled, project name, endpoint host, workspace configured yes/no.

#### Scenario: Admin views LangSmith debug info

- **WHEN** an authenticated admin opens the debug page
- **THEN** LangSmith tracing status SHALL be displayed without any secret values

### Requirement: LangSmith failures shall not break conversations

LangSmith integration SHALL be best-effort. Failures SHALL be logged locally and conversations SHALL continue.

#### Scenario: LangSmith API unavailable

- **WHEN** tracing is enabled and LangSmith API is unavailable
- **THEN** user conversation SHALL continue
- **THEN** app logs SHALL record the tracing error
