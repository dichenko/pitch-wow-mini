## Why

The project currently supports only OpenAI and Anthropic as LLM providers. Adding Mistral as a third option gives admins more flexibility in choosing cost-effective models, enables multi-provider failover strategies, and leverages Mistral's strong performance for multilingual use cases.

## What Changes

- Add Mistral AI provider support to `llm_factory.py` using `langchain-mistralai`
- Add `MISTRAL_API_KEY` and `MISTRAL_MODEL` environment variables
- Add Mistral option to the admin settings page provider dropdowns (main agent + censor)
- Add `langchain-mistralai` to bot service dependencies

## Capabilities

### New Capabilities

- `mistral-provider`: Add Mistral AI as a third LLM provider option for the main agent and censor, selectable from the admin settings panel

### Modified Capabilities

- `admin-settings`: Provider dropdowns now include Mistral option alongside OpenAI and Anthropic

## Impact

- `apps/bot/app/services/llm_factory.py` — new `mistral` case in `create_llm`
- `apps/bot/app/config.py` — new `MISTRAL_API_KEY`, `MISTRAL_MODEL` fields
- `apps/bot/requirements.txt` — add `langchain-mistralai`
- `apps/admin/app/templates/settings/settings.html` — add Mistral provider option
- `.env.example` — already has Mistral section (no env changes needed)
