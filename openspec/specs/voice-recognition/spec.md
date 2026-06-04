# Spec: voice-recognition

## Purpose

Optional voice and audio message transcription for the Telegram bot. Uses OpenAI STT as primary provider with Aisha STT as fallback (primarily for Uzbek). Includes ffmpeg audio normalization, size/duration limits, temp file cleanup, and best-effort error handling.

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

The system SHALL use OpenAI STT (`gpt-4o-transcribe` by default) as primary.

Configurable via: `OPENAI_STT_MODEL`, `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS`.

#### Scenario: Voice recognized by OpenAI

- **WHEN** user sends Telegram voice and OpenAI STT returns text successfully
- **THEN** bot SHALL process that text as a regular user message without calling Aisha STT

### Requirement: STT pipeline shall use Aisha as fallback provider

The system SHALL fall back to Aisha STT when OpenAI STT fails or returns empty.

Configurable via: `AISHA_API_KEY`, `AISHA_BASE_URL`, `AISHA_STT_TIMEOUT_MS`, `AISHA_STT_LANGUAGE` (default: `uz`).

#### Scenario: OpenAI fails, Aisha succeeds

- **WHEN** user sends voice message and OpenAI STT fails or returns empty
- **THEN** bot SHALL call Aisha STT and process its transcript as a regular user message

#### Scenario: Both STT providers fail

- **WHEN** user sends unsupported audio and both OpenAI and Aisha STT providers fail
- **THEN** bot SHALL send: "Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом"
- **THEN** STT failures SHALL be logged

### Requirement: STT provider shall be abstracted

The system SHALL define a common `BaseSttProvider` interface with `transcribe(audio_path: str) -> str | None`.

Implementations: `OpenAISttProvider` (primary), `AishaSttProvider` (fallback).

#### Scenario: Adding new STT provider

- **WHEN** a developer implements `BaseSttProvider` for a new provider
- **THEN** the new provider SHALL be pluggable into the STT pipeline without changing pipeline logic

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
