## 1. Database and Model

- [x] 1.1 Add Alembic migration to allow `welcome_message_ru`, `welcome_message_uz`, and `welcome_message_en` in `prompt_versions.kind`.
- [x] 1.2 Update `PromptVersion` model check constraint to include localized welcome kinds.
- [x] 1.3 Add constants/helpers mapping `ru`, `uz`, `en` to localized welcome prompt kinds.
- [x] 1.4 Add regression tests that localized welcome prompt kinds are accepted and unsupported kinds are rejected.

## 2. Seeding and Migration Behavior

- [x] 2.1 Update seed service to create default active welcome messages for Russian, Uzbek, and English.
- [x] 2.2 Preserve legacy `welcome_message` content as Russian welcome when `welcome_message_ru` is missing.
- [x] 2.3 Ensure seeding does not overwrite existing localized welcome versions.
- [x] 2.4 Add tests for empty DB seeding and legacy Russian welcome preservation.

## 3. Bot Welcome Service

- [x] 3.1 Replace single welcome lookup with language-aware `get_active_welcome_message(language)`.
- [x] 3.2 Add safe in-code default welcome text for each supported language.
- [x] 3.3 Update `/start` and `/restart` flows to request welcome text by stored preferred language.
- [x] 3.4 Ensure welcome history persistence stores the localized text actually sent to the user.
- [x] 3.5 Add tests for Russian, Uzbek, and English welcome lookup and fallback behavior.

## 4. Admin Welcome Page

- [x] 4.1 Update `/admin/welcome` view to load active welcome content and recent history for all three languages.
- [x] 4.2 Update welcome template to render Russian, Uzbek, and English editor sections or tabs.
- [x] 4.3 Add save endpoint behavior that creates a new version only for the submitted language.
- [x] 4.4 Add restore endpoint behavior that restores only the selected language's previous version.
- [x] 4.5 Preserve role-based permissions and CSRF validation for every localized save/restore action.
- [x] 4.6 Add admin route/template tests for view, save, restore, read-only permissions, and CSRF rejection.

## 5. Verification

- [x] 5.1 Update existing tests that expect a single `welcome_message` kind.
- [x] 5.2 Run targeted bot welcome, admin welcome, prompt versioning, and migration tests locally.
- [x] 5.3 Run full test suite locally if feasible.
- [x] 5.4 Verify `openspec status --change localized-welcome-messages` is apply-ready.
- [x] 5.5 Commit and push through GitHub so automated deployment applies the change.
