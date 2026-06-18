## Context

`send_to_admin` is the mandatory bot tool for forwarding user requests to the admin Telegram group. It already injects Telegram user metadata server-side, persists an `AdminNotification`, sends a formatted admin message, loads the full current-thread dialogue history, and sends that history as a markdown document.

The new requirement adds a PDF founder dossier generated from the same dialogue history. The report content is defined by server-side files in `new_task/`: `prompt.md`, `schema.json`, and `sample.json`. The generated JSON is submitted to the Pitch-wow PDF API, which returns a job status URL and eventually a public `pdf_url`.

## Goals / Non-Goals

**Goals:**

- Keep the existing `send_to_admin(comment: str)` tool signature unchanged.
- Generate a strict JSON payload from full current-thread dialogue history using the current main LLM provider/model, with `gpt-5.4-mini` as the selected OpenAI model.
- Validate generated JSON against `new_task/schema.json`, with one repair attempt on validation failure.
- Submit `{ "external_id": "...", "payload": <generated-json> }` to `POST /v1/reports` using `PITCHWOW_PDF_API_KEY`.
- Poll the returned status URL for up to 120 seconds, download the final PDF, and send it to the admin chat.
- Notify admins when PDF generation fails without breaking the main notification or markdown export.
- Store PDF status, job metadata, generated payload, public URL when available, and errors in `admin_notifications.payload`.

**Non-Goals:**

- No durable queue, separate worker process, or retry scheduler for MVP.
- No admin UI for editing the prompt/schema.
- No context-length summarization fallback.
- No change to markdown history export behavior.

## Decisions

### Use an in-process async service, not a separate worker

Implement PDF generation as a dedicated bot service module called by `send_to_admin`.

Rationale: the current bot stack is async, already has `httpx`, LLM factories, temporary file patterns, and Telegram document sending. The MVP timeout is bounded to 120 seconds, so a separate queue would add operational complexity before it is needed.

Alternative considered: a durable background worker. This is better for long-running jobs and retries, but it requires a queue or job table, lifecycle handling, and later admin visibility.

### Treat PDF generation as best-effort after the main notification

The admin message and markdown export should remain the primary behavior. PDF failure should produce an admin-visible failure message and be recorded in the notification payload.

Rationale: `send_to_admin` should not lose the core admin escalation because an LLM call, validation step, external API request, poll timeout, or download failed.

### Use file-based report artifacts

Load `new_task/prompt.md` and `new_task/schema.json` from disk at runtime. `prepared_at` should be set to the generation date before validation/submission.

Rationale: the user will manually edit these files on the server. Keeping them as files avoids new admin UI and prompt-versioning scope.

### Use structured JSON generation when available

For OpenAI, prefer native Structured Outputs with the schema rather than prompt-only JSON. For other current-provider paths, generate JSON with strict prompt instructions and still validate locally. In all cases, perform one repair attempt after validation/parsing failure.

Rationale: native schema-constrained output is more reliable, but this change should still respect the existing "current main LLM settings" rule.

### Validate with JSON Schema locally

Add a validation layer against `new_task/schema.json` before calling the PDF API. If a validation dependency is needed, use a small Python dependency such as `jsonschema`.

Rationale: the external API also validates, but local validation allows one repair attempt and clearer error reporting to admins.

### Store metadata in existing JSONB payload

Do not migrate `admin_notifications`. Store PDF metadata under a nested payload key, for example `pdf_dossier`.

Rationale: the table already has JSONB payload for extended notification metadata, and no query/index requirement exists for PDF fields.

## Risks / Trade-offs

- Long PDF generation blocks the tool call until timeout -> cap total polling at 120 seconds and keep main notification/markdown delivery first.
- Large dialogue history may exceed model context -> accept as MVP limitation and send "PDF not created" on failure.
- Schema uses JSON Schema keywords that may exceed a provider's native structured-output subset -> keep local validation and one repair attempt; fall back to prompt-only JSON for unsupported provider paths.
- External API availability may be intermittent -> surface the failure to admins and store job/error metadata.
- Public PDF URLs expire after 30 days -> store the URL for audit context only; do not rely on it as durable storage.

## Migration Plan

1. Add `PITCHWOW_PDF_API_KEY` and `PITCHWOW_PDF_BASE_URL` settings to bot configuration.
2. Configure `OPENAI_TEXT_MODEL=gpt-5.4-mini` or set the main LLM model setting to `gpt-5.4-mini`.
3. Deploy the bot with `new_task/` files present on the server.
4. Roll back by unsetting `PITCHWOW_PDF_API_KEY` or reverting the service integration; existing admin notification and markdown behavior should continue.

## Open Questions

- None for MVP. A later change can add a durable background worker if real PDF generation times regularly exceed the 120-second tool budget.
