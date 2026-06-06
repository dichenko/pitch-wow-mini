## Why

When a user triggers `send_to_admin`, admins receive only the user's current comment without conversation context. Without the full dialogue history, admins have no way to understand what led to the request. Attaching the complete dialogue history as a markdown file gives admins full context for informed decisions.

## What Changes

- After sending the main notification to admin chat, `send_to_admin` loads all dialogue history for the user
- Generates a temporary `.md` file with user info header + full conversation transcript
- Sends the file as a Telegram document to the admin group chat
- Cleans up the temporary file after sending

## Capabilities

### New Capabilities

- `history-export`: Generate and send a markdown file with the full dialogue history when `send_to_admin` is triggered

### Modified Capabilities

- `langchain-tools`: The `send_to_admin` tool SHALL additionally attach a dialogue history export file after the main notification message

## Non-goals

- No admin-facing UI for history export
- No per-request export to user
- No configurable export format (markdown only)

## Impact

- `apps/bot/app/agent/tools/send_to_admin.py` — add history loading, md generation, file upload
- `apps/bot/app/services/history_service.py` — add `load_all_user_history()` function (no thread filter)
