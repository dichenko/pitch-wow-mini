## 1. History Service

- [x] 1.1 Add `load_all_user_history(user_tg_id)` to `apps/bot/app/services/history_service.py` — loads all dialogue records for user across all threads, ordered chronologically

## 2. send_to_admin Enhancement

- [x] 2.1 After main notification, call `load_all_user_history()` to get records
- [x] 2.2 Format history as markdown string with user info header + conversation transcript
- [x] 2.3 Write markdown to temp file using `tempfile.NamedTemporaryFile`
- [x] 2.4 Send `.md` file to admin chat via `bot.send_document()` in a separate try/except
- [x] 2.5 Clean up temp file in `finally` block

## 3. Verify

- [ ] 3.1 Push to master, wait for CI/CD deploy
- [ ] 3.2 Trigger `send_to_admin`, verify `.md` file arrives in admin chat after notification
