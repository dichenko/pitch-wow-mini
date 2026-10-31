## ADDED Requirements

### Requirement: Daily review scheduling
The system SHALL enqueue one report per user with saved dialogue in each preceding 24-hour window ending at 23:55 Europe/Moscow, independent of send_to_admin. It SHALL catch up missed windows and persist scheduling progress atomically with queue insertion.

#### Scenario: Multiple sessions
- **WHEN** a user has dialogue in multiple threads during a window
- **THEN** one report SHALL contain all their window turns chronologically, grouped by session

#### Scenario: Window boundaries and no visitors
- **WHEN** a turn occurs exactly at the cutoff
- **THEN** it SHALL belong to the next window
- **AND** a window without dialogue SHALL send no documents

### Requirement: Review document contents
Each Markdown document SHALL identify the user with available name, username and Telegram ID, describe the reporting interval, include a three-sentence Russian review of topic, outcome and completion, followed by the full period transcript. Unknown completion SHALL be explicitly uncertain.

#### Scenario: Summarizer unavailable
- **WHEN** the model times out or returns invalid output
- **THEN** the report SHALL include an explicit three-sentence fallback and the full transcript

### Requirement: Persistent delivery
The system SHALL send reports to ADMIN_TELEGRAM_CHAT_ID, persist successful deliveries, retry individual failures and avoid resending already persisted successful reports on restart.

#### Scenario: Partial delivery failure
- **WHEN** sending one user's file fails
- **THEN** other users SHALL still be processed and the failed file SHALL retry after a delay

#### Scenario: Restart
- **WHEN** a worker restarts after a successful report was persisted
- **THEN** it SHALL not resend that report
