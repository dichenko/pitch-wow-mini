## Context

The admin service protects POST routes with a double-submit CSRF pattern: a readable `csrf_token` cookie is compared against a hidden form field by `verify_csrf`. Most admin pages generate or reuse a token in the router, pass that token to the Jinja template, and set the response cookie to the same value.

The settings page currently diverges from that pattern. Its template reads `request.cookies["csrf_token"]` directly, while the route sets a fresh CSRF cookie without passing that same token into the template. On first render, or after a response rotates the cookie, the form field and cookie can differ, causing `/admin/settings/save` to reject a normal admin save attempt with `403 CSRF token mismatch`.

## Goals / Non-Goals

**Goals:**

- Make `/admin/settings` render a hidden CSRF token that matches the cookie expected by `/admin/settings/save`.
- Preserve the existing double-submit CSRF validation behavior.
- Align settings page token handling with the existing admin pages.
- Ensure the save path can execute its existing DB update and audit logging after CSRF passes.

**Non-Goals:**

- Replace the CSRF scheme with server-side token storage.
- Change session cookie settings, SameSite policy, or admin role checks.
- Change LLM provider/model validation beyond what is necessary for saving settings.

## Decisions

**1. Use the existing `get_or_create_csrf_token()` plus `set_csrf_cookie(response, csrf_token)` pattern**

Rationale: This matches `system_prompt`, `censor`, and `admins` routers and avoids introducing a second CSRF mechanism. The router remains the source of the token used by both the form and the outgoing cookie.

Alternative considered: keep reading the cookie in the template and avoid rotating the cookie. This would still leave first-render behavior brittle when no incoming CSRF cookie exists.

**2. Render `{{ csrf_token }}` in the settings template**

Rationale: Templates should not infer security token state from the request when the response may set a different cookie. Passing the token explicitly keeps the rendered form and cookie synchronized.

Alternative considered: use JavaScript to read the cookie before submit. This is unnecessary for a server-rendered form and would not help clients with script disabled.

**3. Keep CSRF validation on the POST dependency**

Rationale: The bug is token synchronization, not excessive validation. Removing or exempting the route would violate the admin-settings requirement and weaken admin write protection.

## Risks / Trade-offs

- [Risk] Existing browser tabs opened before the fix can still contain stale form tokens. -> Mitigation: users reload `/admin/settings` before retrying; new renders produce synchronized tokens.
- [Risk] Fixing CSRF exposes a later save-path exception. -> Mitigation: include the missing SQLAlchemy `select` import in implementation tasks so the route can find the admin record and continue to save/audit logic.
