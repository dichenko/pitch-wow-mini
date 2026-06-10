## MODIFIED Requirements

### Requirement: STT pipeline shall use OpenAI as primary provider

The system SHALL use OpenAI STT (`gpt-4o-transcribe` by default) for users whose stored preferred language is Russian or English.

Configurable via: `OPENAI_STT_MODEL`, `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS`.

#### Scenario: Russian voice recognized by OpenAI

- **WHEN** user has preferred language `ru` and sends Telegram voice
- **THEN** bot SHALL transcribe the normalized audio through OpenAI STT
- **THEN** bot SHALL process that transcript as a regular user message with response language `ru`
- **THEN** bot SHALL NOT call Aisha STT

#### Scenario: English voice recognized by OpenAI

- **WHEN** user has preferred language `en` and sends Telegram voice
- **THEN** bot SHALL transcribe the normalized audio through OpenAI STT
- **THEN** bot SHALL process that transcript as a regular user message with response language `en`
- **THEN** bot SHALL NOT call Aisha STT

### Requirement: STT pipeline shall use Aisha as fallback provider

The system SHALL NOT use Aisha as a generic fallback for Russian or English voice input. The system SHALL use Aisha STT only when the user's stored preferred language is Uzbek.

Configurable via: `AISHA_API_KEY`, `AISHA_BASE_URL`, `AISHA_STT_TIMEOUT_MS`, `AISHA_STT_LANGUAGE` (default: `uz`).

#### Scenario: Uzbek voice recognized by Aisha

- **WHEN** user has preferred language `uz` and sends Telegram voice
- **THEN** bot SHALL transcribe the normalized audio through Aisha STT
- **THEN** bot SHALL process that transcript as a regular user message with response language `uz`
- **THEN** bot SHALL NOT call OpenAI STT

#### Scenario: Uzbek Aisha STT fails

- **WHEN** user has preferred language `uz` and Aisha STT fails or returns empty text
- **THEN** bot SHALL send a localized message asking the user to send text or try again
- **THEN** bot SHALL NOT fall back to OpenAI STT for that Uzbek voice message
- **THEN** STT failures SHALL be logged

#### Scenario: Both STT providers fail

- **WHEN** the selected language's STT provider fails or returns empty
- **THEN** bot SHALL send a localized recognition failure message for the user's stored language
- **THEN** STT failures SHALL be logged

## ADDED Requirements

### Requirement: Voice processing shall use stored preferred language

The system SHALL route voice input and voice output from the user's stored preferred language, not from automatic transcript language detection.

#### Scenario: Voice message with stored language

- **WHEN** user sends a voice or audio message and `user_profiles.preferred_language` is set
- **THEN** the bot SHALL use that stored language for STT provider selection
- **THEN** the bot SHALL pass that stored language to the text response pipeline
- **THEN** the bot SHALL use that stored language for TTS provider selection

#### Scenario: Voice message without stored language

- **WHEN** user sends a voice or audio message and `user_profiles.preferred_language` is missing
- **THEN** the bot SHALL ask the user to choose a language
- **THEN** the bot SHALL NOT run STT or TTS for that message

### Requirement: TTS pipeline shall route by stored preferred language

The system SHALL select TTS provider by stored preferred language.

#### Scenario: Uzbek TTS uses Aisha

- **WHEN** user preferred language is `uz` and the bot has a text response
- **THEN** TTS SHALL use Aisha TTS
- **THEN** OpenAI TTS and Yandex TTS SHALL NOT be used

#### Scenario: Russian TTS uses Yandex

- **WHEN** user preferred language is `ru` and the bot has a text response
- **THEN** TTS SHALL use Yandex SpeechKit TTS
- **THEN** Aisha TTS and OpenAI TTS SHALL NOT be used

#### Scenario: English TTS uses OpenAI

- **WHEN** user preferred language is `en` and the bot has a text response
- **THEN** TTS SHALL use OpenAI TTS
- **THEN** Aisha TTS and Yandex TTS SHALL NOT be used

### Requirement: Text response shall match stored preferred language

The system SHALL instruct the LLM to answer in the user's stored preferred language for both text and voice input.

#### Scenario: Uzbek user receives Uzbek response

- **WHEN** user preferred language is `uz` and the user sends text or voice
- **THEN** the LLM request SHALL include an instruction to answer in Uzbek Latin script
- **THEN** the assistant response SHALL be sent as text before any best-effort voice response

#### Scenario: Russian user receives Russian response

- **WHEN** user preferred language is `ru` and the user sends text or voice
- **THEN** the LLM request SHALL include an instruction to answer in Russian
- **THEN** the assistant response SHALL be sent as text before any best-effort voice response

#### Scenario: English user receives English response

- **WHEN** user preferred language is `en` and the user sends text or voice
- **THEN** the LLM request SHALL include an instruction to answer in English
- **THEN** the assistant response SHALL be sent as text before any best-effort voice response
