## ADDED Requirements

### Requirement: Speech layer shall define shared language and provider contracts

The system SHALL define supported languages `ru`, `uz`, and `en`, normalize unknown or empty language values to `ru`, and expose common STT/TTS provider protocols with structured result dataclasses.

#### Scenario: Unknown language is normalized

- **WHEN** code passes `None` or an unsupported language to the speech layer
- **THEN** the speech layer SHALL return `ru`

#### Scenario: TTS provider returns structured result

- **WHEN** a TTS provider synthesizes speech
- **THEN** it SHALL return a local file path, MIME type, audio format, provider name, model, and optional voice

### Requirement: Speech factory shall route providers by normalized language

The system SHALL route STT and TTS providers through a factory so Telegram handlers do not know provider-specific APIs.

#### Scenario: TTS routing by language

- **WHEN** the normalized language is `uz`, `ru`, or `en`
- **THEN** TTS SHALL route respectively to Aisha, Yandex SpeechKit, or OpenAI

#### Scenario: STT routing by language

- **WHEN** the normalized language is `uz`, `ru`, or `en`
- **THEN** STT SHALL route `uz` to Aisha and `ru`/`en` to OpenAI

### Requirement: TTS providers shall prepare text safely

The system SHALL remove Markdown, URLs, emoji, and excessive whitespace before sending text to TTS providers. Provider-specific length limits SHALL be enforced before or during provider calls.

#### Scenario: Empty prepared text

- **WHEN** text preparation results in an empty string
- **THEN** synthesis SHALL fail with `SpeechProviderError` before calling an external API

#### Scenario: Russian speech replacements

- **WHEN** Yandex TTS receives text containing currency or percent symbols
- **THEN** the provider SHALL replace them with readable Russian words before calling Yandex

### Requirement: TTS provider adapters shall implement provider-specific payloads

The system SHALL provide TTS adapters for OpenAI, Aisha, Yandex SpeechKit, Azure, and a mock provider for tests.

#### Scenario: Aisha TTS payload

- **WHEN** Aisha synthesizes Uzbek speech
- **THEN** it SHALL send multipart form fields for transcript, language, model, mood, and speed, then download `audio_path`

#### Scenario: Yandex TTS payload

- **WHEN** Yandex synthesizes Russian speech
- **THEN** it SHALL send form parameters for text, lang, voice, emotion, speed, and format

#### Scenario: Azure TTS SSML

- **WHEN** Azure synthesizes speech
- **THEN** it SHALL escape user text before embedding it in SSML

### Requirement: TTS audio shall be compatible with Telegram voice

The system SHALL convert non-OGG/non-Opus TTS output to OGG/Opus using ffmpeg before sending Telegram voice.

#### Scenario: Provider returns WAV

- **WHEN** a TTS provider returns a `.wav` file
- **THEN** the system SHALL convert it to `.ogg` with Opus settings before `answer_voice`

### Requirement: TTS errors shall preserve text replies

The system SHALL send the assistant text response before TTS and SHALL treat voice synthesis as best-effort.

#### Scenario: TTS provider fails

- **WHEN** the assistant text response has been sent and TTS raises `SpeechProviderError`
- **THEN** the user SHALL keep the text answer and receive a localized message that voice synthesis is unavailable

### Requirement: Temporary audio files shall be cleaned up

The system SHALL create speech temporary files under the configured speech temp directory and delete input, original TTS, and converted TTS files after success or failure.

#### Scenario: Cleanup after voice handling

- **WHEN** voice handling completes or raises an error
- **THEN** all created temporary audio files SHALL be removed if they exist
