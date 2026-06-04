# Spec Delta: langchain-tools

## Capability

```text
langchain-tools
```

## ADDED Requirements

### Requirement: Bot shall use LangChain agent with registered tools

The system SHALL use LangChain-compatible tools.

Minimum template tools:

1. `send_to_admin` (REQUIRED — see dedicated requirement below)
2. `save_lead` (stub)
3. `get_project_knowledge` (stub or reads from knowledge file)
4. `create_followup_task` (stub)

Tools may be stubs but MUST demonstrate the pattern for future projects.

#### Scenario: Bot starts with template tools registered

- GIVEN a bot starts from the template
- WHEN the LangChain agent initializes
- THEN `send_to_admin`, `save_lead`, `get_project_knowledge` and `create_followup_task` SHALL be registered as tools

### Requirement: Tools shall be defined in code, not in admin panel

The system SHALL NOT allow admins to create arbitrary executable tools from the web UI.

Admin panel can only edit natural language instructions on how the agent should use existing tools.

#### Scenario: Admin changes tools instruction

- GIVEN a tool exists in code
- WHEN admin changes tools instruction
- THEN agent behavior may change
- BUT executable tool implementation SHALL remain unchanged

### Requirement: Tool calls shall be logged

The system SHALL log every tool call.

Tool call log SHALL include:

- trace_id;
- user_tg_id;
- tool_name;
- tool_input JSON;
- tool_output summary;
- status;
- error;
- duration_ms;
- created_at.

#### Scenario: Tool call logged to DB

- GIVEN the agent invokes a tool
- WHEN the tool call completes
- THEN a row SHALL be inserted into `tool_call_logs` with trace_id, user_tg_id, tool_name, tool_input, tool_output, status, duration_ms

### Requirement: Agent requests shall have trace IDs

Every user message processed by the agent SHALL have a trace ID.

Trace ID SHALL be included in:

- application logs;
- agent execution logs;
- tool call logs;
- admin-visible debug view if implemented.

#### Scenario: Trace ID propagated through request

- GIVEN a user sends a message
- WHEN the agent processes the message
- THEN a unique trace_id SHALL be generated and included in all logs and DB records for that request

### Requirement: Template shall include a default `send_to_admin` tool

The system SHALL provide one mandatory default tool `send_to_admin` registered in the LangChain agent out of the box.

This tool SHALL be available to every assistant created from the template without any additional implementation by the developer.

**Purpose:** The model calls this tool when it needs to forward information to the administrators' chat.

**LLM-facing signature:**

```python
send_to_admin(comment: str)
```

The LLM SHALL pass only a free-form `comment` field.

All Telegram user data SHALL be attached automatically by the backend, not generated or supplied by the LLM.

#### Scenario: Agent calls `send_to_admin`

- GIVEN the LangChain agent decides information should be forwarded to admins
- WHEN the agent invokes `send_to_admin(comment="...")`
- THEN the tool SHALL send the `comment` to the admin chat identified by `ADMIN_TELEGRAM_CHAT_ID`
- AND the tool SHALL automatically attach the following user fields:
  - `tg_id`
  - `first_name` (if available)
  - `last_name` (if available)
  - `username` (if available)
  - `telegram_link` = `https://t.me/<username>` (only if username exists)
  - `language_code` (if available)
  - current `trace_id`
  - timestamp of the request

#### Scenario: `ADMIN_TELEGRAM_CHAT_ID` is not configured

- GIVEN `ADMIN_TELEGRAM_CHAT_ID` is empty or not set in `.env`
- WHEN the agent invokes `send_to_admin`
- THEN the tool SHALL NOT break the user conversation
- AND the tool SHALL save the notification payload to the `admin_notifications` table in DB
- AND the tool SHALL return a success confirmation to the agent

#### Scenario: `ADMIN_TELEGRAM_CHAT_ID` is configured

- GIVEN `ADMIN_TELEGRAM_CHAT_ID` is set in `.env`
- WHEN the agent invokes `send_to_admin`
- THEN the tool SHALL send the formatted message to that Telegram chat via Bot API
- AND the tool SHALL also save the notification record to `admin_notifications` table

#### Scenario: User has no username

- GIVEN a Telegram user without a `username` set in their profile
- WHEN the agent invokes `send_to_admin`
- THEN the tool SHALL send the notification without `telegram_link`
- AND `telegram_link` field SHALL be `null` in the notification payload

#### Scenario: Tool is registered by default

- GIVEN a new assistant project created from the template
- WHEN the bot starts
- THEN `send_to_admin` SHALL already be registered in the LangChain agent
- AND no additional developer configuration SHALL be required to make the tool available

#### Scenario: LLM does not generate user data

- GIVEN the `send_to_admin` tool is invoked
- WHEN the LLM constructs the tool call
- THEN the LLM SHALL only supply the `comment` argument
- AND all user identity fields SHALL be injected server-side by the tool implementation, not by the LLM

#### Scenario: Tool call is logged

- GIVEN `send_to_admin` is invoked
- WHEN the tool completes (success or failure)
- THEN the call SHALL be logged to `tool_call_logs` with trace_id, tool_name, input, output, status, duration_ms
- AND the notification record SHALL be persisted in `admin_notifications` table

#### Scenario: Tool is described in default tools instruction

- GIVEN a fresh template deployment with seeded defaults
- WHEN the active tools instruction is loaded
- THEN the default tools instruction SHALL include guidance on when and how the agent should use `send_to_admin`
