## Why

Voice language detection from short Uzbek phrases is brittle and can cause the assistant to answer in Russian even when the user spoke Uzbek. The bot needs an explicit user language preference that controls conversation language and speech provider routing.

## What Changes

- `/start` SHALL present an inline language menu with Uzbek, Russian, and English buttons using flag labels.
- The selected language SHALL be persisted in the user's profile and reused for future text and voice interactions.
- If a user has no selected language, the bot SHALL ask them to choose before processing normal messages.
- Voice processing SHALL use the stored language instead of auto-detecting language from the transcript.
- STT/TTS routing SHALL be deterministic:
  - Uzbek: Aisha STT and Aisha TTS.
  - Russian: OpenAI STT and Yandex SpeechKit TTS.
  - English: OpenAI STT and OpenAI TTS.
- Existing best-effort error handling and temp audio cleanup SHALL remain.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `welcome-message`: `/start` changes from sending the welcome message immediately to first collecting language selection when needed.
- `database`: user profile storage must persist each Telegram user's selected language.
- `voice-recognition`: STT/TTS provider selection changes from transcript language detection/fallback to stored profile language routing.

## Non-goals

- No admin UI for changing a user's language.
- No automatic language detection as the primary routing mechanism.
- No change to the selected LLM provider or prompt management model.
- No direct production-server hotfixing; implementation should flow through GitHub deployment.

## Impact

- Bot handlers for `/start`, callbacks, text messages, and voice messages.
- Database schema/repositories for Telegram user profile language storage.
- Speech provider factory or voice pipeline routing.
- Tests for language selection, persistence, and provider routing.
