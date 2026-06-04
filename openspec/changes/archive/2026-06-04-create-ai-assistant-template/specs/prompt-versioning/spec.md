# Spec Delta: prompt-versioning

## Capability

```text
prompt-versioning
```

## ADDED Requirements

### Requirement: System prompt shall be editable from admin panel

The system SHALL store the active system prompt in DB.

#### Scenario: Admin opens prompt page

- GIVEN admin has at least `read` role
- WHEN admin opens "System Prompt"
- THEN admin SHALL see the active prompt content
- AND metadata: version, author, created date

#### Scenario: Admin saves prompt

- GIVEN admin has `write` or `superadmin` role
- WHEN admin edits and saves system prompt
- THEN system SHALL create a new prompt version
- AND mark it as active
- AND keep all previous versions

### Requirement: Old system prompts shall be preserved

The system SHALL never overwrite old prompt versions.

Prompt version record SHALL include:

- id;
- kind = `system_prompt`;
- content;
- version number;
- active flag;
- created_by_admin_id;
- created_by_tg_id;
- created_by_username;
- created_at;
- change_note optional.

#### Scenario: History preserved after multiple edits

- GIVEN a system prompt has been edited three times
- WHEN admin views the version history
- THEN all three previous versions SHALL be present with their content, author and timestamp intact

### Requirement: Last three system prompts shall be restorable

The admin panel SHALL show the last three previous system prompt versions.

#### Scenario: Admin restores previous system prompt

- GIVEN admin has `write` or `superadmin` role
- WHEN admin clicks restore on one of the last three versions
- THEN system SHALL create a new active version copied from selected old version
- AND record who restored it and when
- AND old versions SHALL remain unchanged

### Requirement: Tools instruction shall be editable and versioned

The system SHALL store tools instruction separately from system prompt.

Tools instruction record SHALL use the same versioning mechanism with:

```text
kind = tools_instruction
```

#### Scenario: Admin edits tools instruction

- GIVEN admin has `write` or `superadmin` role
- WHEN admin saves tools instruction
- THEN system SHALL create a new active tools instruction version

#### Scenario: Admin restores previous tools instruction

- GIVEN admin has `write` or `superadmin` role
- WHEN admin restores one of the last three tools instruction versions
- THEN system SHALL create a new active version copied from selected version

### Requirement: Prompt assembly shall include tools instruction

The system SHALL concatenate active system prompt and active tools instruction for every agent request.

Required order:

```text
<non-editable core guardrails>

<active system prompt from DB>

# Tools usage instruction

<active tools instruction from DB>
```

#### Scenario: User sends message

- GIVEN active system prompt and active tools instruction exist
- WHEN bot handles user message
- THEN LangChain agent SHALL receive the assembled system message

### Requirement: Missing prompts shall have safe defaults

The system SHALL seed default prompt versions during initial setup or first startup.

#### Scenario: Empty DB

- GIVEN prompt_versions table is empty
- WHEN app starts
- THEN system SHALL insert default active system prompt
- AND default active tools instruction
- AND default active censor prompt

### Requirement: Censor prompt shall be editable and versioned

The system SHALL store the censor prompt separately from system prompt and tools instruction.

Censor prompt record SHALL use the same versioning mechanism with:

```text
kind = censor_prompt
```

#### Scenario: Admin edits censor prompt

- GIVEN admin has `write` or `superadmin` role
- WHEN admin saves censor prompt
- THEN system SHALL create a new active censor prompt version

#### Scenario: Admin restores previous censor prompt

- GIVEN admin has `write` or `superadmin` role
- WHEN admin restores one of the last three censor prompt versions
- THEN system SHALL create a new active version copied from selected version

#### Scenario: Censor prompt used in pipeline

- GIVEN censor is enabled and active censor prompt exists
- WHEN the main agent produces a draft response
- THEN the censor LLM SHALL receive the active censor prompt, the original user message, and the draft response
- AND the censor LLM SHALL return the final response text
