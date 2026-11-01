## Context

Daily reports already have persistent delivery and summary fallback. The user now wants closure notifications after an hour of silence, with all historical sessions, not a daily window. Existing local test-isolation changes belong to the user and must remain uncommitted.

## Goals / Non-Goals

Goals: ten-minute polling, strictly greater than sixty-minute user inactivity, full chronology, profile link, 3–4 summary sentences, durable deduplication and resumed-chat handling. Non-goals: modify send_to_admin or artifact behavior, or repair deployment-account permissions.

## Decisions

- Replace the daily worker and service with inactivity equivalents. Keep the old daily table for historical data. Migration 008 adds a dedicated inactivity queue keyed by (user_tg_id, last_history_id).
- Add nullable user_message_at to dialogue_history. New text/voice turns use the incoming Telegram message date, old records and welcome turns fall back to created_at. Sort the full history by effective user timestamp, persistence timestamp and ID.
- Every scan groups all stored turns by user (traffic is rare), supersedes stale pending snapshots and inserts at most one immutable report for the latest history entry. Reports include the first stored interaction, last user timestamp and detection time in Moscow. On first deployment existing inactive users are reported once.
- Check for resumed activity before delivery and again after summary generation. Recent profile updates also defer closure while an incoming request is still being processed. Old pending snapshots are superseded rather than delivered as if the user were still inactive.
- Preserve summaries for retries, mark sent only after Telegram accepts a file, and lock delivery rows with SKIP LOCKED. Atomic unique insertion handles concurrent scans. A crash between Telegram acceptance and database commit can still cause a duplicate.
- Remove the obsolete Compose service with --remove-orphans during deployment; run migrations before workers start. Defaults need no .env edits.

## Risks / Trade-offs

- Legacy timestamps are approximate because receipt times were not stored; explicitly retain created_at fallback.
- Only saved dialogues are exported; opening the bot before selecting a language has no stored transcript.
- Model failure produces an explicit fallback summary and still sends the complete history.
- A user can return immediately after the final pre-send check; external Telegram delivery cannot be atomic with new incoming messages.

## Migration Plan

Build images, start PostgreSQL, apply 008, then start Compose with --remove-orphans. Migration is additive and retains daily deliveries. Rollback restores the previous application images; new tables can remain to preserve state.

## Follow-up: Summary timeout and compact document

The summary defaults to a 300-second worker deadline and an explicit 300-second
provider request timeout. The latter overrides Mistral's shorter 120-second default;
other LLM call sites retain their provider defaults. Documents keep identity/profile
in a compact header and only three sections: dialogue time, Russian summary and
correspondence. Stored legacy transcript headings are nested during rendering.

On a primary error (including initialization, timeout and invalid output), try
OpenAI using OPENAI_TEXT_MODEL and OPENAI_API_KEY. Skip an identical fallback
candidate. Each candidate has the same 300-second budget (up to ten minutes for
two attempts); use a static notice only if every candidate fails. Log provider,
model and error class without exposing the transcript or credentials.
