# Pitch-wow PDF API Integration

Base URL:

```text
https://api-pitchwow-pdf.liven8n.site
```

All private API requests require:

```http
Authorization: Bearer <API_KEY>
```

## 1. Create PDF Job

```http
POST /v1/reports
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

Request body:

```json
{
  "external_id": "optional-client-id",
  "payload": {
    "schema_version": "1.0",
    "startup": {},
    "founder": {},
    "summary": "...",
    "traction": [],
    "market": {},
    "risks": []
  }
}
```

For the current sample template, `payload` must match:

```text
templates/sample_founder_report/v1/schema.json
```

Example:

```bash
curl -X POST https://api-pitchwow-pdf.liven8n.site/v1/reports \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  --data-binary @templates/sample_founder_report/v1/sample.json
```

Successful response:

```json
{
  "job_id": "job_01...",
  "status": "queued",
  "status_url": "/v1/reports/job_01...",
  "poll_after_seconds": 10
}
```

## 2. Poll Job Status

Wait `poll_after_seconds`, then call:

```http
GET /v1/reports/:job_id
Authorization: Bearer <API_KEY>
```

Example:

```bash
curl https://api-pitchwow-pdf.liven8n.site/v1/reports/job_01... \
  -H "Authorization: Bearer <API_KEY>"
```

Possible statuses:

```text
queued
processing
done
failed
expired
```

If the status is `queued` or `processing`, poll again every 10 seconds.

## 3. Done Response

```json
{
  "job_id": "job_01...",
  "status": "done",
  "created_at": "2026-06-18T04:57:07.851Z",
  "updated_at": "2026-06-18T04:57:08.825Z",
  "pdf_url": "https://api-pitchwow-pdf.liven8n.site/r/pw_xxx.pdf",
  "expires_at": "2026-07-18T04:57:07.851Z"
}
```

Use `pdf_url` as the final public PDF link. It does not require authorization.

## 4. Failed Response

```json
{
  "job_id": "job_01...",
  "status": "failed",
  "error": {
    "code": "RENDER_FAILED",
    "message": "PDF rendering failed"
  }
}
```

## 5. Validation Error

If the payload does not match the template schema:

```http
400 Bad Request
```

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Payload does not match template schema",
  "details": [
    {
      "path": "/startup/name",
      "message": "must be string"
    }
  ]
}
```

## 6. Important Rules

- Max payload size: `256 KB`.
- Public PDF links expire after 30 days.
- One API key can access only jobs created by its assistant.
- Do not send HTML, external image URLs, CSS, JS, or remote assets in payload.
- Treat `pdf_url` as the final result for the end user.
