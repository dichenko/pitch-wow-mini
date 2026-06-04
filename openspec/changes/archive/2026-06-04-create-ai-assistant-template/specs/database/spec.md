# Spec Delta: database

## Capability

```text
database
```

## ADDED Requirements

### Requirement: Database shall store admins

The system SHALL create and maintain an `admins` table with the following fields:

```sql
id UUID PRIMARY KEY
tg_id BIGINT NOT NULL UNIQUE
username TEXT NULL
display_name TEXT NULL
role TEXT NOT NULL CHECK (role IN ('read', 'write', 'superadmin'))
is_active BOOLEAN NOT NULL DEFAULT TRUE
created_by_admin_id UUID NULL REFERENCES admins(id)
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
deactivated_by_admin_id UUID NULL REFERENCES admins(id)
deactivated_at TIMESTAMPTZ NULL
```

#### Scenario: Admin record created

- GIVEN a new admin is added by a superadmin
- WHEN the insert completes
- THEN the `admins` table SHALL contain the new record with `is_active = TRUE`

### Requirement: Database shall store admin login tokens

The system SHALL create and maintain an `admin_login_tokens` table with the following fields:

```sql
id UUID PRIMARY KEY
admin_tg_id BIGINT NOT NULL
token_hash TEXT NOT NULL UNIQUE
expires_at TIMESTAMPTZ NOT NULL
used_at TIMESTAMPTZ NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
ip_address INET NULL
user_agent TEXT NULL
```

#### Scenario: Login token created

- GIVEN an admin requests a login link via `/admin`
- WHEN the token is generated
- THEN a record SHALL be inserted with only the SHA-256 hash and an expiry timestamp

### Requirement: Database shall store prompt versions

The system SHALL create and maintain a `prompt_versions` table with the following fields:

```sql
id UUID PRIMARY KEY
kind TEXT NOT NULL CHECK (kind IN ('system_prompt', 'tools_instruction', 'censor_prompt'))
version_number INTEGER NOT NULL
content TEXT NOT NULL
is_active BOOLEAN NOT NULL DEFAULT FALSE
created_by_admin_id UUID NULL REFERENCES admins(id)
created_by_tg_id BIGINT NULL
created_by_username TEXT NULL
change_note TEXT NULL
restored_from_version_id UUID NULL REFERENCES prompt_versions(id)
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

Constraints:

```sql
UNIQUE(kind, version_number)
```

Only one active version per kind SHALL exist at any time. The system SHALL enforce this via partial unique index or transaction logic.

#### Scenario: Prompt version saved

- GIVEN an admin saves a new system prompt
- WHEN the version is created
- THEN a new record SHALL be inserted with an incremented `version_number` and `is_active = TRUE`
- AND all previous versions of the same kind SHALL have `is_active = FALSE`

### Requirement: Database shall store audit log

The system SHALL create and maintain an `admin_audit_log` table with the following fields:

```sql
id UUID PRIMARY KEY
admin_id UUID NULL REFERENCES admins(id)
admin_tg_id BIGINT NULL
action TEXT NOT NULL
entity_type TEXT NOT NULL
entity_id UUID NULL
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
ip_address INET NULL
user_agent TEXT NULL
```

Required audit actions:

- `admin.login_link_created`
- `admin.login_success`
- `admin.login_failed`
- `prompt.created`
- `prompt.restored`
- `tools_instruction.created`
- `tools_instruction.restored`
- `admin.created`
- `admin.role_changed`
- `admin.deactivated`

#### Scenario: Audit event recorded

- GIVEN an admin performs an auditable action
- WHEN the action completes
- THEN a row SHALL be inserted into `admin_audit_log` with the action name and relevant metadata

### Requirement: Database shall store admin notifications

The system SHALL create and maintain an `admin_notifications` table to store `send_to_admin` payloads regardless of whether `ADMIN_TELEGRAM_CHAT_ID` is configured:

```sql
id UUID PRIMARY KEY
trace_id TEXT NOT NULL
user_tg_id BIGINT NOT NULL
first_name TEXT NULL
last_name TEXT NULL
username TEXT NULL
telegram_link TEXT NULL
language_code TEXT NULL
comment TEXT NOT NULL
payload JSONB NOT NULL DEFAULT '{}'::jsonb
delivered BOOLEAN NOT NULL DEFAULT FALSE
delivery_error TEXT NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

#### Scenario: Notification persisted

- GIVEN `send_to_admin` is invoked by the agent
- WHEN the tool completes
- THEN a row SHALL be inserted into `admin_notifications` with the full payload

### Requirement: Database shall store censor runs

The system SHALL create and maintain a `censor_runs` table with the following fields:

```sql
id UUID PRIMARY KEY
trace_id TEXT NOT NULL
user_tg_id BIGINT NULL
draft_response TEXT NOT NULL
final_response TEXT NOT NULL
censor_prompt_version INTEGER NOT NULL
censor_model TEXT NULL
status TEXT NOT NULL CHECK (status IN ('success', 'error', 'skipped'))
error TEXT NULL
duration_ms INTEGER NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

#### Scenario: Censor run recorded

- GIVEN censor is enabled and processes a response
- WHEN the censor LLM call completes
- THEN a row SHALL be inserted into `censor_runs` with status `success` or `error`

### Requirement: Database shall store application settings

The system SHALL create and maintain an `app_settings` table with the following fields:

```sql
key TEXT PRIMARY KEY
value TEXT NOT NULL
updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
updated_by_admin_id UUID NULL REFERENCES admins(id)
```

Required settings keys:

- `censor_enabled` — `true` or `false`.

#### Scenario: Setting updated

- GIVEN an admin toggles a setting
- WHEN the update completes
- THEN the `app_settings` row SHALL be upserted with the new value and `updated_at` timestamp
