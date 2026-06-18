## 1. Configuration And Assets

- [x] 1.1 Add bot settings for `PITCHWOW_PDF_API_KEY` and `PITCHWOW_PDF_BASE_URL` with default base URL `https://api-pitchwow-pdf.liven8n.site`.
- [x] 1.2 Ensure report artifact files are loaded from `new_task/prompt.md` and `new_task/schema.json` using stable project-relative paths.
- [x] 1.3 Add JSON Schema validation dependency or implement validation using an already available library.

## 2. PDF Dossier Service

- [x] 2.1 Create a dedicated async service module for PDF dossier generation.
- [x] 2.2 Implement dialogue history serialization for the dossier LLM input using all records from the current or fallback thread.
- [x] 2.3 Implement LLM JSON generation using the current main provider/model settings, with OpenAI structured output support when available.
- [x] 2.4 Set `deck.prepared_at` to the current generation date before validation/submission.
- [x] 2.5 Implement JSON parsing and schema validation against `new_task/schema.json`.
- [x] 2.6 Implement one LLM repair attempt when parsing or schema validation fails.
- [x] 2.7 Implement Pitch-wow `POST /v1/reports` request with Bearer auth and body `{external_id, payload}`.
- [x] 2.8 Implement polling of the returned status URL for up to 120 seconds.
- [x] 2.9 Implement PDF download from public `pdf_url` into a temporary local file.
- [x] 2.10 Ensure the service returns structured success/failure metadata without exposing API keys.

## 3. send_to_admin Integration

- [x] 3.1 Reuse the same full current-thread dialogue records for markdown export and PDF dossier generation.
- [x] 3.2 Invoke PDF dossier generation after the main admin message and markdown history export.
- [x] 3.3 Send the generated PDF to the admin Telegram chat when generation succeeds.
- [x] 3.4 Send an admin-chat failure message when PDF generation fails or is not configured.
- [x] 3.5 Delete temporary PDF files after success or failure paths.
- [x] 3.6 Preserve existing `send_to_admin(comment: str)` LLM-facing signature and success return text.

## 4. Persistence And Logging

- [x] 4.1 Store PDF dossier status, generated JSON, job metadata, public PDF URL, and errors under a nested key in `admin_notifications.payload`.
- [x] 4.2 Keep `delivered=True` based on the main admin message delivery, independent of PDF generation failure.
- [x] 4.3 Add structured logs for dossier generation start, validation failure, repair attempt, PDF API job creation, polling result, download, and failure.
- [x] 4.4 Ensure no logs or persisted payloads include `PITCHWOW_PDF_API_KEY`.

## 5. Tests

- [x] 5.1 Add unit tests for schema validation success and one repair attempt on invalid JSON.
- [x] 5.2 Add unit tests for PDF API job creation, polling success, failed status, and timeout.
- [x] 5.3 Extend `send_to_admin` tests for successful PDF attachment after markdown export.
- [x] 5.4 Extend `send_to_admin` tests for PDF failure admin message and persisted error metadata.
- [x] 5.5 Add a test that `ADMIN_TELEGRAM_CHAT_ID` empty still persists the notification without attempting Telegram document delivery.
- [x] 5.6 Run the focused bot/admin test suite and fix regressions.

## 6. Documentation And Verification

- [x] 6.1 Document required `.env` values for `PITCHWOW_PDF_API_KEY`, `PITCHWOW_PDF_BASE_URL`, and recommended `OPENAI_TEXT_MODEL=gpt-5.4-mini`.
- [x] 6.2 Verify `openspec validate add-pdf-dossier-to-send-to-admin --strict` passes.
- [ ] 6.3 Manually verify the happy path against the Pitch-wow API when a real API key and admin chat are configured.
