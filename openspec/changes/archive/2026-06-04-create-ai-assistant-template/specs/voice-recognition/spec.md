# Spec Delta: voice-recognition

## Capability

```text
voice-recognition
```

## ADDED Requirements

### Requirement: Bot shall recognize voice messages

The system SHALL support Telegram voice and audio message transcription to text.

Voice recognition SHALL be optional and controlled through env:

```env
VOICE_ENABLED=false
```

#### Scenario: Voice recognition enabled

- GIVEN `VOICE_ENABLED=true`
- WHEN user sends a voice or audio message to the bot
- THEN the bot SHALL download the file
- AND normalize it using ffmpeg
- AND attempt transcription through the STT pipeline

#### Scenario: Voice recognition disabled

- GIVEN `VOICE_ENABLED=false`
- WHEN user sends a voice or audio message
- THEN the bot SHALL politely ask the user to send their message as text

### Requirement: STT pipeline shall use OpenAI as primary provider

The system SHALL use OpenAI STT as the primary speech-to-text provider.

Required env:

```env
OPENAI_STT_MODEL=gpt-4o-transcribe
OPENAI_STT_LANGUAGE=
OPENAI_STT_TIMEOUT_MS=60000
```

#### Scenario: Voice recognized by OpenAI

- GIVEN user sends Telegram voice
- WHEN OpenAI STT returns text
- THEN bot SHALL process that text as a regular user message
- AND Aisha STT SHALL NOT be called

### Requirement: STT pipeline shall use Aisha as fallback provider

The system SHALL fall back to Aisha STT API when OpenAI STT fails or returns empty/uncertain results.

Required env:

```env
AISHA_API_KEY=
AISHA_BASE_URL=
AISHA_STT_TIMEOUT_MS=60000
AISHA_STT_LANGUAGE=uz
```

Aisha STT is intended primarily for Uzbek language recognition.

#### Scenario: OpenAI fails, Aisha succeeds

- GIVEN user sends Uzbek voice
- WHEN OpenAI STT fails or returns empty text
- THEN bot SHALL call Aisha STT
- AND process Aisha transcript as a regular user message

#### Scenario: Both STT providers fail

- GIVEN user sends unsupported/unclear audio
- WHEN both OpenAI and Aisha STT providers fail
- THEN bot SHALL send user-friendly failure message:
  ```text
  Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом
  ```
- AND log STT failure to `censor_runs` or dedicated log

### Requirement: STT provider shall be abstracted

The system SHALL define a common STT provider interface.

Implementations:

- `OpenAISttProvider` — primary.
- `AishaSttProvider` — fallback.

#### Scenario: Adding new STT provider

- GIVEN a developer wants to add a new STT provider
- WHEN the developer implements the STT provider interface
- THEN the new provider SHALL be pluggable into the STT pipeline without changing the pipeline logic

### Requirement: Audio files shall be handled safely

The system SHALL use ffmpeg to normalize audio before STT processing.

Required env:

```env
VOICE_TEMP_DIR=/tmp/assistant-audio
VOICE_MAX_AUDIO_SIZE_MB=25
VOICE_MAX_DURATION_SEC=120
```

#### Scenario: Audio normalization

- GIVEN bot downloads a Telegram voice file
- WHEN the file is ready for STT
- THEN ffmpeg SHALL convert it to a normalized format suitable for the STT provider

#### Scenario: Temp files cleaned up

- GIVEN audio processing is complete (success or failure)
- WHEN the STT pipeline finishes
- THEN all temporary audio files SHALL be deleted from `VOICE_TEMP_DIR`

#### Scenario: Audio exceeds size limit

- GIVEN a voice message larger than `VOICE_MAX_AUDIO_SIZE_MB`
- WHEN the bot attempts to process it
- THEN the bot SHALL reject the file
- AND send user a message explaining the size limit

#### Scenario: Audio exceeds duration limit

- GIVEN a voice message longer than `VOICE_MAX_DURATION_SEC`
- WHEN the bot attempts to process it
- THEN the bot SHALL reject the file
- AND send user a message explaining the duration limit

### Requirement: Voice transcription metadata shall be preserved

The system SHALL store voice transcription metadata in the message log.

Required metadata:

- original Telegram `file_id`;
- audio duration (if available);
- original MIME type (if available);
- STT provider used: `openai` or `aisha`;
- detected language (if available);
- `trace_id`;
- transcription status: `success`, `failed`, `skipped`;
- normalized audio path (temporary only, not persisted long-term).

#### Scenario: Voice metadata stored in log

- GIVEN a voice message is processed
- WHEN transcription completes
- THEN the message log SHALL contain file_id, duration, MIME type, STT provider used, detected language, trace_id and transcription status

### Requirement: STT errors shall not break conversations

STT integration SHALL be best-effort.

#### Scenario: STT error

- GIVEN an STT provider returns an error
- WHEN the error occurs
- THEN the error SHALL be logged locally
- AND the user SHALL receive a clear message asking them to send text instead
- AND the bot conversation SHALL continue normally
- AND STT error details SHALL NOT be exposed to the user

### Requirement: Voice integration shall be documented

The README SHALL include:

- how to enable voice recognition;
- how to configure OpenAI STT;
- how to configure Aisha STT fallback;
- ffmpeg dependency requirement;
- temp file cleanup behavior;
- size and duration limits.

#### Scenario: Voice documentation present

- GIVEN a developer opens the README
- WHEN they look for voice recognition documentation
- THEN all items listed above SHALL be present and actionable

