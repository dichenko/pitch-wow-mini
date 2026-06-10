## ADDED Requirements

### Requirement: Welcome Message page shall manage localized welcome messages

The admin panel SHALL provide localized welcome message management on the Welcome Message page.

The page SHALL allow admins to view active Russian, Uzbek, and English welcome messages; edit each language for `write` and `superadmin`; save a new version per language; view recent previous versions per language; restore a previous version per language; and see who saved each version and when.

#### Scenario: Admin views localized welcome messages

- **WHEN** admin with at least `read` role opens the Welcome Message page
- **THEN** the active Russian welcome message SHALL be displayed
- **THEN** the active Uzbek welcome message SHALL be displayed
- **THEN** the active English welcome message SHALL be displayed

#### Scenario: Write admin saves one localized welcome

- **WHEN** admin with `write` or `superadmin` role edits and saves the Uzbek welcome message
- **THEN** a new `welcome_message_uz` version SHALL be created and marked active
- **THEN** active Russian and English welcome messages SHALL NOT be modified

#### Scenario: Read admin cannot edit localized welcome

- **WHEN** admin with `read` role opens the Welcome Message page
- **THEN** localized welcome content SHALL be visible
- **THEN** save and restore controls SHALL NOT be available

#### Scenario: Admin restores one localized welcome

- **WHEN** admin with `write` or `superadmin` role restores a previous English welcome version
- **THEN** a new active `welcome_message_en` version SHALL be created from the selected version
- **THEN** Russian and Uzbek welcome versions SHALL NOT be modified

#### Scenario: Localized welcome save requires CSRF

- **WHEN** admin submits a localized welcome save or restore request without a valid CSRF token
- **THEN** the system SHALL reject the request with 403
