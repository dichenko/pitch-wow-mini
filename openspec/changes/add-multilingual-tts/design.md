## Context

The bot already supports Telegram voice/audio input, but the handler downloads, normalizes, probes, and chooses STT providers directly. TTS must be introduced without growing handler-level provider conditionals. The requested architecture mirrors a speech layer with provider adapters, language routing, temporary-file management, and best-effort voice output.

## Goals / Non-Goals

**Goals:**

- Introduce a shared `apps.bot.app.speech` package for language normalization, STT/TTS protocols, provider results, errors, provider factory, temp files, and provider adapters.
- Route `uz` to Aisha, `ru` to Yandex TTS/OpenAI STT, and `en` to OpenAI.
- Keep the text response as the primary result and add TTS as a best-effort follow-up.
- Keep secrets in settings and avoid logging API keys or authorization headers.
- Cover routing, provider payloads, temp cleanup, conversion, and fallback behavior with tests.

**Non-Goals:**

- Building admin screens for TTS prompt editing.
- Persisting rich voice metadata in a new schema.
- Guaranteeing live provider success without configured credentials.

## Decisions

1. Create a new speech package instead of extending `services/stt`.
   - Rationale: TTS needs shared concepts across STT and TTS, including language routing and errors. A dedicated package avoids mixing new provider contracts with the older STT-only interface.
   - Alternative considered: keep `services/stt` and add `services/tts`; this leaves routing split across handlers or duplicate factories.

2. Return structured result dataclasses from providers.
   - Rationale: handlers need provider/model/format metadata and local audio paths for cleanup and Telegram sending.
   - Alternative considered: providers return raw strings/bytes; this makes conversion and metadata tracking harder.

3. Send text before TTS.
   - Rationale: the assistant response is the primary product. Provider outages must not hide the answer from the user.
   - Alternative considered: wait for TTS before sending anything; this increases latency and makes TTS a blocking dependency.

4. Use HTTP adapters with injectable clients.
   - Rationale: tests can assert payloads without real credentials or network calls.
   - Alternative considered: provider methods instantiate all clients internally; this is simpler but harder to test.

5. Keep Azure as an adapter but not default routing.
   - Rationale: it preserves the extension point without changing requested language routing.
   - Alternative considered: automatic Yandex-to-Azure fallback; this adds policy complexity and hidden costs.

## Risks / Trade-offs

- Provider API details can drift or differ by account -> adapters validate key response fields and convert errors to `SpeechProviderError`; tests lock the request shapes described in the task.
- `ffmpeg`/`ffprobe` must exist in runtime images -> current voice recognition already depends on them, and TTS conversion uses the same operational assumption.
- TTS can add latency and provider cost -> text is sent first, and voice is best-effort.
- Existing text handler did not return the generated response -> refactor it to return `str | None` while preserving current behavior for text messages.

## Migration Plan

1. Add speech package and settings.
2. Refactor voice handler to use speech factory and temp helpers.
3. Refactor text processing to return the final text after sending/saving it.
4. Add tests and update env examples.
5. Rollback by disabling `VOICE_ENABLED` or reverting the voice handler to STT-only behavior.

## Open Questions

- Whether future admin UI should expose `tts.prompts` editing alongside existing LLM settings.
- Whether voice reply metadata should become first-class database columns or remain best-effort/raw payload in a later change.
