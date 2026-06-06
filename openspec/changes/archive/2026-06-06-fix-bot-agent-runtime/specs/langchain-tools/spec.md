## MODIFIED Requirements

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
