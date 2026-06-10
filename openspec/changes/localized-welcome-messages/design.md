## Context

The bot currently stores one active welcome message in `prompt_versions` with `kind="welcome_message"`. The admin panel exposes one Welcome Message editor, and the bot service reads that single active version for `/start` and `/restart`. With persisted user language selection, welcome text must become language-specific while keeping the existing append-only versioning model.

## Goals / Non-Goals

**Goals:**
- Provide separate active welcome messages for `uz`, `ru`, and `en`.
- Let admins edit and restore each language independently.
- Preserve append-only prompt versioning and audit behavior.
- Let bot welcome delivery select the active text by stored preferred language.
- Seed defaults for all supported languages.

**Non-Goals:**
- No automatic translation between languages.
- No per-user custom welcome text.
- No changes to system prompt, tools instruction, or censor prompt semantics.
- No server-side hotfix workflow; implementation remains local code followed by GitHub deployment.

## Decisions

1. **Use separate prompt kinds per language.**
   - Add `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en`.
   - Rationale: each language gets independent active version, history, authorship, change notes, and restore.
   - Alternative considered: one `welcome_message` JSON blob with all languages. Rejected because a small edit to one language would version all languages together and make restore ambiguous.

2. **Keep `/admin/welcome` as one management page.**
   - The page should render three language sections or tabs, one for each supported language.
   - Each section saves/restores only its corresponding prompt kind.
   - Rationale: admins manage one conceptual feature, but version history remains language-specific.

3. **Expose language-aware welcome service API.**
   - Replace `get_active_welcome_message()` with a language-aware function such as `get_active_welcome_message(language)`.
   - The service maps `ru`, `uz`, `en` to prompt kinds and safe defaults.
   - Rationale: callers should not know PromptVersion kind naming details.

4. **Migrate existing single welcome content to Russian.**
   - During migration or seed, preserve any existing `welcome_message` as the initial/active Russian welcome if no `welcome_message_ru` exists.
   - Seed Uzbek and English defaults when missing.
   - Rationale: current production welcome is Russian-oriented and should not be discarded.

## Risks / Trade-offs

- Existing DB check constraint blocks new kinds -> Add Alembic migration before code uses new kinds.
- Admin page becomes more complex -> Keep one route but split form actions by language.
- Missing localized content could block `/start` -> Always provide in-code safe defaults by language.
- Existing tests expect `welcome_message` -> Update tests to verify the three new kinds and optional legacy migration.
