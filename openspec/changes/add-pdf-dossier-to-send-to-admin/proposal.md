## Why

Admins currently receive the user's message and a markdown dialogue export, but still have to manually turn founder interview context into an investment-ready dossier. This change automates that dossier generation when `send_to_admin` is used, while keeping the existing admin notification flow intact.

## What Changes

- Extend `send_to_admin` so successful admin notifications also attempt to generate and attach a PDF founder dossier.
- Add a server-side PDF dossier generation flow:
  - load the full current-thread dialogue history;
  - use the current main LLM settings with `gpt-5.4-mini` as the intended model;
  - apply file-based prompt and JSON Schema artifacts from `new_task/`;
  - validate the generated JSON and perform one LLM repair attempt on validation failure;
  - create a Pitch-wow PDF job with Bearer authentication;
  - poll for up to 120 seconds;
  - download the generated PDF and send it to the admin Telegram group.
- On PDF generation failure, send a clear admin-group message that the PDF was not created.
- Persist PDF generation metadata, public PDF URL when available, generated JSON payload, and error details in `admin_notifications.payload`.
- Keep the existing markdown history attachment.

## Non-goals

- Do not add a durable queue or separate OS worker for MVP.
- Do not add admin UI editing for the dossier prompt/schema; files remain manually editable on the server.
- Do not change the `send_to_admin(comment: str)` LLM-facing signature.
- Do not remove or replace the markdown dialogue export.
- Do not add context-length summarization fallback in this change.

## Capabilities

### New Capabilities

- `pdf-dossier-generation`: Generate a strict founder dossier JSON from dialogue history, submit it to the external Pitch-wow PDF API, poll for completion, download the PDF, and report success/failure.

### Modified Capabilities

- `langchain-tools`: `send_to_admin` shall attach the generated PDF dossier when available and notify admins when PDF generation fails.

## Impact

- Affected code: `apps/bot/app/agent/tools/send_to_admin.py`, bot service configuration, new PDF dossier service module, tests around admin notifications.
- External systems: Pitch-wow PDF API at `PITCHWOW_PDF_BASE_URL` with `PITCHWOW_PDF_API_KEY`.
- Dependencies: may require JSON Schema validation support if not already available.
- Data: `admin_notifications.payload` will include PDF generation status, public PDF URL, generated payload, job metadata, and errors.
