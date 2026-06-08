# history-export Specification

## Purpose
TBD - created by archiving change add-history-export-to-send-to-admin. Update Purpose after archive.
## Requirements
### Requirement: send_to_admin shall attach dialogue history as markdown file

When `send_to_admin` is triggered and successfully delivers the notification to the admin chat, the system SHALL additionally:

1. Load dialogue history records for the current user thread, or for the user's most recently updated thread when current thread context is unavailable
2. Generate a temporary markdown file with a header (user info + export timestamp) and the conversation transcript grouped by date
3. Send the file as a Telegram document to the admin chat
4. Delete the temporary file afterwards

#### Scenario: History file sent after notification

- **WHEN** `send_to_admin` successfully sends the notification message to admin chat
- **THEN** the system SHALL load `DialogueHistory` records for only one thread
- **THEN** a `.md` file SHALL be created with user info header and dialogue transcript
- **THEN** the file SHALL be sent to admin chat via `send_document`
- **THEN** the temp file SHALL be deleted

#### Scenario: History file groups messages by date

- **WHEN** a `.md` history file is generated
- **THEN** the file SHALL start with `# История диалога`
- **THEN** each calendar date SHALL be rendered as a second-level heading like `## 2026-06-07`
- **THEN** each user message SHALL be rendered as `**HH:MM Фаундер**: <message>`
- **THEN** each assistant response SHALL be rendered as `**Ассистент**: <message>`
- **THEN** technical `thread_id` and `trace_id` metadata SHALL NOT be rendered in the transcript

#### Scenario: No history exists

- **WHEN** the user has no dialogue history records
- **THEN** a `.md` file SHALL still be created with the user info header and a note "No dialogue history recorded"

#### Scenario: File send failure does not break notification

- **WHEN** the file upload to admin chat fails (e.g., network error)
- **THEN** the error SHALL be logged
- **THEN** the main notification message SHALL still have been delivered
- **THEN** `delivered=True` SHALL remain if the main notification was sent

### Requirement: History export shall include only the latest relevant user thread

The exported history SHALL include only `DialogueHistory` records from the current `thread_id`. If `send_to_admin` is invoked without current thread context, the system SHALL use the user's most recently updated `thread_id`. Records SHALL be ordered chronologically.

#### Scenario: Previous user threads are excluded

- **WHEN** a user has sent `/restart` and started a new thread, then triggers `send_to_admin`
- **THEN** the exported file SHALL contain dialogue records from the new/current thread
- **THEN** the exported file SHALL NOT contain dialogue records from older threads

#### Scenario: Latest user thread is used when current context is unavailable

- **WHEN** `send_to_admin` is invoked without current thread context
- **THEN** the system SHALL find the user's most recently updated thread
- **THEN** the exported file SHALL contain only dialogue records from that thread
