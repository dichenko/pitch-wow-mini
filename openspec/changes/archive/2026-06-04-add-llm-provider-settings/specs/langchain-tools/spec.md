## MODIFIED Requirements

### Requirement: Bot shall use LangGraph ReAct agent with registered tools

The system SHALL use a LangGraph ReAct agent (`create_react_agent`) with a configurable LLM provider.

Supported providers: OpenAI (`ChatOpenAI`) and Anthropic (`ChatAnthropic`).

Four tools registered: `send_to_admin` (REQUIRED), `save_lead` (stub), `get_project_knowledge` (reads knowledge file), `create_followup_task` (stub).

LLM provider and model SHALL be read from `app_settings` (`llm_provider`, `llm_model`), falling back to `.env` defaults (`OPENAI_API_KEY`, `OPENAI_TEXT_MODEL`). Temperature SHALL be 0.7.

Provider-specific configuration:

- **OpenAI**: uses `OPENAI_API_KEY`, `OPENAI_BASE_URL` from `.env`
- **Anthropic**: uses `ANTHROPIC_API_KEY` from `.env`

#### Scenario: Bot starts with template tools registered

- **WHEN** a bot starts from the template and the LangChain agent initializes
- **THEN** all four tools SHALL be registered

#### Scenario: Agent uses OpenAI

- **WHEN** `llm_provider` is set to `openai` (or not set) and a user sends a message
- **THEN** the main agent SHALL invoke `ChatOpenAI` with the configured model

#### Scenario: Agent uses Anthropic

- **WHEN** `llm_provider` is set to `anthropic` and a user sends a message
- **THEN** the main agent SHALL invoke `ChatAnthropic` with the configured model

#### Scenario: Anthropic API key missing

- **WHEN** `llm_provider` is `anthropic` and `ANTHROPIC_API_KEY` is not set
- **THEN** the agent SHALL log an error and return a clear error message to the user
