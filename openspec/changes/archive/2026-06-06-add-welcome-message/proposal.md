## Why

The bot currently sends a hardcoded greeting on `/start`. There is no way for admins to customize this message or control what first impression the bot makes. A versioned welcome message gives admins control over onboarding while automatically seeding LLM context for the first real interaction.

## What Changes

- Add a new "Welcome Message" page in the admin panel for editing the welcome text
- Welcome messages use the existing `PromptVersion` system (kind=`welcome_message`) — full versioning with history and restore
- On `/start` and `/restart`, the bot sends the active welcome message directly (no LLM) and persists it to dialogue history
- The welcome message becomes part of the LLM context on the very next user message

## Capabilities

### New Capabilities

- `welcome-message`: Admin-configurable welcome message sent on `/start` and `/restart`, versioned and persisted to dialogue history for LLM context

### Modified Capabilities

- `admin-panel`: New "Welcome Message" page accessible from the admin sidebar, using the existing prompt edit/version pattern
- `langchain-tools`: `/start` and `/restart` handlers SHALL send the active welcome message and insert it into dialogue history

## Non-goals

- Multi-language welcome messages
- Per-user welcome message variants
- LLM-generated welcome messages

## Impact

- `apps/bot/app/handlers/start.py` — send welcome message, persist to history
- `apps/bot/app/handlers/restart.py` — send welcome message, persist to history
- `apps/admin/app/routers/` — new `welcome.py` router (mirrors system_prompt.py pattern)
- `apps/admin/app/templates/` — reuse prompt/edit.html or new template
- `apps/admin/app/main.py` — register new router
- `apps/admin/app/templates/base.html` — add sidebar link
- No DB migration needed (uses existing `prompt_versions` table with `kind="welcome_message"`)
