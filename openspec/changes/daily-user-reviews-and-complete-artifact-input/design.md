## Context

Tool calls currently control administrator visibility. Dialogue turns are saved only after the agent replies, while the artifact worker may claim a new job earlier.

## Goals / Non-Goals

Goals: independent daily lead visibility, complete artifact input and restart-safe per-user delivery. Non-goals: change existing tool triggers, artifact package contents or artifact delivery statuses.

## Decisions

- Run a separate Compose worker at 23:55 Europe/Moscow. Use fixed 24-hour half-open windows [previous cutoff, cutoff), including every stored turn across threads. A persisted scheduling cursor catches up missed windows after downtime.
- Enqueue immutable per-user transcript snapshots and identity in a daily_user_reviews table, with unique (window_end, user_tg_id). Advance the scheduling cursor in the same transaction as queue insertion. Lock the cursor and delivery rows to coordinate worker instances.
- Generate exactly three Russian review sentences through the configured text model, treating dialogue as untrusted data. If summarization fails, send an explicit three-sentence fallback with the complete transcript; visibility must not depend on LLM availability.
- Store the generated review for retries, mark sent only after Telegram accepts the document, and retry failures with a delay. Telegram offers no document idempotency key, so a crash between acceptance and commit can still duplicate a file.
- Populate ArtifactJob.input_dialogue_md at enqueue time from history plus the triggering message. The worker uses the snapshot and falls back to the old history loader for pre-existing jobs. No change to artifact delivery statuses.
- Include users with a stored welcome turn. Visits before language selection do not yet have dialogue records and are outside this conversation report.

## Risks / Trade-offs

- Long histories can exceed model context: fall back to an explicit unavailable review while preserving the full transcript.
- New table requires migration before starting workers: deployment builds images, runs migrations in a one-off bot container, then starts services.
- Partial failures do not block other users; pending rows retry independently.

## Migration Plan

Apply Alembic 007 before starting the new worker. Existing artifact jobs remain compatible. Rollback stops daily-review-worker and reverts application images; retain the additive table to preserve delivery history.

## Open Questions

None. Production uses master rather than main; retain that branch and workflow trigger.
