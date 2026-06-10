## Why

The bot will use an explicit preferred language selected on `/start`, so the welcome message must match that language. A single global welcome text is no longer enough once Uzbek, Russian, and English users follow different localized onboarding paths.

## What Changes

- Replace the single active welcome message with three language-specific welcome messages: Uzbek, Russian, and English.
- Admin panel SHALL allow editing each language's welcome message independently.
- Each language-specific welcome message SHALL be versioned and restorable from history.
- Bot welcome delivery SHALL select the active welcome text by the user's stored preferred language.
- Default seed data SHALL include sensible welcome messages for all three supported languages.
- Missing language-specific content SHALL fall back to a safe default in the requested language.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `welcome-message`: welcome retrieval and delivery become language-specific.
- `prompt-versioning`: welcome prompt versioning expands from one `welcome_message` kind to separate language-specific welcome kinds.
- `admin-panel`: Welcome Message section changes from a single editor to three language-specific editors with history/restore.
- `database`: prompt version constraints and seed behavior must support language-specific welcome prompt kinds.

## Non-goals

- No automatic translation of welcome messages.
- No per-user custom welcome messages beyond language selection.
- No change to system prompt, tools instruction, or censor prompt versioning.
- No direct production-server updates; implementation should go through local code, GitHub, and automated deploy.

## Impact

- Admin welcome routes, forms, templates, and services.
- Bot welcome service and `/start`/language-selection flow.
- PromptVersion model constraint, Alembic migration, and seed service.
- Tests for admin editing, version restore, seeding, and language-specific welcome selection.
