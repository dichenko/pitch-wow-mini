## ADDED Requirements

### Requirement: Artifact input includes the triggering message
New artifact jobs SHALL contain an immutable dialogue snapshot including the user message that triggered send_to_admin, even if that turn has not yet been persisted. Existing jobs without a snapshot SHALL retain the history-loading fallback.

#### Scenario: Worker wins the race
- **WHEN** the worker claims a job before the current dialogue turn is saved
- **THEN** artifact generation SHALL still receive the triggering user message

#### Scenario: Existing job
- **WHEN** a previously queued job has no input snapshot
- **THEN** the worker SHALL load its current user/thread history as before
