## ADDED Requirements

### Requirement: send_to_admin shall attach dialogue history as markdown file

When `send_to_admin` is triggered and successfully delivers the notification to the admin chat, the system SHALL additionally:

1. Load all dialogue history records for the user across all threads
2. Generate a temporary markdown file with a header (user info + export timestamp) and the full conversation transcript
3. Send the file as a Telegram document to the admin chat
4. Delete the temporary file afterwards

#### Scenario: History file sent after notification

- **WHEN** `send_to_admin` successfully sends the notification message to admin chat
- **THEN** the system SHALL load all `DialogueHistory` records for the user
- **THEN** a `.md` file SHALL be created with user info header and dialogue transcript
- **THEN** the file SHALL be sent to admin chat via `send_document`
- **THEN** the temp file SHALL be deleted

#### Scenario: No history exists

- **WHEN** the user has no dialogue history records
- **THEN** a `.md` file SHALL still be created with the user info header and a note "No dialogue history recorded"

#### Scenario: File send failure does not break notification

- **WHEN** the file upload to admin chat fails (e.g., network error)
- **THEN** the error SHALL be logged
- **THEN** the main notification message SHALL still have been delivered
- **THEN** `delivered=True` SHALL remain if the main notification was sent

### Requirement: History export shall include all user threads

The exported history SHALL include all `DialogueHistory` records for the user across all `thread_id` values, ordered chronologically.

#### Scenario: Multi-thread user history exported

- **WHEN** a user has sent `/restart` and started a new thread, then triggers `send_to_admin`
- **THEN** the exported file SHALL contain dialogue records from both the old and new threads
