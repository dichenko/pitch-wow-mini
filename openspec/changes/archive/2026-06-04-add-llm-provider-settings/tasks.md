## 1. Dependencies and Configuration

- [x] 1.1 Add `langchain-anthropic` to bot Dockerfile requirements
- [x] 1.2 Add `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` to `.env.example`
- [x] 1.3 Add Anthropic env vars to `apps/bot/app/config.py` (BotSettings)
- [x] 1.4 Add Anthropic env vars to `apps/admin/app/config.py` (AdminSettings) for display

## 2. LLM Factory

- [x] 2.1 Create `create_llm(provider, model, temperature)` factory in `apps/bot/app/services/llm_factory.py`
- [x] 2.2 Implement `ChatOpenAI` path (existing logic) with `openai_api_key`, `openai_base_url`
- [x] 2.3 Implement `ChatAnthropic` path using `langchain_anthropic.ChatAnthropic` with `ANTHROPIC_API_KEY`
- [x] 2.4 Handle missing API key: log error, raise clear exception

## 3. Settings Service

- [x] 3.1 Create `apps/bot/app/services/settings_service.py` with:
  - `get_llm_provider()` → `app_settings.llm_provider` or `"openai"`
  - `get_llm_model()` → `app_settings.llm_model` or `OPENAI_TEXT_MODEL`
  - `get_censor_provider()` → `app_settings.censor_provider` or `"openai"`
  - `get_censor_model()` → `app_settings.censor_model` or `OPENAI_TEXT_MODEL`
  - `save_llm_settings(provider, model, censor_provider, censor_model, admin_id)`
- [x] 3.2 Implement fallback to `.env` defaults when settings not in DB

## 4. Admin Settings Router

- [x] 4.1 Create `apps/admin/app/routers/settings.py` with `GET /admin/settings`
- [x] 4.2 Settings page SHALL show current values for all 4 settings
- [x] 4.3 Settings page SHALL have dropdown for provider + text input for model for both agents
- [x] 4.4 `POST /admin/settings/save` to persist settings
- [x] 4.5 Enforce `require_role(request, "write")` for save
- [x] 4.6 CSRF protection on POST
- [x] 4.7 Log audit event `settings.updated` with changed keys in metadata

## 5. Admin Templates

- [x] 5.1 Create `apps/admin/app/templates/settings/settings.html` template
- [x] 5.2 Add "Settings" link to `apps/admin/app/templates/base.html` navigation sidebar

## 6. Router Registration

- [x] 6.1 Register settings router in `apps/admin/app/main.py`
- [x] 6.2 Ensure auth middleware protects `/admin/settings` routes

## 7. Agent Integration

- [x] 7.1 Modify `apps/bot/app/agent/agent.py`: replace hardcoded `ChatOpenAI` with `create_llm(provider, model, 0.7)`
- [x] 7.2 Read provider/model from settings service at agent creation time
- [x] 7.3 Modify `apps/bot/app/services/censor_service.py`: replace hardcoded `ChatOpenAI` with `create_llm(provider, model, 0.3)`
- [x] 7.4 Read censor provider/model from settings service at censor invocation time

## 8. Testing

- [x] 8.1 Test settings default to `openai` when no DB entries exist
- [x] 8.2 Test settings save and read from `app_settings`
- [x] 8.3 Test agent uses `ChatAnthropic` when `llm_provider=anthropic`
- [x] 8.4 Test censor uses separate provider from main agent
- [x] 8.5 Test fallback to `.env` when DB setting is missing
- [x] 8.6 Test `ANTHROPIC_API_KEY` missing error handling
- [x] 8.7 Test read admin cannot edit settings
- [x] 8.8 Test audit event `settings.updated` is logged
- [x] 8.9 Test CSRF enforcement on settings save
