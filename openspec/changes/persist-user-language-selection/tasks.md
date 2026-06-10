## 1. Data Model

- [x] 1.1 Add Alembic migration for `user_profiles` with `tg_id`, Telegram metadata, nullable `preferred_language`, timestamps, and language constraint.
- [x] 1.2 Add SQLAlchemy `UserProfile` model and indexes/constraints matching the migration.
- [x] 1.3 Add repository/service helpers to upsert user metadata, get preferred language, and save preferred language.
- [x] 1.4 Add tests for user profile creation, language persistence, invalid language rejection, and language loading.

## 2. Language Selection UX

- [x] 2.1 Add supported language constants and localized labels for Uzbek, Russian, and English.
- [x] 2.2 Add Telegram inline language keyboard with flag labels and callback payloads for `uz`, `ru`, and `en`.
- [x] 2.3 Update `/start` to show language selection when no preferred language exists.
- [x] 2.4 Add callback handler that persists selected language, resets the user thread, sends localized welcome, and stores welcome history.
- [x] 2.5 Update `/restart` behavior to preserve stored language and send localized welcome when language exists.
- [x] 2.6 Add tests for first `/start`, language callback, returning `/start`, and `/restart`.

## 3. Text Message Language Routing

- [x] 3.1 Update text handler to require preferred language before invoking the agent.
- [x] 3.2 Pass stored preferred language into `process_user_text` for every normal text message.
- [x] 3.3 Inject LLM response-language instruction from stored language rather than text detection.
- [x] 3.4 Add tests that text messages before language selection show the language menu and do not invoke the LLM.
- [x] 3.5 Add tests that Uzbek, Russian, and English profile languages produce matching LLM language instructions.

## 4. Voice STT/TTS Routing

- [x] 4.1 Update voice handler to require preferred language before downloading or normalizing audio.
- [x] 4.2 Route STT by stored language: `uz` to Aisha, `ru` and `en` to OpenAI.
- [x] 4.3 Route TTS by stored language: `uz` to Aisha, `ru` to Yandex, `en` to OpenAI.
- [x] 4.4 Remove transcript language detection as the primary voice routing decision.
- [x] 4.5 Keep ffmpeg normalization, duration/size checks, temp cleanup, and best-effort TTS fallback unchanged.
- [x] 4.6 Localize voice disabled, file too large, duration too long, STT failure, and TTS fallback messages by stored language.
- [x] 4.7 Add tests for Uzbek voice using Aisha STT/TTS only.
- [x] 4.8 Add tests for Russian voice using OpenAI STT and Yandex TTS only.
- [x] 4.9 Add tests for English voice using OpenAI STT/TTS only.

## 5. Regression and Deployment Readiness

- [x] 5.1 Update existing tests that assumed auto language detection in voice pipeline.
- [x] 5.2 Run targeted speech, start, callback, database, and message handler tests locally.
- [x] 5.3 Run full test suite locally if feasible.
- [x] 5.4 Verify `openspec status --change persist-user-language-selection` is apply-ready.
- [x] 5.5 Commit and push through GitHub so GitHub Actions performs deployment.
