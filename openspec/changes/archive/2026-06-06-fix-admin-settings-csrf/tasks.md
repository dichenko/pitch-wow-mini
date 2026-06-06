## 1. Settings CSRF Rendering

- [x] 1.1 Update `settings_page` to create or reuse a CSRF token with `get_or_create_csrf_token(request)`.
- [x] 1.2 Pass `csrf_token` into the settings template context on initial render, validation-error render, and success render.
- [x] 1.3 Set the outgoing CSRF cookie with the same token rendered in the form via `set_csrf_cookie(response, csrf_token)`.
- [x] 1.4 Update `settings.html` to render the hidden CSRF field from `{{ csrf_token }}` instead of reading `request.cookies`.

## 2. Save Path Correctness

- [x] 2.1 Add the missing SQLAlchemy `select` import used by `settings_save`.
- [x] 2.2 Confirm read-only admins still cannot submit changes and write/superadmin sessions can proceed past CSRF validation.

## 3. Verification

- [x] 3.1 Add or update tests covering synchronized CSRF rendering for `/admin/settings`.
- [x] 3.2 Add or update tests covering POST `/admin/settings/save` rejection without a matching CSRF token.
- [x] 3.3 Add or update tests covering a normal settings save with a matching CSRF token.
- [x] 3.4 Run the relevant test suite and `openspec validate fix-admin-settings-csrf --strict`.
