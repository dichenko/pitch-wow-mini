# Spec: langchain-tools

## Purpose

LangGraph ReAct agent with registered tools for the Telegram bot. Includes a mandatory `send_to_admin` tool plus three stub tools demonstrating the pattern for future projects. Tool calls are logged to the database with trace IDs.
## Requirements
### Requirement: Bot shall use LangGraph ReAct agent with registered tools

The system SHALL use a LangGraph ReAct agent (`create_react_agent`) with a configurable LLM provider and a `MemorySaver` checkpointer for multi-turn conversation continuity.

Supported providers: OpenAI (`ChatOpenAI`), Anthropic (`ChatAnthropic`), and Mistral (`ChatMistralAI`).

Four tools registered: `send_to_admin` (REQUIRED), `save_lead` (stub), `get_project_knowledge` (reads knowledge file), `create_followup_task` (stub).

LLM provider and model SHALL be read from `app_settings` (`llm_provider`, `llm_model`), falling back to `.env` defaults. Temperature SHALL be 0.7.

Provider-specific configuration:

- **OpenAI**: uses `OPENAI_API_KEY`, `OPENAI_BASE_URL` from `.env`
- **Anthropic**: uses `ANTHROPIC_API_KEY` from `.env`
- **Mistral**: uses `MISTRAL_API_KEY` from `.env`

The assembled system prompt SHALL be passed to `create_react_agent` using a keyword supported by the pinned LangGraph runtime.

The agent SHALL be configured with a checkpointer. Each user SHALL have a persistent `thread_id` based on their Telegram user ID for conversation continuity across messages.

#### Scenario: Bot starts with template tools registered

- **WHEN** a bot starts from the template and the LangChain agent initializes
- **THEN** all four tools SHALL be registered

#### Scenario: Agent uses OpenAI

- **WHEN** `llm_provider` is set to `openai` (or not set) and a user sends a message
- **THEN** the main agent SHALL invoke `ChatOpenAI` with the configured model

#### Scenario: Agent uses Anthropic

- **WHEN** `llm_provider` is set to `anthropic` and a user sends a message
- **THEN** the main agent SHALL invoke `ChatAnthropic` with the configured model

#### Scenario: Agent uses Mistral

- **WHEN** `llm_provider` is set to `mistral` and a user sends a message
- **THEN** the main agent SHALL invoke `ChatMistralAI` with the configured model

#### Scenario: Anthropic API key missing

- **WHEN** `llm_provider` is `anthropic` and `ANTHROPIC_API_KEY` is not set
- **THEN** the agent SHALL log an error and return a clear error message to the user

#### Scenario: Agent factory uses supported LangGraph prompt parameter

- **WHEN** the agent is created with the assembled system prompt
- **THEN** `create_react_agent` SHALL be called without unsupported keyword arguments
- **THEN** the assembled system prompt SHALL be provided to the LangGraph agent

#### Scenario: Conversation context preserved across messages

- **WHEN** a user sends message A, then sends message B
- **THEN** the agent SHALL have access to the context from message A when processing message B

#### Scenario: User thread_id is based on tg_id

- **WHEN** the same Telegram user sends multiple messages
- **THEN** all messages SHALL use `str(user.tg_id)` as the LangGraph `thread_id`

### Requirement: /restart command shall clear conversation history

The bot SHALL support a `/restart` command.

The `/restart` command SHALL clear the user's conversation history so the next message starts a fresh conversation.

The `/restart` command SHALL send the active welcome message to the user and persist it to dialogue history.

#### Scenario: User sends /restart

- **WHEN** a user sends `/restart`
- **THEN** the user's conversation history SHALL be cleared
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context

### Requirement: /start command shall clear conversation history

The `/start` command SHALL clear the user's conversation history before sending the welcome message.

The `/start` command SHALL send the active welcome message to the user and persist it to dialogue history.

#### Scenario: User sends /start with existing history

- **WHEN** a user with existing conversation history sends `/start`
- **THEN** the conversation history SHALL be cleared
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context

#### Scenario: First /start

- **WHEN** a new user sends `/start` for the first time
- **THEN** the active welcome message SHALL be sent to the user
- **THEN** the welcome message SHALL be recorded in dialogue history as an assistant message
- **THEN** the next message SHALL start with the welcome message in LLM context

### Requirement: Tools shall be defined in code, not in admin panel

The system SHALL NOT allow admins to create arbitrary executable tools from the web UI. Admin panel can only edit natural language usage instructions.

#### Scenario: Admin changes tools instruction

- **WHEN** a tool exists in code and admin changes tools instruction
- **THEN** agent behavior may change but executable implementation SHALL remain unchanged

### Requirement: Tool calls shall be logged

The system SHALL log every tool call to `tool_call_logs` with: `trace_id`, `user_tg_id`, `tool_name`, `tool_input` (JSONB), `tool_output`, `status`, `error`, `duration_ms`, `created_at`.

#### Scenario: Tool call logged to DB

- **WHEN** the agent invokes a tool and the tool call completes
- **THEN** a row SHALL be inserted into `tool_call_logs`

### Requirement: Agent requests shall have trace IDs

Every user message processed by the agent SHALL have a unique trace ID (UUID4). Trace ID SHALL be included in: application logs, tool call logs, censor runs, admin notifications, and LangSmith metadata.

#### Scenario: Trace ID propagated through request

- **WHEN** a user sends a message and the agent processes it
- **THEN** a unique trace_id SHALL be generated and included in all logs and DB records for that request

### Requirement: Template shall include a mandatory `send_to_admin` tool

The system SHALL provide `send_to_admin` registered out of the box without additional developer configuration.

**LLM-facing signature:** `send_to_admin(comment: str)`. The LLM passes only `comment`. All Telegram user data is attached server-side: `tg_id`, `first_name`, `last_name`, `username`, `telegram_link` (derived from username), `language_code`, `trace_id`, timestamp.

After sending the notification message, the tool SHALL additionally generate and send a markdown file containing the user's full dialogue history.

#### Scenario: Agent calls `send_to_admin`

- **WHEN** the LangChain agent invokes `send_to_admin(comment="...")`
- **THEN** the tool SHALL attach all user fields server-side
- **THEN** the tool SHALL send a formatted notification to the admin chat
- **THEN** the tool SHALL send a `.md` file with the user's full dialogue history

#### Scenario: ADMIN_TELEGRAM_CHAT_ID is not configured

- **WHEN** `ADMIN_TELEGRAM_CHAT_ID` is empty and the agent invokes `send_to_admin`
- **THEN** the tool SHALL save the notification to `admin_notifications` table without breaking the conversation
- **THEN** return a success confirmation to the agent

#### Scenario: ADMIN_TELEGRAM_CHAT_ID is configured

- **WHEN** `ADMIN_TELEGRAM_CHAT_ID` is set and the agent invokes `send_to_admin`
- **THEN** the tool SHALL send the formatted message to that Telegram chat via Bot API
- **THEN** the tool SHALL send a `.md` file attachment with the user's full dialogue history
- **THEN** also save the notification record to `admin_notifications` with `delivered = TRUE`

#### Scenario: User has no username

- **WHEN** a Telegram user without a `username` invokes `send_to_admin`
- **THEN** `telegram_link` SHALL be `null` in the notification payload

#### Scenario: Tool is registered by default

- **WHEN** a new assistant project is created from the template and the bot starts
- **THEN** `send_to_admin` SHALL already be registered in the LangChain agent

#### Scenario: LLM does not generate user data

- **WHEN** the `send_to_admin` tool is invoked and the LLM constructs the tool call
- **THEN** the LLM SHALL only supply the `comment` argument
- **THEN** all user identity fields SHALL be injected server-side

#### Scenario: Tool call is logged

- **WHEN** `send_to_admin` is invoked and the tool completes
- **THEN** the call SHALL be logged to `tool_call_logs`
- **THEN** the notification record SHALL be persisted in `admin_notifications`

