## 1. Admin Welcome Page

- [x] 1.1 Create `apps/admin/app/routers/welcome.py` router (GET /admin/welcome, POST /admin/welcome/save, POST /admin/welcome/restore/{version_id}), mirroring system_prompt.py pattern with `kind="welcome_message"`
- [x] 1.2 Register welcome router in `apps/admin/app/main.py` (`app.include_router(welcome.router)`)
- [x] 1.3 Add "Welcome Message" sidebar link in `apps/admin/app/templates/base.html`

## 2. Seed Default Welcome Message

- [x] 2.1 Add `welcome_message` seeding to `apps/bot/app/services/seed_service.py` — create initial PromptVersion with kind="welcome_message" and sensible default text if none exists

## 3. Bot Handlers

- [x] 3.1 Create `apps/bot/app/services/welcome_service.py` with `get_active_welcome_message()` and `save_welcome_to_history(user_tg_id, thread_id, text, trace_id)` functions
- [x] 3.2 Update `apps/bot/app/handlers/start.py` — after history reset, fetch active welcome, send it (no LLM), persist to history
- [x] 3.3 Update `apps/bot/app/handlers/restart.py` — after history reset, fetch active welcome, send it (no LLM), persist to history

## 4. Verify

- [ ] 4.1 Push to master, wait for CI/CD deploy
- [ ] 4.2 Test: send /start, verify welcome message arrives, send text message, verify LLM context includes welcome
