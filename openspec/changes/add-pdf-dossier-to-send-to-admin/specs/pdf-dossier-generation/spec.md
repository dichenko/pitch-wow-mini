## ADDED Requirements

### Requirement: System shall generate a founder dossier payload from dialogue history

When `send_to_admin` requests PDF dossier generation, the system SHALL load all available dialogue records for the relevant user thread and generate a JSON payload that conforms to the server-side JSON Schema in `new_task/schema.json`.

The system SHALL use the server-side prompt in `new_task/prompt.md` and the current main LLM provider/model settings. For OpenAI deployments, the selected model SHALL be `gpt-5.4-mini`.

The system SHALL set `deck.prepared_at` to the current generation date in `YYYY-MM-DD` format.

#### Scenario: Payload generated from current thread history

- **WHEN** `send_to_admin` is invoked with current thread context
- **THEN** the PDF dossier generation flow SHALL use all dialogue history records for that thread
- **THEN** the generated payload SHALL include `schema_version = "1.0"`
- **THEN** the generated payload SHALL include `template_id = "vc_founder_dossier_v1"`
- **THEN** `deck.prepared_at` SHALL equal the generation date

#### Scenario: Payload generated from latest thread fallback

- **WHEN** `send_to_admin` is invoked without current thread context
- **THEN** the PDF dossier generation flow SHALL use the user's most recently updated thread
- **THEN** records from older threads SHALL NOT be included

### Requirement: System shall validate and repair dossier JSON before PDF submission

The system SHALL parse the LLM response as JSON and validate it against `new_task/schema.json` before submitting it to the external PDF API.

If parsing or validation fails, the system SHALL perform one repair attempt using the same current main LLM provider/model and the validation error context. If the repaired JSON still fails parsing or validation, the PDF dossier generation SHALL fail with an admin-visible error.

#### Scenario: Generated JSON validates

- **WHEN** the LLM returns JSON that conforms to `new_task/schema.json`
- **THEN** the system SHALL submit that JSON to the PDF API
- **THEN** no repair attempt SHALL be made

#### Scenario: First JSON invalid and repair succeeds

- **WHEN** the first LLM response is invalid JSON or violates `new_task/schema.json`
- **THEN** the system SHALL perform exactly one repair attempt
- **THEN** if the repaired JSON validates, the system SHALL submit the repaired JSON to the PDF API

#### Scenario: Repair fails

- **WHEN** the first LLM response is invalid and the single repair attempt also fails
- **THEN** the system SHALL NOT call the PDF API
- **THEN** the generation result SHALL include an error suitable for admin notification and persistence

### Requirement: System shall create and poll Pitch-wow PDF jobs

The system SHALL create a PDF report job by calling `POST {PITCHWOW_PDF_BASE_URL}/v1/reports` with:

- `Authorization: Bearer <PITCHWOW_PDF_API_KEY>`
- `Content-Type: application/json`
- request body `{ "external_id": <trace-or-notification-id>, "payload": <validated-dossier-json> }`

The system SHALL poll the returned status URL until status is `done`, `failed`, `expired`, or until 120 seconds have elapsed.

When the job status is `done`, the system SHALL download the returned public `pdf_url` without authorization and return a local temporary PDF file path plus the public URL.

#### Scenario: PDF job completes

- **WHEN** the PDF API returns a queued job and later returns status `done`
- **THEN** the system SHALL download the PDF from `pdf_url`
- **THEN** the generation result SHALL include the local PDF path, public PDF URL, job ID, and status `done`

#### Scenario: PDF job fails

- **WHEN** the PDF API returns status `failed` or `expired`
- **THEN** the system SHALL stop polling
- **THEN** the generation result SHALL include the job ID, terminal status, and error details when available

#### Scenario: PDF job times out

- **WHEN** the PDF job does not reach a terminal status within 120 seconds
- **THEN** the system SHALL stop polling
- **THEN** the generation result SHALL indicate a timeout error

#### Scenario: PDF API not configured

- **WHEN** `PITCHWOW_PDF_API_KEY` is empty
- **THEN** the system SHALL skip external PDF generation
- **THEN** the generation result SHALL indicate that PDF generation is not configured

### Requirement: System shall persist PDF dossier generation metadata

The system SHALL store PDF dossier metadata in `admin_notifications.payload` under a dedicated nested key.

The stored metadata SHALL include generation status, generated JSON payload when available, PDF API job metadata when available, public PDF URL when available, and error details when generation fails.

#### Scenario: Successful metadata persisted

- **WHEN** PDF dossier generation succeeds
- **THEN** the notification payload SHALL include status `done`
- **THEN** the notification payload SHALL include the generated dossier JSON
- **THEN** the notification payload SHALL include the PDF API job ID and public PDF URL

#### Scenario: Failed metadata persisted

- **WHEN** PDF dossier generation fails
- **THEN** the notification payload SHALL include status `failed` or equivalent failure status
- **THEN** the notification payload SHALL include a non-secret error summary
- **THEN** the notification payload SHALL NOT include the Bearer API key
