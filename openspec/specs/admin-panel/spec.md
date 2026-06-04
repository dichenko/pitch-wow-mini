# Spec: admin-panel

## Purpose

A separate FastAPI web service providing an admin panel for managing the AI assistant. Uses Jinja2 templates with HTMX for server-side rendering. Provides pages for System Prompt, Tools Instruction, Censor, Administrators, Debug, and Preview Assembled Prompt management.

## Requirements

### Requirement: Admin panel shall be a separate web service

The system SHALL provide admin panel as a separate service `admin`.

Admin service SHALL have its own Docker container and listen internally on port `8080`.

#### Scenario: Admin service runs independently

- **WHEN** the Docker Compose stack is started and services are running
- **THEN** the admin service SHALL be a separate container from the bot service
- **THEN** SHALL listen on port `8080` internally

### Requirement: Admin panel shall provide management sections

Admin panel SHALL include the following sections:

1. System Prompt
2. Tools Instruction
3. Administrators
4. Censor (response reviewer)
5. Debug
6. Preview Assembled Prompt
7. Settings

#### Scenario: Admin navigates to sections

- **WHEN** an authenticated admin opens the admin panel and the dashboard loads
- **THEN** navigation links SHALL be present for System Prompt, Tools Instruction, Censor, Administrators, Debug, Preview Prompt and Settings sections

### Requirement: System Prompt page

System Prompt page SHALL allow:

- view active system prompt;
- edit active system prompt for `write` and `superadmin`;
- save new version;
- view last three previous versions;
- restore one of last three versions;
- see who saved each version and when.

#### Scenario: Admin views system prompt

- **WHEN** admin with at least `read` role opens the System Prompt page
- **THEN** the active system prompt content SHALL be displayed

#### Scenario: Write admin saves system prompt

- **WHEN** admin with `write` or `superadmin` role edits and saves the system prompt
- **THEN** a new version SHALL be created and marked active

### Requirement: Tools Instruction page

Tools Instruction page SHALL allow:

- view active tools instruction;
- edit active tools instruction for `write` and `superadmin`;
- save new version;
- view last three previous versions;
- restore one of last three versions;
- see who saved each version and when.

#### Scenario: Admin views tools instruction

- **WHEN** admin with at least `read` role opens the Tools Instruction page
- **THEN** the active tools instruction content SHALL be displayed

#### Scenario: Write admin saves tools instruction

- **WHEN** admin with `write` or `superadmin` role edits and saves the tools instruction
- **THEN** a new version SHALL be created and marked active

### Requirement: Administrators page

Administrators page SHALL allow:

- view admins for all roles;
- add admin by Telegram ID;
- optionally store username/display name;
- choose role: read/write/superadmin;
- deactivate/delete admin;
- change admin role.

Only `superadmin` SHALL be allowed to add, delete, deactivate or change roles.

#### Scenario: Superadmin adds admin

- **WHEN** admin with `superadmin` role submits a new admin with Telegram ID and role
- **THEN** the system SHALL create the admin record

#### Scenario: Non-superadmin views admins

- **WHEN** admin with `read` or `write` role opens the Administrators page
- **THEN** the admin list SHALL be visible
- **THEN** add/deactivate/role-change controls SHALL NOT be available

### Requirement: Admin panel shall use FastAPI Jinja2 HTMX

The admin panel SHALL use FastAPI with Jinja2 templates and HTMX for the UI.

#### Scenario: Admin page loads

- **WHEN** an authenticated admin requests an admin page
- **THEN** the admin service SHALL render the page using Jinja2 templates

### Requirement: Admin panel shall have health endpoint

Admin service SHALL expose:

```http
GET /health
```

Expected response:

```json
{"status":"OK","service":"admin"}
```

#### Scenario: Health check

- **WHEN** the admin service is running and a GET request is sent to `/health`
- **THEN** the response SHALL be `{"status":"OK","service":"admin"}` with HTTP 200

### Requirement: Censor page shall allow managing response reviewer

The admin panel SHALL provide a page at `/admin/censor`.

Censor page SHALL allow:

- checkbox: enable/disable censor (`CENSOR_ENABLED`);
- view active censor prompt;
- edit active censor prompt for `write` and `superadmin`;
- save new censor prompt version;
- view last three previous versions;
- restore one of last three versions;
- see who saved each version and when;
- optional change_note field.

#### Scenario: Admin enables censor

- **WHEN** admin with `write` or `superadmin` role toggles censor enabled checkbox and saves
- **THEN** censor SHALL be enabled for all subsequent user messages
- **THEN** the setting SHALL be persisted in DB settings table

#### Scenario: Admin disables censor

- **WHEN** censor is currently enabled and admin toggles censor disabled and saves
- **THEN** censor LLM pass SHALL be skipped for all subsequent messages
- **THEN** draft responses SHALL be sent directly to users

#### Scenario: Admin saves censor prompt

- **WHEN** admin with `write` or `superadmin` role edits and saves censor prompt
- **THEN** system SHALL create a new censor prompt version, mark it as active, and keep all previous versions

#### Scenario: Admin restores censor prompt

- **WHEN** admin with `write` or `superadmin` role clicks restore on one of the last three censor prompt versions
- **THEN** system SHALL create a new active version copied from selected old version
- **THEN** record who restored it and when

### Requirement: Debug page shall show censor and send_to_admin status

The debug page `/admin/debug` SHALL additionally show:

- censor enabled/disabled;
- active censor prompt version;
- `ADMIN_TELEGRAM_CHAT_ID` configured yes/no (without revealing the value);
- last `send_to_admin` notification timestamp if available;
- last censor run timestamp and status if available.

#### Scenario: Admin views debug page

- **WHEN** an authenticated admin opens the debug page
- **THEN** censor status, send_to_admin configuration status and last run timestamps SHALL be displayed
- **THEN** no secret values SHALL be visible

### Requirement: Preview assembled prompt page

The admin panel SHALL provide a read-only preview page at `/admin/preview-prompt`.

The preview page SHALL display the full assembled prompt as sent to the LLM, combining:

- core guardrails (from file, non-editable);
- active system prompt (from DB);
- active tools instruction (from DB).

#### Scenario: Admin previews assembled prompt

- **WHEN** an authenticated admin opens the preview prompt page
- **THEN** the full assembled prompt SHALL be displayed in read-only form
- **THEN** the admin SHALL see the exact text that is sent to the LLM as the system message
