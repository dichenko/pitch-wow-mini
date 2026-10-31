## Why

Administrators need a lead's conversation soon after the user stops replying, rather than a report at a fixed daily time. The report must include the full user history and explicitly identify inactivity-based closure.

## What Changes

- Replace daily scheduling with a worker polling every ten minutes.
- After strictly more than sixty minutes without a user message, send a Markdown report with first visit, last user message and detection times in Moscow, profile link, a three-to-four-sentence summary and full chronological history.
- Persist per-history delivery state, retry failed uploads, skip already reported history and report again after renewed conversation becomes inactive.
- Record incoming message time separately from the later assistant-response persistence time.

## Capabilities

### New Capabilities
- `inactive-conversation-reviews`: Inactivity-triggered full-history administrator reports.

### Modified Capabilities

None. The previous daily reporting implementation is superseded by this capability.

## Impact

Bot history persistence, review worker/service, additive Alembic 008 migration, Compose, environment defaults, deployment instructions and tests. Existing artifact snapshot behavior is retained. Historical daily review rows are retained but no longer processed.

## Non-goals

Do not change send_to_admin triggers, artifact package contents or existing artifact delivery statuses. Do not change server deployment-account permissions.
