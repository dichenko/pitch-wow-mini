## Why

Saving LLM settings from `/admin/settings` can fail with `403 CSRF token mismatch` because the rendered form token can differ from the CSRF cookie set in the same response. This blocks admins from persisting provider and model changes, including the new Mistral option.

## What Changes

- Render the settings form with a CSRF token generated or reused by the router, instead of reading directly from the incoming request cookie in the template.
- Set the outgoing CSRF cookie to the same token that is rendered into the form.
- Preserve CSRF protection for `/admin/settings/save`; do not weaken or bypass validation.
- Fix the settings save path so it can proceed past CSRF validation and complete its existing DB/audit work.

## Non-goals

- No change to authentication, admin roles, or session cookie semantics.
- No change to LLM provider behavior, model defaults, or database schema.
- No redesign of the settings UI beyond the hidden CSRF token handling.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `admin-settings`: Clarify that settings form rendering SHALL keep the submitted CSRF token synchronized with the cookie expected by POST validation.

## Impact

- `apps/admin/app/routers/settings.py` - align token generation, template context, cookie setting, and save-path imports.
- `apps/admin/app/templates/settings/settings.html` - render the router-provided `csrf_token`.
- Admin settings save workflow - expected to return success or validation errors rather than CSRF mismatch when the page was opened normally.
