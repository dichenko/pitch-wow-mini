## Why

Voice recognition currently stops at STT and routes provider behavior inside the Telegram handler. The bot needs multilingual TTS as a separate speech layer so voice replies can be added without coupling handlers to provider-specific APIs.

## What Changes

- Add a speech layer with shared language normalization, STT/TTS result types, provider protocols, and `SpeechProviderError`.
- Add TTS provider adapters for OpenAI, Aisha, Yandex SpeechKit, Azure, and a mock provider for tests.
- Route providers by normalized language: `uz` uses Aisha, `ru` uses Yandex TTS and OpenAI STT, `en` uses OpenAI.
- Add temporary audio file helpers, file cleanup, size validation, and OGG/Opus conversion for Telegram voice.
- Extend the voice pipeline so text is sent first, then synthesized voice is sent best-effort.
- Add language-specific TTS prompt lookup and environment settings for provider configuration.
- Add focused tests for routing, payloads, cleanup, text fallback, and conversion behavior.

## Capabilities

### New Capabilities

- `multilingual-tts`: Speech-layer TTS interfaces, provider routing, provider adapters, temp-file handling, text preparation, and safe fallback behavior.

### Modified Capabilities

- `voice-recognition`: Voice message handling now uses the shared speech factory for STT and sends a best-effort TTS voice reply after the primary text answer.

## Non-goals

- No admin UI for editing TTS prompts in this change.
- No database schema migration for rich voice metadata beyond existing dialogue history behavior.
- No runtime verification against real external provider accounts or API keys.

## Impact

- Affects `apps/bot/app/config.py`, `.env.example`, Telegram voice/message handlers, and new `apps/bot/app/speech/*` modules.
- Adds tests under `tests/`.
- Requires `ffmpeg` for Telegram voice normalization/conversion, as current voice handling already does.
