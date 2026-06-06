## MODIFIED Requirements

### Requirement: Bot shall use LangGraph ReAct agent with registered tools

The system SHALL use a LangGraph ReAct agent (`create_react_agent`) with a configurable LLM provider and database-backed recent dialogue history for multi-turn conversation continuity.

Supported providers: OpenAI (`ChatOpenAI`), Anthropic (`ChatAnthropic`), and Mistral (`ChatMistralAI`).

Four tools registered: `send_to_admin` (REQUIRED), `save_lead` (stub), `get_project_knowledge` (reads knowledge file), `create_followup_task` (stub).

LLM provider and model SHALL be read from `app_settings` (`llm_provider`, `llm_model`), falling back to `.env` defaults. Temperature SHALL be 0.7.

Provider-specific configuration:

- **OpenAI**: uses `OPENAI_API_KEY`, `OPENAI_BASE_URL` from `.env`
- **Anthropic**: uses `ANTHROPIC_API_KEY` from `.env`
- **Mistral**: uses `MISTRAL_API_KEY` from `.env`

Before each LLM request related to a user message, the system SHALL load up to `llm_history_messages` latest dialogue records for the current Telegram user and current thread ID. One dialogue record SHALL mean one user question plus the final assistant response sent to the user. The system SHALL include those records as prior chat messages before the current user message.

The agent SHALL use the current `thread_id` based on the Telegram user ID and reset counter. Each user SHALL have isolated history. `/start` and `/restart` SHALL move the user to a new thread ID so previous-thread history is not included in future LLM requests.

#### Scenario: Bot starts with template tools registered

- **WHEN** a bot starts from the template and the LangChain agent initializes
- **THEN** all four tools SHALL be registered

#### Scenario: Agent uses OpenAI

- **WHEN** `llm_provider` is set to `openai` (or not set) and a user sends a message
- **THEN** the main agent SHALL invoke `ChatOpenAI` with the configured model
- **THEN** recent dialogue history SHALL be included in the request using the common message-building path

#### Scenario: Agent uses Anthropic

- **WHEN** `llm_provider` is set to `anthropic` and a user sends a message
- **THEN** the main agent SHALL invoke `ChatAnthropic` with the configured model
- **THEN** recent dialogue history SHALL be included in the request using the common message-building path

#### Scenario: Agent uses Mistral

- **WHEN** `llm_provider` is set to `mistral` and a user sends a message
- **THEN** the main agent SHALL invoke `ChatMistralAI` with the configured model
- **THEN** recent dialogue history SHALL be included in the request using the common message-building path

#### Scenario: Anthropic API key missing

- **WHEN** `llm_provider` is `anthropic` and `ANTHROPIC_API_KEY` is not set
- **THEN** the agent SHALL log an error and return a clear error message to the user

#### Scenario: Conversation context preserved across messages

- **WHEN** a user sends message A and receives response A, then sends message B
- **THEN** the LLM request for message B SHALL include message A and response A as prior chat messages

#### Scenario: History window is limited by setting

- **WHEN** `llm_history_messages` is `20` and the user has more than 20 completed dialogue records in the current thread
- **THEN** the LLM request SHALL include only the latest 20 dialogue records before the current user message

#### Scenario: History can be disabled

- **WHEN** `llm_history_messages` is `0`
- **THEN** the LLM request SHALL include no prior dialogue records from the database
- **THEN** the current user message SHALL still be processed

#### Scenario: Censor receives same recent history

- **WHEN** censor is enabled and a user message produces a draft response
- **THEN** the censor LLM request SHALL include the same recent dialogue records for the current user and thread
- **THEN** the censor SHALL still receive the current user message and draft response

#### Scenario: User thread_id is based on tg_id

- **WHEN** the same Telegram user sends multiple messages without reset
- **THEN** all messages SHALL use `str(user.tg_id)` as the LangGraph `thread_id`

#### Scenario: Reset excludes previous-thread history

- **WHEN** a user sends `/restart` or `/start` after existing dialogue history
- **THEN** the user's next message SHALL use a new thread ID
- **THEN** previous-thread dialogue records SHALL NOT be included in that next LLM request
