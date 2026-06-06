## 1. Dependencies

- [x] 1.1 Add `langchain-mistralai` to `apps/bot/requirements.txt` (compatible with `langchain==0.3.7`)

## 2. Config

- [x] 2.1 Add `mistral_api_key` and `mistral_model` fields to `BotSettings` in `apps/bot/app/config.py`

## 3. LLM Factory

- [x] 3.1 Add `mistral` case to `create_llm()` in `apps/bot/app/services/llm_factory.py` using `ChatMistralAI`
- [x] 3.2 Handle missing `MISTRAL_API_KEY` with clear `ValueError`

## 4. Admin Settings UI

- [x] 4.1 Add `<option value="mistral">Mistral</option>` to both provider dropdowns in `apps/admin/app/templates/settings/settings.html`

## 5. Verify

- [x] 5.1 Push to master, wait for CI/CD, verify Mistral appears in admin settings page as provider option
