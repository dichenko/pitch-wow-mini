## 1. Speech Layer

- [x] 1.1 Create shared speech contracts, language normalization, and errors
- [x] 1.2 Add temp-file helpers, file-size validation, text preparation, cleanup, and OGG conversion
- [x] 1.3 Implement OpenAI, Aisha, Yandex, Azure, and mock speech providers
- [x] 1.4 Implement provider factory and language routing

## 2. Bot Integration

- [x] 2.1 Add bot settings and `.env.example` entries for TTS providers and speech temp files
- [x] 2.2 Refactor text processing to return the final assistant response after sending text
- [x] 2.3 Refactor voice handler to use speech factory for STT and best-effort TTS
- [x] 2.4 Add language-specific TTS prompt lookup

## 3. Verification

- [x] 3.1 Add unit tests for language routing, provider payloads, text preparation, and temp cleanup
- [x] 3.2 Add unit tests for voice pipeline text-first fallback behavior
- [x] 3.3 Run OpenSpec validation and relevant pytest suite
