## ADDED Requirements

### Requirement: Mistral AI shall be available as an LLM provider

The system SHALL support Mistral AI as a third LLM provider option for both the main agent and the censor agent.

#### Scenario: Mistral configurable for main agent

- **WHEN** admin sets `llm_provider` to `mistral` and provides a Mistral model name (e.g. `mistral-large`) via the admin settings page
- **THEN** the main agent SHALL use Mistral AI for processing user messages

#### Scenario: Mistral configurable for censor

- **WHEN** admin sets `censor_provider` to `mistral` and provides a Mistral model name via the admin settings page
- **THEN** the censor agent SHALL use Mistral AI for reviewing responses

### Requirement: Mistral API key shall be provided via environment variable

The system SHALL read the Mistral API key from the `MISTRAL_API_KEY` environment variable.

#### Scenario: Missing API key raises error

- **WHEN** the LLM factory is asked to create a Mistral instance and `MISTRAL_API_KEY` is not set
- **THEN** the system SHALL raise a `ValueError` with a clear message indicating the key is missing

#### Scenario: Valid API key uses Mistral

- **WHEN** `MISTRAL_API_KEY` is set and provider is `mistral`
- **THEN** the system SHALL create a `ChatMistralAI` LangChain instance with the configured model and API key

### Requirement: Mistral provider shall use langchain-mistralai integration

The system SHALL use `langchain-mistralai` package with `ChatMistralAI` class to interface with the Mistral API.

#### Scenario: Factory creates Mistral LLM

- **WHEN** `create_llm(provider="mistral", model="mistral-large")` is called
- **THEN** a `ChatMistralAI` instance SHALL be returned with the specified model and temperature
