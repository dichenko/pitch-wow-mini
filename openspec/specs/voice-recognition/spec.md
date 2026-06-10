# Spec: voice-recognition

## Purpose

Optional voice and audio message transcription for the Telegram bot. Uses OpenAI STT as primary provider with Aisha STT as fallback (primarily for Uzbek). Includes ffmpeg audio normalization, size/duration limits, temp file cleanup, best-effort error handling, and best-effort TTS voice reply after transcription.

## Requirements

### Requirement: Bot shall support voice message transcription

The system SHALL support Telegram voice and audio message transcription to text, controlled via `VOICE_ENABLED` env (default: `false`).

#### Scenario: Voice recognition enabled

- **WHEN** `VOICE_ENABLED=true` and user sends a voice or audio message
- **THEN** the bot SHALL download the file, normalize it using ffmpeg, and attempt transcription through the STT pipeline

#### Scenario: Voice recognition disabled

- **WHEN** `VOICE_ENABLED=false` and user sends a voice or audio message
- **THEN** the bot SHALL politely ask the user to send their message as text

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

### Requirement: STT provider shall be abstracted

The system SHALL define common speech-layer provider protocols for STT and TTS and route providers by normalized language through the speech factory.

Implementations: `OpenAISpeechProvider`, `AishaSpeechProvider`, `YandexSpeechKitProvider`, `AzureSpeechProvider`, and `MockSpeechProvider`.

#### Scenario: Adding new speech provider

- **WHEN** a developer implements the speech-layer provider protocol for a new provider
- **THEN** the new provider SHALL be pluggable into speech routing without changing Telegram handler provider payload logic

### Requirement: Audio files shall be handled safely

The system SHALL normalize audio with ffmpeg (16kHz mono WAV) before STT.

Limits: `VOICE_MAX_AUDIO_SIZE_MB` (default: 25 MB), `VOICE_MAX_DURATION_SEC` (default: 120 sec). Temp files in `VOICE_TEMP_DIR` (default: `/tmp/assistant-audio`).

#### Scenario: Audio normalization

- **WHEN** bot downloads a Telegram voice file
- **THEN** ffmpeg SHALL convert it: `-ar 16000 -ac 1`

#### Scenario: Temp files cleaned up

- **WHEN** audio processing is complete (success or failure)
- **THEN** all temporary audio files SHALL be deleted

#### Scenario: Audio exceeds size limit

- **WHEN** a voice message is larger than `VOICE_MAX_AUDIO_SIZE_MB`
- **THEN** the bot SHALL reject the file with an explanation of the size limit

#### Scenario: Audio exceeds duration limit

- **WHEN** a voice message is longer than `VOICE_MAX_DURATION_SEC`
- **THEN** the bot SHALL reject the file with an explanation of the duration limit

### Requirement: Voice recognition shall extract duration via ffprobe

After normalizing audio, the system SHALL use ffprobe to check duration before proceeding with STT.

#### Scenario: Duration check

- **WHEN** audio has been normalized and ffprobe returns a duration value
- **THEN** the duration SHALL be compared against `VOICE_MAX_DURATION_SEC`
- **THEN** if exceeded, the message SHALL be rejected before STT

### Requirement: STT errors shall not break conversations

STT integration SHALL be best-effort. Errors SHALL be logged locally. The user SHALL receive a clear message asking to send text instead. Error details SHALL NOT be exposed to the user.

#### Scenario: STT error

- **WHEN** an STT provider returns an error
- **THEN** the bot conversation SHALL continue normally
- **THEN** STT error details SHALL NOT be visible to the user

### Requirement: Voice pipeline shall send best-effort TTS reply

After successful STT and assistant response generation, the voice pipeline SHALL send the text answer first and then attempt to send a Telegram voice reply for the same text.

#### Scenario: Text is sent before voice

- **WHEN** user sends a voice message and the assistant produces a text response
- **THEN** bot SHALL send the text response before starting TTS

#### Scenario: Voice synthesis succeeds

- **WHEN** TTS synthesis and OGG/Opus preparation succeed
- **THEN** bot SHALL send the synthesized result via Telegram `answer_voice`

#### Scenario: Voice synthesis fails

- **WHEN** TTS synthesis or conversion fails after text has been sent
- **THEN** bot SHALL keep the conversation alive and SHALL send a localized text notice about voice synthesis failure

#### Scenario: Transcript language is uncertain

- **WHEN** STT succeeds and the transcript language cannot be confidently detected
- **THEN** bot SHALL send the text response and skip TTS without failing the conversation

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
