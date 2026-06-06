## Context

`send_to_admin` already sends a Telegram text notification and persists to DB. Dialogue history is stored in `dialogue_history` table per user + thread. The bot instance is accessible via `apps.bot.app.bot_instance`.

## Goals / Non-Goals

**Goals:**
- After the notification message, attach a `.md` file with complete user dialogue history
- History includes all threads for the user, chronologically ordered
- File is temporary — created, sent, deleted in one call

**Non-Goals:**
- No permanent file storage
- No admin-requested on-demand export
- No PDF/HTML/JSON export — markdown only

## Decisions

**1. Load ALL user history, not just current thread**

Rationale: Admins need full context across conversation resets (`/start`, `/restart`). Thread isolation is for LLM context management, not for admin review.

**2. Create temp file with `tempfile.NamedTemporaryFile`**

Rationale: Standard Python pattern for temporary files. File is created in memory/disk, sent via Telegram, then automatically cleaned up in `finally` block.

**3. Send as document via `bot.send_document()`**

Rationale: Telegram supports sending files up to 50MB. Markdown files are small. Using `send_document` with `InputFile` from the temp file path. `send_document` is separate from `send_message` — independent try/except to not break main notification on file error.

**4. Markdown format with user info header + conversation transcript**

Format:
```md
# Dialogue History

**User:** First Last (@username)
**TG ID:** 123456
**Exported at:** 2026-06-06 12:00 UTC

---

## User:
<message text>

## Assistant:
<response text>

...
```

## Risks / Trade-offs

- [Risk] Temp file not deleted on crash → Mitigation: `finally` block with `os.remove()`, best-effort
- [Risk] Very large histories hit Telegram 50MB file limit → Mitigation: unlikley for text dialogues (50MB ≈ millions of messages); can add truncation later if needed
