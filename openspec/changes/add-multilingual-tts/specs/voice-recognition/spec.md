## MODIFIED Requirements

### Requirement: STT pipeline shall use OpenAI as primary provider

The system SHALL use OpenAI STT (`gpt-4o-transcribe` by default) for normalized `ru` and `en` voice messages.

Configurable via: `OPENAI_STT_MODEL`, `OPENAI_STT_LANGUAGE`, `OPENAI_STT_TIMEOUT_MS`.

#### Scenario: Russian or English voice recognized by OpenAI

- **WHEN** user sends Telegram voice and the normalized language is `ru` or `en`
- **THEN** bot SHALL process the audio through OpenAI STT and process the returned text as a regular user message

### Requirement: STT pipeline shall use Aisha as fallback provider

The system SHALL use Aisha STT for normalized `uz` voice messages. It SHALL NOT expose provider errors to the user.

Configurable via: `AISHA_API_KEY`, `AISHA_BASE_URL`, `AISHA_STT_TIMEOUT_MS`, `AISHA_STT_LANGUAGE` (default: `uz`).

#### Scenario: Uzbek voice recognized by Aisha

- **WHEN** user sends voice message and the normalized language is `uz`
- **THEN** bot SHALL call Aisha STT and process its transcript as a regular user message

#### Scenario: STT provider fails

- **WHEN** the routed STT provider fails or returns empty
- **THEN** bot SHALL send: "Не удалось распознать голосовое сообщение, пожалуйста, отправьте текстом"
- **THEN** STT failures SHALL be logged

### Requirement: STT provider shall be abstracted

The system SHALL define common speech-layer provider protocols for STT and TTS and route providers by normalized language through the speech factory.

Implementations: `OpenAISpeechProvider`, `AishaSpeechProvider`, `YandexSpeechKitProvider`, `AzureSpeechProvider`, and `MockSpeechProvider`.

#### Scenario: Adding new speech provider

- **WHEN** a developer implements the speech-layer provider protocol for a new provider
- **THEN** the new provider SHALL be pluggable into speech routing without changing Telegram handler provider payload logic

## ADDED Requirements

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
