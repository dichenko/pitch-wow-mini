## Context

The project already has a versioned prompt system (`PromptVersion` model with `kind` field: `system_prompt`, `tools_instruction`, `censor_prompt`). The admin panel has pages for each kind using a shared `prompt/edit.html` template. The `/start` handler sends a hardcoded greeting. The dialogue history system (`DialogueHistory`) persists user/assistant exchanges for LLM context.

## Goals / Non-Goals

**Goals:**
- Add `welcome_message` as a new `PromptVersion.kind`
- Admin page at `/admin/welcome` using the existing prompt editing pattern
- `/start` and `/restart` send active welcome message (no LLM), insert into `DialogueHistory`
- Zero DB migration needed (reuse existing `prompt_versions` table)

**Non-Goals:**
- No separate DB table for welcome messages
- No LLM involvement in welcome message generation
- No per-user welcome variants

## Decisions

**1. Reuse `PromptVersion` with `kind="welcome_message"` instead of new table**

Rationale: The versioning pattern (content, version_number, is_active, change_note, restore) is identical. Adding a new `kind` value avoids schema changes and code duplication.

**2. Admin page reuses `prompt/edit.html` template**

Rationale: Same UI pattern — textarea for content, change note field, version history list with restore buttons. Pass `kind="welcome_message"` and `title="Welcome Message"` as template variables.

**3. Seed default welcome message on first startup**

Rationale: If no welcome message exists in DB, the `seed_defaults` function creates an initial version with sensible default text. This ensures the bot always has a welcome message after first deploy.

**4. Welcome message inserted into DialogueHistory as AIMessage**

Rationale: The message comes from the bot (assistant), not the user. Using `AIMessage` means it appears in history as if the LLM said it, which is correct — the LLM will see it as context on the next exchange. Using `role="assistant"` in the DB record.

**5. Welcome sent on BOTH `/start` and `/restart`**

Rationale: Both commands represent a conversation reset. The welcome should re-establish the bot's persona and provide onboarding context for the fresh conversation.

## Risks / Trade-offs

- [Risk] Welcome message too long exceeds Telegram 4096 char limit → Mitigation: truncate or warn admin in UI if message exceeds limit
- [Risk] Seed creates duplicate on multi-instance startup → Mitigation: `_upsert_setting` pattern already handles idempotent seeding
