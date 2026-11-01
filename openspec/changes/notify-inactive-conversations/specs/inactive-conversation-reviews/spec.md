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
Each report SHALL contain a compact identity/profile header and three sections: dialogue time (first interaction to last user message, Moscow), a three-to-four-sentence Russian summary, and full correspondence across all stored sessions from oldest to newest. Inactivity detection time SHALL remain stored in the database without a separate document section. Closure SHALL be attributed to inactivity in the Telegram caption, not inferred agreement. Summary generation and provider request timeouts SHALL default to 300 seconds.

#### Scenario: Five-minute summary budget
- **WHEN** the worker generates a summary with default configuration
- **THEN** both the worker deadline and the provider request timeout SHALL be 300 seconds

#### Scenario: Compact report
- **WHEN** a new or previously queued report is delivered
- **THEN** it SHALL contain dialogue time, Russian summary and correspondence as its three main sections

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

### Requirement: Reserve summary model
Summary generation SHALL try the configured model first and OpenAI with OPENAI_TEXT_MODEL second when initialization, generation, timeout or output validation fails. Each attempt SHALL have a 300-second deadline by default. Identical primary and fallback models SHALL not be attempted twice. The static unavailable-summary notice SHALL be used only when no candidate succeeds.

#### Scenario: Primary failure
- **WHEN** the primary summary model times out or returns an invalid result
- **THEN** the OpenAI model SHALL receive the same transcript and Russian summary instruction

#### Scenario: Both models unavailable
- **WHEN** all summary candidates fail
- **THEN** the full transcript SHALL still be delivered with the explicit unavailable-summary notice
