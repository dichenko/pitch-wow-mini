## Context

The project uses a factory pattern (`llm_factory.py`) to create LLM instances based on provider name and model. Two providers exist: `openai` (via `langchain-openai`) and `anthropic` (via `langchain-anthropic`). Settings for provider/model selection are stored in the `app_settings` DB table and managed through the admin panel (`/admin/settings`). Env vars provide API keys and default model names.

## Goals / Non-Goals

**Goals:**
- Add `mistral` as a third provider in `create_llm()` factory function
- Allow admin to select Mistral + model for main agent and censor independently
- Follow the same pattern as existing providers (env var for API key, DB setting for model)
- No database migration needed — provider and model values are string-based settings

**Non-Goals:**
- Multi-provider fallback chains
- Provider-specific temperature or parameter tuning per provider
- Custom base URL for Mistral (uses official API endpoint)

## Decisions

**1. Use `langchain-mistralai` (`ChatMistralAI`) over raw Mistral SDK**

Rationale: Consistent with existing pattern (ChatOpenAI, ChatAnthropic). LangChain integration handles message formatting, streaming, and tool calling automatically.

**2. Add Mistral API key via env var `MISTRAL_API_KEY`**

Rationale: Follows existing convention (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Env vars are already in `BotSettings` model with case-insensitive mapping.

**3. Add Mistral API key to `llm_factory.py` error message on missing key**

Current code uses `ValueError` with a clear message when API key is missing. Mistral follows the same pattern.

**4. No `MISTRAL_BASE_URL` env var**

Rationale: Mistral's API is a single endpoint (`api.mistral.ai`). Unlike OpenAI, there are no common alternative/compatible endpoints. Can be added later if needed.

## Risks / Trade-offs

- [Risk] `langchain-mistralai` version compatibility with existing `langchain==0.3.7` → Mitigation: Pin to compatible version. Check versions used in similar langchain setups.
- [Risk] Mistral API key leak in logs → Mitigation: Key read from env var, never logged. Same pattern as OpenAI/Anthropic.
