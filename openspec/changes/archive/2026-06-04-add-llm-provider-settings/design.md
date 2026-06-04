## Context

The template currently hardcodes `ChatOpenAI` for both the main LangChain agent (`agent.py`) and the censor/reviewer pass (`censor_service.py`). LLM provider and model are set via `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_TEXT_MODEL`). There is no mechanism to switch to Anthropic Claude without code changes, and no way to use different providers for the main agent vs censor.

The admin panel has no settings page — only prompt management, censor toggle, and admin management.

## Goals / Non-Goals

**Goals:**
- Support Anthropic Claude via `langchain-anthropic` as an alternative LLM provider
- Allow admin to select provider and model independently for main agent and censor
- Provide a Settings page in the admin panel at `/admin/settings`
- Store selections in `app_settings` table; fall back to `.env` defaults when not set
- Zero impact on existing deployments after migration (OpenAI remains default)
- Both agents dynamically resolve provider at invocation time

**Non-Goals:**
- Do NOT support custom/base URL for Anthropic (use official API only)
- Do NOT add provider selection for voice STT (stays OpenAI/Aisha)
- Do NOT support other LLM providers beyond OpenAI and Anthropic in this change
- Do NOT add per-user or per-conversation provider switching
- Do NOT change LangSmith tracing logic

## Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Store settings as `app_settings` rows (not new table) | `app_settings` already exists for `censor_enabled`; key-value is sufficient for provider/model pairs. No migration needed. |
| 2 | Settings keys: `llm_provider`, `llm_model`, `censor_provider`, `censor_model` | Separate keys for main agent and censor allow independent selection. Clear naming. |
| 3 | Factory function `create_llm(provider: str, model: str)` in shared code | Single place for provider instantiation logic. Returns `ChatOpenAI` or `ChatAnthropic`. Easy to extend. |
| 4 | Read settings from DB at request time with session-level cache | Avoids stale settings for long-running agent sessions. Lightweight with async DB. |
| 5 | `ChatAnthropic` via `langchain-anthropic` package | Official LangChain integration. API key via `ANTHROPIC_API_KEY` env var. |
| 6 | Settings page: one form with two sections (Main Agent / Censor) | Compact UX. All settings on one page — no tab switching needed for 4 fields. |
| 7 | `write` and `superadmin` can edit settings; `read` can view | Follows existing role model (same as prompt editing permission). |
| 8 | Audit `settings.updated` event when settings are saved | Follows existing audit pattern for traceability. |
| 9 | Env vars `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` added to `.env.example` and config | API key stays in `.env` (security). Model name has sensible default. |
| 10 | Dropdown options: `openai` / `anthropic` | Simple select. Can be extended to enum in future. |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| DB read on every agent invocation adds latency | `app_settings` table is tiny (few rows); indexed by PK. Negligible overhead. |
| Anthropic API key missing causes runtime failure | On startup, validate that configured provider's API key is set. If missing, log warning; agent falls back gracefully with clear error to user. |
| Censor model not available on chosen provider | Admin selects model name manually; validation of model availability is out of scope. Admin is responsible for correct model name. |
| Existing deployments have no `llm_provider` setting | Fallback: if setting missing, use `openai` with `OPENAI_TEXT_MODEL`. Existing behavior unchanged. |
