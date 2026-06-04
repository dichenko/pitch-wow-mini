# Tasks: create-ai-assistant-template

## Phase 1: Repository Structure and Configuration

### 1.1 Repository Layout

- [x] Create directory structure:
  - [x] `apps/bot/app/agent/tools/`
  - [x] `apps/bot/app/handlers/`
  - [x] `apps/bot/app/services/`
  - [x] `apps/bot/app/db/repositories/`
  - [x] `apps/admin/app/routers/`
  - [x] `apps/admin/app/templates/`
  - [x] `apps/admin/app/services/`
  - [x] `apps/admin/app/db/`
  - [x] `packages/shared/models/`
  - [x] `packages/shared/schemas/`
  - [x] `packages/shared/utils/`
  - [x] `infra/`
  - [x] `migrations/versions/`
  - [x] `scripts/`
  - [x] `openspec/`
- [x] Add `__init__.py` files for all Python packages.
- [x] Remove hardcoded dental-clinic names from template.
- [x] Add sample project knowledge file for demo assistant.

### 1.2 Environment Configuration

- [x] Create `.env.example` with all required variables:
  - [x] `APP_ENV`, `APP_TIMEZONE`
  - [x] `PROJECT_SLUG`, `COMPOSE_PROJECT_NAME`
  - [x] `BOT_PUBLIC_URL`, `ADMIN_PUBLIC_URL`
  - [x] `BOT_HOST_PORT`, `ADMIN_HOST_PORT`
  - [x] `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `BOT_MODE`
  - [x] `ROOT_ADMIN_TG_ID`, `ADMIN_LOGIN_TOKEN_TTL_MINUTES`
  - [x] `ADMIN_TELEGRAM_CHAT_ID`
  - [x] `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - [x] `TEXT_LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_TEXT_MODEL`
  - [x] `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_ENDPOINT`, `LANGSMITH_PROJECT`, `LANGSMITH_WORKSPACE_ID`, `LANGSMITH_TAGS`, `LANGSMITH_SAMPLE_RATE`
  - [x] `SESSION_SECRET`, `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`
  - [x] `CENSOR_ENABLED`
  - [x] `VOICE_ENABLED`, `VOICE_TEMP_DIR`, `VOICE_MAX_AUDIO_SIZE_MB`, `VOICE_MAX_DURATION_SEC`
  - [x] `OPENAI_STT_MODEL`, `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS`
  - [x] `AISHA_API_KEY`, `AISHA_BASE_URL`, `AISHA_STT_TIMEOUT_MS`, `AISHA_STT_LANGUAGE`
- [x] Create `config.py` with Pydantic Settings for bot service.
- [x] Create `config.py` with Pydantic Settings for admin service.

## Phase 2: Database and Migrations

### 2.1 SQLAlchemy Models

- [x] Create shared models in `packages/shared/models/`:
  - [x] `admins` table model.
  - [x] `admin_login_tokens` table model.
  - [x] `prompt_versions` table model.
  - [x] `admin_audit_log` table model.
  - [x] `tool_call_logs` table model (optional).
- [x] Create async database session factory.

### 2.2 Alembic Migrations

- [x] Initialize Alembic in `migrations/`.
- [x] Create migration for `admins` table with indexes on `tg_id`.
- [x] Create migration for `admin_login_tokens` table with indexes on `token_hash`, `expires_at`.
- [x] Create migration for `prompt_versions` table with:
  - [x] `UNIQUE(kind, version_number)` constraint.
  - [x] Partial unique index for active version per kind.
  - [x] Index on `kind`.
- [x] Create migration for `admin_audit_log` table with indexes on `admin_id`, `created_at`.
- [x] Create migration for `admin_notifications` table with index on `trace_id`, `created_at`.
- [x] Create migration for `censor_runs` table with index on `trace_id`, `created_at`.
- [x] Create migration for `app_settings` table.
- [x] Add `censor_prompt` to `prompt_versions.kind` CHECK constraint.
- [x] Create migration for `tool_call_logs` table (optional).

### 2.3 Seed Data

- [x] Add default system prompt seed.
- [x] Add default tools instruction seed.
- [x] Add default censor prompt seed.
- [x] Add sample project knowledge file.
- [x] Implement seed-on-first-startup logic.

## Phase 3: Docker and Infrastructure

### 3.1 Docker Compose

- [x] Create `infra/docker-compose.yml`:
  - [x] `bot` service with build context `../apps/bot`, port binding `127.0.0.1:${BOT_HOST_PORT}:8000`.
  - [x] `admin` service with build context `../apps/admin`, port binding `127.0.0.1:${ADMIN_HOST_PORT}:8080`.
  - [x] `postgres` service with `postgres:16-alpine`, healthcheck, project-scoped volume.
  - [x] `depends_on` with `condition: service_healthy` for postgres.
  - [x] `restart: unless-stopped` for all services.
- [x] Add healthchecks for bot and admin services.

### 3.2 Dockerfiles

- [x] Create `apps/bot/Dockerfile` with Python 3.12, dependencies, entrypoint.
- [x] Create `apps/admin/Dockerfile` with Python 3.12, dependencies, entrypoint.

### 3.3 Caddy Example

- [x] Create `infra/Caddyfile.example`:
  - [x] Bot domain reverse proxy to `127.0.0.1:18001`.
  - [x] Admin domain reverse proxy to `127.0.0.1:18002`.
  - [x] Comments explaining host-level Caddy setup.

### 3.4 Init Script

- [x] Create `scripts/init_project_env.py`:
  - [x] Copy `.env.example` to `.env` if `.env` does not exist.
  - [x] Generate `PROJECT_SLUG` if missing.
  - [x] Generate random free `BOT_HOST_PORT`.
  - [x] Generate random free `ADMIN_HOST_PORT`.
  - [x] Generate `SESSION_SECRET`.
  - [x] Print Caddyfile snippet for the new project.

## Phase 4: Bot Service — Core

### 4.1 Bot Setup

- [x] Create `apps/bot/app/main.py` with aiogram 3 bot initialization.
- [x] Add health endpoint `GET /health` via FastAPI (if webhook mode) or separate health check.
- [x] Support `BOT_MODE=polling` and `BOT_MODE=webhook`.
- [x] Add structured JSON logging.

### 4.2 Root Admin Bootstrap

- [x] On startup, read `ROOT_ADMIN_TG_ID` from config.
- [x] Check if `admins` table contains this `tg_id`.
- [x] If not, insert with role `superadmin`.
- [x] If exists with different role, treat as `superadmin` regardless of DB value.

### 4.3 `/admin` Command Handler

- [x] Create `apps/bot/app/handlers/admin.py`.
- [x] Check if user is root admin or active admin in DB.
- [x] If not admin, deny access with clear message.
- [x] If admin:
  - [x] Generate secure random token (`secrets.token_urlsafe(32)`).
  - [x] Hash token with SHA-256.
  - [x] Store token hash with expiration in `admin_login_tokens`.
  - [x] Send `ADMIN_PUBLIC_URL/admin/login?token=<raw_token>` to Telegram user.
- [x] Log audit event `admin.login_link_created`.

### 4.4 Message Handler

- [x] Create `apps/bot/app/handlers/message.py`.
- [x] Generate `trace_id` for each user message.
- [x] Load conversation history (if applicable).
- [x] Assemble prompt via prompt assembler.
- [x] Invoke LangChain agent.
- [x] Log agent run with trace_id.
- [x] Send response to user.

## Phase 5: Prompt Assembly and Versioning

### 5.1 Prompt Assembler

- [x] Create `apps/bot/app/agent/prompt_assembler.py`.
- [x] Load `core_guardrails.md` from file (non-editable).
- [x] Load active `system_prompt` from DB.
- [x] Load active `tools_instruction` from DB.
- [x] Concatenate in order:
  ```
  <core guardrails>
  
  <active system prompt>
  
  # Tools usage instruction
  
  <active tools instruction>
  ```
- [x] Add fallback defaults if DB is empty.
- [x] Compute `assembled_prompt_hash` for LangSmith metadata.

### 5.2 Prompt Service

- [x] Create `apps/bot/app/services/prompt_service.py` (or shared).
- [x] `get_active_system_prompt()` — returns active version.
- [x] `get_active_tools_instruction()` — returns active version.
- [x] `get_prompt_versions(kind, limit=3)` — returns last N versions.
- [x] `create_prompt_version(kind, content, admin_id, change_note)` — creates new version, marks active.
- [x] `restore_prompt_version(kind, source_version_id, admin_id)` — creates new version copied from source.

### 5.3 Core Guardrails

- [x] Create `apps/bot/app/agent/core_guardrails.md` with:
  - [x] Prohibition of disclosing secrets.
  - [x] Prohibition of executing arbitrary admin instructions that break security.
  - [x] Personal data handling rules.
  - [x] General tool usage policy.
  - [x] Rule not to fabricate tool call results.

## Phase 6: LangChain Agent and Tools

### 6.1 Agent Definition

- [x] Create `apps/bot/app/agent/agent.py`.
- [x] Define LangChain agent with tool calling.
- [x] Accept assembled prompt as system message.
- [x] Configure LLM provider and model from settings.
- [x] Add LangSmith metadata and tags to agent config.

### 6.2 Template Tools

- [x] Create `apps/bot/app/agent/tools/send_to_admin.py` — REQUIRED default tool:
  - [x] Define LLM-facing signature: `send_to_admin(comment: str)`.
  - [x] Accept only `comment` from LLM; reject any other arguments.
  - [x] On invocation, automatically attach user data from the current Telegram context:
    - [x] `tg_id`
    - [x] `first_name` (if available)
    - [x] `last_name` (if available)
    - [x] `username` (if available)
    - [x] `telegram_link` = `https://t.me/<username>` (only if username exists)
    - [x] `language_code` (if available)
    - [x] current `trace_id` from request context
    - [x] timestamp of the request
  - [x] Send formatted notification (comment + user data) to `ADMIN_TELEGRAM_CHAT_ID` via Bot API.
  - [x] If `ADMIN_TELEGRAM_CHAT_ID` is not set, save notification to `admin_notifications` table and do NOT break conversation.
  - [x] Always save notification record to `admin_notifications` table regardless of delivery method.
  - [x] Log the tool call with trace_id.
- [x] Create `apps/bot/app/agent/tools/save_lead.py` — stub implementation.
- [x] Create `apps/bot/app/agent/tools/get_project_knowledge.py` — reads from knowledge file.
- [x] Create `apps/bot/app/agent/tools/create_followup_task.py` — stub implementation.
- [x] Register all tools in `tools/__init__.py`, with `send_to_admin` marked as always-registered.
- [x] Add clear pattern for adding new tools.

### 6.3 Tool Call Logging

- [x] Log every tool call to `tool_call_logs` table:
  - [x] `trace_id`, `user_tg_id`, `tool_name`, `tool_input`, `tool_output`, `status`, `error`, `duration_ms`, `created_at`.
- [x] Include `trace_id` in all application logs for the request.

## Phase 7: LangSmith Observability

### 7.1 LangSmith Configuration

- [x] Add LangSmith dependencies to requirements.
- [x] Configure LangSmith from env variables:
  - [x] `LANGSMITH_TRACING`
  - [x] `LANGSMITH_API_KEY`
  - [x] `LANGSMITH_ENDPOINT`
  - [x] `LANGSMITH_PROJECT` (default: `PROJECT_SLUG`)
  - [x] `LANGSMITH_WORKSPACE_ID`
  - [x] `LANGSMITH_TAGS`
  - [x] `LANGSMITH_SAMPLE_RATE`
- [x] When `LANGSMITH_TRACING=false`, app works without LangSmith API key.

### 7.2 Trace Metadata

- [x] Add metadata to every agent run:
  - [x] `trace_id`
  - [x] `project_slug`
  - [x] `app_env`
  - [x] `telegram_user_id`
  - [x] `telegram_username`
  - [x] `bot_mode`
  - [x] `system_prompt_version`
  - [x] `tools_instruction_version`
  - [x] `assembled_prompt_hash`
  - [x] `llm_provider`
  - [x] `llm_model`
- [x] Add tags:
  - [x] `project:<PROJECT_SLUG>`
  - [x] `env:<APP_ENV>`
  - [x] `channel:telegram`
  - [x] `bot-mode:<BOT_MODE>`
  - [x] Additional tags from `LANGSMITH_TAGS`.

### 7.3 Secret Protection

- [x] Ensure secrets are NOT sent to LangSmith:
  - [x] No API keys in metadata/tags/inputs/outputs.
  - [x] No cookies, admin tokens, DB credentials.
  - [x] Filter tool inputs/outputs for secret patterns.

### 7.4 Graceful Degradation

- [x] Wrap LangSmith calls in try/except.
- [x] Log tracing errors locally.
- [x] Continue conversation if LangSmith is unavailable.
- [x] Store last tracing error for debug page.

## Phase 7.5: Censor / Response Reviewer

### 7.5.1 Censor Service

- [x] Create `apps/bot/app/services/censor_service.py`.
- [x] Implement censor LLM call:
  - [x] Accept draft response, original user message, trace_id.
  - [x] Load active censor prompt from DB (`kind = censor_prompt`).
  - [x] Call LLM with censor prompt + user message + draft.
  - [x] Return final response text.
- [x] Implement censor toggle check:
  - [x] Read `censor_enabled` from `app_settings` table.
  - [x] If disabled, skip censor pass and return draft as-is.
- [x] Implement failure handling:
  - [x] If censor LLM fails, return draft response as fallback.
  - [x] Log error to `censor_runs` with `status='error'`.
  - [x] Do NOT break the user conversation.

### 7.5.2 Censor Logging

- [x] Create `censor_runs` table migration.
- [x] Log every censor run:
  - [x] `trace_id`, `user_tg_id`, `draft_response`, `final_response`.
  - [x] `censor_prompt_version`, `censor_model`.
  - [x] `status` (success/error/skipped), `error`, `duration_ms`.
  - [x] `created_at`.

### 7.5.3 Censor Prompt Management

- [x] Add `censor_prompt` to `prompt_versions.kind` CHECK constraint.
- [x] Extend `prompt_service` to handle `kind = censor_prompt`.
- [x] Seed default censor prompt on first startup.
- [x] Add censor prompt versioning (create, restore) same as system prompt.

### 7.5.4 Censor LangSmith Integration

- [x] When `LANGSMITH_TRACING=true` and censor is enabled:
  - [x] Censor LLM call appears as child span in same trace.
  - [x] Metadata includes: `trace_id`, `censor_enabled`, `censor_prompt_version`, `main_agent_run_id`.
- [x] When censor is disabled:
  - [x] No censor LLM call in LangSmith trace.
- [x] Censor errors logged in LangSmith metadata without secrets.

## Phase 7.6: Voice Recognition Pipeline

### 7.6.1 STT Provider Interface

- [x] Create `apps/bot/app/services/stt/base.py` — abstract STT provider interface.
- [x] Define method: `transcribe(audio_path: str) -> Optional[str]`.
- [x] Implement `OpenAISttProvider` in `apps/bot/app/services/stt/openai_stt.py`:
  - [x] Use `OPENAI_STT_MODEL` (default: `gpt-4o-transcribe`).
  - [x] Configure `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS`.
- [x] Implement `AishaSttProvider` in `apps/bot/app/services/stt/aisha_stt.py`:
  - [x] Use `AISHA_BASE_URL`, `AISHA_API_KEY`.
  - [x] Configure `AISHA_STT_LANGUAGE` (default: `uz`), `AISHA_STT_TIMEOUT_MS`.
  - [x] Add TODO/mock mode if API format not confirmed without key.

### 7.6.2 Voice Handler

- [x] Create `apps/bot/app/handlers/voice.py`.
- [x] Handle Telegram voice/audio messages when `VOICE_ENABLED=true`.
- [x] Download file via Telegram Bot API.
- [x] Check file size against `VOICE_MAX_AUDIO_SIZE_MB`.
- [x] Check audio duration against `VOICE_MAX_DURATION_SEC`.
- [x] Normalize audio using ffmpeg to standard format.
- [x] Call OpenAI STT (primary).
- [x] If OpenAI fails or returns empty, call Aisha STT (fallback).
- [x] If both fail, send user-friendly failure message.
- [x] If success, process transcribed text as regular message.
- [x] Delete all temp audio files after processing.
- [x] Log voice metadata to message log:
  - [x] `file_id`, duration, MIME type, provider used, detected language, trace_id, transcription status.

### 7.6.3 Voice Configuration

- [x] Add `VOICE_ENABLED`, `VOICE_TEMP_DIR`, `VOICE_MAX_AUDIO_SIZE_MB`, `VOICE_MAX_DURATION_SEC` to config.
- [x] Add `OPENAI_STT_MODEL`, `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS` to config.
- [x] Add `AISHA_API_KEY`, `AISHA_BASE_URL`, `AISHA_STT_TIMEOUT_MS`, `AISHA_STT_LANGUAGE` to config.
- [x] Add voice env vars to `.env.example`.

### 7.6.4 Docker ffmpeg

- [x] Add `ffmpeg` installation to bot Dockerfile.
- [x] Ensure `VOICE_TEMP_DIR` directory exists in container.

## Phase 8: Admin Service — Authentication

### 8.1 Token Login

- [x] Create `apps/admin/app/routers/auth.py`.
- [x] Implement `GET /admin/login?token=...`:
  - [x] Hash incoming token with SHA-256.
  - [x] Find token record in DB.
  - [x] Reject if missing, expired, or already used.
  - [x] Mark token as used (`used_at = now()`).
  - [x] Create signed session cookie.
  - [x] Redirect to `/admin/dashboard`.
- [x] Log audit event `admin.login_success` or `admin.login_failed`.

### 8.2 Session Management

- [x] Implement session middleware with `SESSION_SECRET`.
- [x] Configure cookie: `SESSION_COOKIE_NAME`, `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`.
- [x] Protect all `/admin/*` routes (except `/admin/login`).
- [x] Implement logout: invalidate session, redirect to login info page.

### 8.3 CSRF Protection

- [x] Add CSRF token for POST forms.
- [x] Validate CSRF on all POST requests.

### 8.4 Role Enforcement

- [x] Create dependency/middleware for role checks.
- [x] Enforce permissions based on admin role.
- [x] Always treat `ROOT_ADMIN_TG_ID` as `superadmin`.

## Phase 9: Admin Service — UI Pages

### 9.1 Layout and Dashboard

- [x] Create base Jinja2 template with:
  - [x] Sidebar/nav with links to System Prompt, Tools Instruction, Censor, Administrators, Debug.
  - [x] Current admin identity display.
  - [x] Role badge.
  - [x] Logout button.
- [x] Create dashboard page `/admin/dashboard` with overview.
- [x] Add `/health` endpoint.

### 9.2 System Prompt Page

- [x] Create `apps/admin/app/routers/system_prompt.py`.
- [x] Page `/admin/system-prompt`:
  - [x] Show active system prompt content.
  - [x] Show metadata: version number, saved by, date.
  - [x] Edit form (visible only for `write` and `superadmin`).
  - [x] Change note field (optional).
  - [x] Save creates new version, marks active.
  - [x] Show last 3 previous versions with restore buttons.
  - [x] Restore creates new version copied from selected version.
- [x] Log audit events: `prompt.created`, `prompt.restored`.

### 9.3 Tools Instruction Page

- [x] Create `apps/admin/app/routers/tools_instruction.py`.
- [x] Page `/admin/tools-instruction`:
  - [x] Same behavior as System Prompt page.
  - [x] Store as `kind=tools_instruction`.
- [x] Log audit events: `tools_instruction.created`, `tools_instruction.restored`.

### 9.3.5 Censor Page

- [x] Create `apps/admin/app/routers/censor.py`.
- [x] Page `/admin/censor`:
  - [x] Checkbox: enable/disable censor.
  - [x] Textarea: active censor prompt.
  - [x] Save button: creates new censor prompt version.
  - [x] Show last 3 previous versions with restore buttons.
  - [x] Restore creates new version copied from selected version.
  - [x] Metadata: who/when saved each version.
  - [x] Optional change_note field.
  - [x] Optional preview/test area (stretch goal).
- [x] Persist `censor_enabled` to `app_settings` table.
- [x] Log audit events: `censor_prompt.created`, `censor_prompt.restored`, `censor.toggled`.

### 9.4 Administrators Page

- [x] Create `apps/admin/app/routers/admins.py`.
- [x] Page `/admin/admins`:
  - [x] List all admins with roles, status.
  - [x] Add admin form (visible only to `superadmin`):
    - [x] Telegram ID input.
    - [x] Optional username/display name.
    - [x] Role selector: read/write/superadmin.
  - [x] Deactivate/delete admin (only `superadmin`).
  - [x] Change role (only `superadmin`).
  - [x] Prevent removing root admin accidentally.
- [x] Log audit events: `admin.created`, `admin.role_changed`, `admin.deactivated`.

### 9.5 Debug Page

- [x] Create `apps/admin/app/routers/debug.py`.
- [x] Page `/admin/debug`:
  - [x] App version / git commit (if available).
  - [x] Active system prompt version.
  - [x] Active tools instruction version.
  - [x] LLM provider/model.
  - [x] Bot mode.
  - [x] DB connection status.
  - [x] LangSmith status:
    - [x] Tracing enabled/disabled.
    - [x] Project name.
    - [x] Endpoint host.
    - [x] Workspace configured yes/no.
    - [x] Last successful trace timestamp (if available).
    - [x] Last tracing error (if any, without secrets).
  - [x] Censor status:
    - [x] Censor enabled/disabled.
    - [x] Active censor prompt version.
  - [x] send_to_admin status:
    - [x] `ADMIN_TELEGRAM_CHAT_ID` configured yes/no (without revealing the value).
    - [x] Last notification timestamp (if available).
  - [x] Last censor run timestamp and status (if available).
- [x] No secrets displayed.

### 9.6 Preview Assembled Prompt

- [x] Add read-only preview page or section:
  - [x] Show core guardrails + active system prompt + active tools instruction.
  - [x] Helps admin understand final prompt sent to LLM.

## Phase 10: Audit Service

- [x] Create shared audit service.
- [x] Implement `log_audit_event(admin_id, admin_tg_id, action, entity_type, entity_id, metadata, ip_address, user_agent)`.
- [x] Required audit actions:
  - [x] `admin.login_link_created`
  - [x] `admin.login_success`
  - [x] `admin.login_failed`
  - [x] `prompt.created`
  - [x] `prompt.restored`
  - [x] `tools_instruction.created`
  - [x] `tools_instruction.restored`
  - [x] `censor_prompt.created`
  - [x] `censor_prompt.restored`
  - [x] `censor.toggled`
  - [x] `admin.created`
  - [x] `admin.role_changed`
  - [x] `admin.deactivated`

## Phase 11: Tests

- [x] Test admin role permissions (read/write/superadmin).
- [x] Test `/admin` access allowed for admin, denied for non-admin.
- [x] Test token expiration (reject after TTL).
- [x] Test token single-use (reject on reuse).
- [x] Test prompt version creation (new version, old versions preserved).
- [x] Test restore creates new version (source unchanged).
- [x] Test prompt assembly includes guardrails + system prompt + tools instruction.
- [x] Test LangSmith disabled mode works without API key.
- [x] Test LangSmith enabled mode attaches trace_id metadata.
- [x] Test LangSmith tracing failure does not break conversation.
- [x] Test secrets are not included in LangSmith metadata.
- [x] Test non-admin cannot access admin panel.
- [x] Test read admin cannot write.
- [x] Test write admin cannot manage admins.
- [x] Test `send_to_admin` is registered by default on bot startup.
- [x] Test `send_to_admin` attaches all user fields (tg_id, first_name, last_name, username, telegram_link, language_code, trace_id, timestamp).
- [x] Test `send_to_admin` omits `telegram_link` when user has no username.
- [x] Test LLM can only supply `comment` argument to `send_to_admin`.
- [x] Test `send_to_admin` saves to `admin_notifications` when `ADMIN_TELEGRAM_CHAT_ID` not set.
- [x] Test censor enabled/disabled toggle persists in `app_settings`.
- [x] Test censor prompt versioning (create, restore, last 3 versions).
- [x] Test censor LLM failure fallback sends draft response.
- [x] Test censor LLM run logged to `censor_runs`.
- [x] Test censor disabled skips LLM call and returns draft.
- [x] Test voice recognition disabled asks user to send text.
- [x] Test voice recognized by OpenAI → text processed as message.
- [x] Test OpenAI STT fails → Aisha STT fallback succeeds.
- [x] Test both STT providers fail → user-friendly failure message.
- [x] Test audio size exceeds limit → rejection message.
- [x] Test audio duration exceeds limit → rejection message.
- [x] Test temp audio files are deleted after processing.
- [x] Test STT error not exposed to user.

## Phase 12: Documentation

- [x] Update `README.md`:
  - [x] Project overview and purpose.
  - [x] Local development guide.
  - [x] VPS deployment guide.
  - [x] `.env` setup instructions.
  - [x] Port generation and init script usage.
  - [x] Caddy configuration guide.
  - [x] Migrations guide.
  - [x] Telegram bot token setup.
  - [x] Admin login flow explanation.
  - [x] How to create a new assistant from template.
  - [x] How to add a new tool.
  - [x] How admin access works.
  - [x] How prompt versioning works.
  - [x] How to enable LangSmith tracing.
  - [x] How to search LangSmith traces by local trace_id.
  - [x] How to enable and configure censor.
  - [x] How censor prompt versioning works.
  - [x] How to enable voice recognition.
  - [x] How to configure OpenAI STT and Aisha STT fallback.
  - [x] How `send_to_admin` works with `ADMIN_TELEGRAM_CHAT_ID` and DB fallback.
