## MODIFIED Requirements

### Requirement: Settings page shall require CSRF protection

All POST requests that save admin settings SHALL include a valid CSRF token.

The settings page SHALL render a hidden CSRF token whose value matches the CSRF cookie that the server expects on the subsequent save request.

#### Scenario: Settings form renders synchronized CSRF token

- **WHEN** an authenticated admin opens `/admin/settings`
- **THEN** the response SHALL include a `csrf_token` cookie
- **THEN** the settings form SHALL include a hidden `csrf_token` field with the same token value

#### Scenario: POST without CSRF token

- **WHEN** an admin sends a POST to `/admin/settings/save` without a matching CSRF token
- **THEN** the system SHALL reject the request with 403

#### Scenario: POST with synchronized CSRF token

- **WHEN** an admin opens `/admin/settings` and submits the rendered settings form without modifying its CSRF field
- **THEN** CSRF validation SHALL pass
- **THEN** settings validation and persistence SHALL continue according to the admin's role and submitted values
