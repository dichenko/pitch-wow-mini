## ADDED Requirements

### Requirement: Inactivity closure
The worker SHALL check every 600 seconds by default. It SHALL enqueue a report only when strictly more than 60 minutes have passed since the latest user interaction. It SHALL run independently of send_to_admin and replace daily reporting.

#### Scenario: Threshold
- **WHEN** exactly 60 minutes have elapsed
- **THEN** the conversation SHALL remain active until a later check

#### Scenario: Slow assistant
- **WHEN** a user message is saved after a slow assistant response
- **THEN** inactivity SHALL use the incoming message timestamp instead of the response persistence time

### Requirement: Full conversation report
Each report SHALL include identity, available t.me/username link, first interaction time, last user message time, inactivity detection time in Moscow, a three-to-four-sentence Russian summary and all stored user history across sessions from oldest to newest. Closure SHALL be explicitly attributed to inactivity, not inferred agreement.

#### Scenario: Multiple sessions and fallback
- **WHEN** a user has old and new sessions and summarization fails
- **THEN** the document SHALL still contain every session, chronological timestamps and an explicit unavailable-summary notice

### Requirement: Durable delivery and renewed activity
Successful reports SHALL not repeat for unchanged history. Failed files SHALL retry. Renewed dialogue SHALL become eligible for a new full-history report after another inactivity period. Pending snapshots overtaken by new activity SHALL be superseded, including when the user returns during summary generation.

#### Scenario: Restart and return
- **WHEN** a report was sent, the worker restarts and the user later sends another message
- **THEN** unchanged history SHALL not resend and new history SHALL produce a new report only after the inactivity threshold

#### Scenario: New message before retry
- **WHEN** a pending report exists and the user resumes talking
- **THEN** the stale pending report SHALL not be delivered
