## Why

Rare bot visitors are valuable leads, but administrators only hear about conversations when the assistant calls a tool. Artifact generation can also start before the triggering message is saved and omit the founder's last answer.

## What Changes

- Deliver one Markdown review per active user daily at 23:55 Europe/Moscow, covering the preceding 24 hours across sessions.
- Include identity, a three-sentence Russian review of topics, outcome and completion, and the complete period transcript.
- Persist delivery progress and retry individual failures without resending completed reviews after restarts.
- Snapshot artifact input at enqueue time, including the triggering user message.

## Capabilities

### New Capabilities
- `daily-user-reviews`: Scheduled per-user administrator reports independent of assistant tool calls.

### Modified Capabilities
- `history-export`: Artifact input includes the triggering message even before the current turn is persisted.

## Impact

Bot services, a new daily review worker, database migration, Docker Compose, configuration, tests and deployment documentation. The default production branch is master, which already triggers the deployment workflow.

## Non-goals

Do not change artifact contents, tool-trigger criteria, existing artifact delivery statuses or product methodology.
