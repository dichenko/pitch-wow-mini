## Context

The current voice flow transcribes audio first, tries to infer language from the transcript, then routes the response and TTS based on that inference. This breaks for short Uzbek Latin phrases because lexical detection is low confidence. The bot already has separate speech providers for Aisha, OpenAI, and Yandex, but there is no persisted per-user language preference that can serve as the routing source of truth.

## Goals / Non-Goals

**Goals:**
- Make user-selected language the authoritative source for text responses, STT, and TTS.
- Ask for language on `/start` with inline buttons before normal conversation begins.
- Persist the selected language by Telegram user ID.
- Route speech deterministically: Uzbek uses Aisha STT/TTS, Russian uses OpenAI STT and Yandex TTS, English uses OpenAI STT/TTS.
- Keep existing voice size/duration limits, ffmpeg normalization, temp cleanup, and text fallback behavior.

**Non-Goals:**
- Do not add an admin UI for changing user language.
- Do not rely on automatic language detection for primary routing.
- Do not change LLM provider selection or prompt versioning.
- Do not perform direct production-server changes; deployment remains GitHub-driven.

## Decisions

1. **Persist language in a dedicated user profile table.**
   - Create a `user_profiles` table keyed by `tg_id` with `preferred_language`, Telegram display fields, and timestamps.
   - Rationale: the setting belongs to the Telegram user, not to a dialogue turn or global app setting.
   - Alternative considered: storing language only in FSM/memory. Rejected because it would reset on deploy and would not support durable routing.

2. **Use `/start` as the language gate.**
   - On `/start`, if no language exists, show inline language buttons and do not send the welcome message yet.
   - After language selection, persist the profile language, reset the thread, then send and persist the welcome message.
   - Alternative considered: send welcome first and ask language later. Rejected because the welcome itself must be localized.

3. **Require language before message processing.**
   - Text and voice handlers must load the profile language before invoking the agent or speech providers.
   - If missing, they send the language menu.
   - Rationale: this prevents accidental Russian defaults for Uzbek users.

4. **Route STT/TTS from stored language, not transcript detection.**
   - `uz`: Aisha STT and Aisha TTS.
   - `ru`: OpenAI STT and Yandex TTS.
   - `en`: OpenAI STT and OpenAI TTS.
   - Automatic detection can remain only as a diagnostic or fallback for legacy code paths, not as the main routing decision.

5. **Inject language instruction into LLM requests.**
   - The message pipeline should pass the stored language to the agent and add a concise system instruction requiring the response in that language.
   - Rationale: provider routing alone does not ensure the text answer language.

## Risks / Trade-offs

- Existing users have no profile language → On their next `/start` or message, show the language menu and pause normal processing until selection.
- Users may choose the wrong language → They can run `/start` again to select another language; implementation can optionally add `/language` later.
- Aisha outage affects all Uzbek voice input/output → Keep localized text fallback and structured logs; do not silently switch Uzbek to OpenAI because the product requirement is Aisha-only for Uzbek.
- Migration adds a table → Use Alembic with a reversible migration and no destructive changes.
