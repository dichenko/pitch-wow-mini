# План реализации Artifact Prompt Generator Worker

Источник требований: `codex_task_artifact_prompt_generator.md`.

Цель: после вызова `send_to_admin(comment)` создавать фоновую задачу генерации Markdown-пакета артефактов, обрабатывать ее отдельным worker-процессом, сохранять результат в БД и отправлять `.md` файл в админский Telegram-чат. Основной Telegram agent не должен генерировать артефакты и не должен ждать LLM-вызов worker'а.

## 1. Предварительная фиксация текущих паттернов

Перед кодом зафиксировать существующие точки расширения:

- Prompt management уже строится на `PromptVersion`, `prompt_service.py`, роутерах `apps/admin/app/routers/system_prompt.py`, `tools_instruction.py`, общем шаблоне `apps/admin/app/templates/prompt/edit.html` и audit log.
- `send_to_admin` уже сохраняет `AdminNotification`, отправляет сообщение админу и файл истории диалога.
- История диалога доступна через `load_user_thread_history(user_tg_id, thread_id)` и `load_latest_user_thread_history(user_tg_id)`.
- LLM создается через `apps/bot/app/services/llm_factory.py:create_llm`.
- Конфигурация bot-сервиса живет в `apps/bot/app/config.py`, значения берутся из `.env`.

## 2. База данных и модели

### 2.1 Расширить `PromptVersion.kind`

Файлы:

- `packages/shared/models/database.py`
- новая миграция в `migrations/versions/`
- при необходимости тесты в `tests/test_core.py`

Действия:

1. Добавить `artifact_generator_prompt` в `CheckConstraint("check_prompt_kind")`.
2. Создать Alembic migration после `004_user_profiles_and_localized_welcome.py`.
3. В migration безопасно пересоздать constraint:
   - `op.drop_constraint("check_prompt_kind", "prompt_versions", type_="check")`
   - `op.create_check_constraint(...)` с существующими prompt kinds плюс `artifact_generator_prompt`
4. В downgrade вернуть предыдущий список kind.

### 2.2 Добавить `ArtifactJob`

Файлы:

- `packages/shared/models/database.py`
- та же или отдельная новая migration

Модель:

- `id UUID primary key`
- `notification_id UUID nullable`
- `trace_id Text not null`
- `user_tg_id BigInteger not null`
- `thread_id Text not null`
- `status Text not null default "pending"`
- `input_comment Text nullable`
- `input_dialogue_md Text nullable`
- `artifact_prompt_version Integer nullable`
- `artifact_model_provider Text nullable`
- `artifact_model Text nullable`
- `output_markdown Text nullable`
- `error Text nullable`
- `attempts Integer not null default 0`
- `created_at DateTime(timezone=True) server_default=func.now()`
- `started_at DateTime(timezone=True) nullable`
- `finished_at DateTime(timezone=True) nullable`

Constraints/indexes:

- `check_artifact_job_status`: `pending`, `running`, `success`, `error`
- `ix_artifact_jobs_status_created_at(status, created_at)`
- `ix_artifact_jobs_trace_id(trace_id)`
- `ix_artifact_jobs_user_tg_id_created_at(user_tg_id, created_at)`

Решение по FK: для MVP можно оставить `notification_id` как nullable UUID без ORM relationship, чтобы не усложнять миграции. Если добавлять FK, использовать `admin_notifications.id` с `ondelete="SET NULL"`.

## 3. Seed default prompt

Файлы:

- `apps/bot/app/services/seed_service.py`

Действия:

1. Добавить константу `DEFAULT_ARTIFACT_GENERATOR_PROMPT`.
2. Содержимое взять из раздела 12 исходного задания без смысловых изменений.
3. В `seed_defaults()` добавить `_seed_prompt_if_missing(kind="artifact_generator_prompt", content=DEFAULT_ARTIFACT_GENERATOR_PROMPT, ...)`.
4. Проверить, что seed остается идемпотентным: если prompt kind уже есть, новая версия не создается.

Важно: в исходном markdown видны mojibake-символы для русских фрагментов. Перед вставкой default prompt лучше открыть файл в корректной кодировке/сверить источник, чтобы не засеять испорченный текст.

## 4. Admin page для Artifact Generator Prompt

Файлы:

- новый `apps/admin/app/routers/artifact_generator_prompt.py`
- `apps/admin/app/main.py`
- `apps/admin/app/templates/base.html`
- возможно `apps/admin/app/templates/dashboard.html`

Рекомендуемый путь:

- `GET /admin/prompts/artifact-generator`
- `POST /admin/prompts/artifact-generator/save`
- `POST /admin/prompts/artifact-generator/restore/{version_id}`

Действия:

1. Повторить поведение `system_prompt.py`, но с:
   - `kind="artifact_generator_prompt"`
   - `title="Artifact Generator Prompt"` или русским заголовком, если интерфейс переводится
   - `page_url="/admin/prompts/artifact-generator"`
2. Использовать общий шаблон `prompt/edit.html`.
3. Для просмотра требовать залогиненного admin.
4. Для save/restore использовать `require_role(request, "write")`.
5. Для версий использовать существующие `create_prompt_version()` и `restore_prompt_version()`.
6. Audit log:
   - action: `prompt.created` / `prompt.restored`
   - metadata: `{"kind": "artifact_generator_prompt", "version": new_version.version_number}`
7. Подключить router в `apps/admin/app/main.py`.
8. Добавить ссылку в sidebar.

Опциональное улучшение: обобщить `system_prompt.py` и `tools_instruction.py` в один reusable helper/router factory. Для MVP допустимо добавить отдельный маленький роутер по существующему паттерну.

## 5. Изменить `send_to_admin`

Файл:

- `apps/bot/app/agent/tools/send_to_admin.py`

Действия:

1. Импортировать `ArtifactJob`.
2. После создания `AdminNotification` вызвать `await session.flush()`, чтобы получить `notification.id`.
3. Добавить `ArtifactJob`:
   - `notification_id=notification.id`
   - `trace_id=trace_id`
   - `user_tg_id=tg_id`
   - `thread_id=current_thread_id or str(tg_id)`
   - `input_comment=comment`
   - `status="pending"`
4. Коммитить вместе с notification.
5. Если создание job падает, логировать exception, но сохранять текущий success response для agent.

Тонкий момент: сейчас `send_to_admin` сначала отправляет сообщения в Telegram, потом сохраняет notification. Требование говорит "после saving AdminNotification create ArtifactJob", но не требует менять порядок доставки. Для минимального риска оставить внешний flow, а внутри DB-блока создать обе записи в одной транзакции.

## 6. Artifact generation service

Файл:

- новый `apps/bot/app/services/artifact_generation.py`

Состав:

```python
@dataclass
class ArtifactGenerationResult:
    markdown: str
    prompt_version: int
    provider: str
    model: str
```

Функции:

- `async def get_active_artifact_prompt() -> tuple[str, int]`
- `async def generate_artifacts_from_dialogue(dialogue_md: str, comment: str | None, trace_id: str) -> ArtifactGenerationResult`

Действия:

1. Загрузить active `PromptVersion` для `artifact_generator_prompt`.
2. Если active prompt отсутствует, использовать `DEFAULT_ARTIFACT_GENERATOR_PROMPT` как fallback и version `0`, но это должно быть редким случаем после seed.
3. Определить provider/model по текущим настройкам:
   - `settings.text_llm_provider`
   - model: `openai_text_model`, `anthropic_model` или `mistral_model`
4. Создать LLM через `create_llm(provider, model, temperature=settings.artifact_generator_temperature)`.
5. Вызвать plain chat completion:
   - `SystemMessage(content=artifact_prompt)`
   - `HumanMessage(content=user_payload)`
6. Вернуть Markdown content и metadata.

Payload:

```markdown
# Founder Interview Dialogue

<dialogue_md>

# send_to_admin Comment

<comment or empty>
```

## 7. Artifact delivery service

Файл:

- новый `apps/bot/app/services/artifact_delivery.py`

Действия:

1. Создать временный `.md` файл через `tempfile.NamedTemporaryFile(delete=False, encoding="utf-8")`.
2. Имя: `pitch_wow_artifacts_<user_tg_id>_<job_id>.md`.
3. Отправить файл в `ADMIN_TELEGRAM_CHAT_ID` через `apps.bot.app.bot_instance.bot.send_document`.
4. Использовать `FSInputFile`.
5. Caption: `Pitch Wow artifacts generated for <user_tg_id>`.
6. В `finally` удалить temp file.
7. При ошибке логировать exception и пробрасывать ошибку worker'у, чтобы job мог перейти в `error`.

## 8. Artifact worker

Файл:

- новый `apps/bot/app/workers/artifact_worker.py`

Цикл:

1. Инициализировать logging.
2. Бесконечный async loop.
3. Claim oldest pending job.
4. Process job.
5. Sleep `settings.artifact_worker_poll_interval_sec`.

Claim:

```python
select(ArtifactJob)
    .where(ArtifactJob.status == "pending")
    .order_by(ArtifactJob.created_at.asc())
    .limit(1)
    .with_for_update(skip_locked=True)
```

В той же transaction:

- `status="running"`
- `started_at=func.now()` или `datetime.now(timezone.utc)`
- `attempts=ArtifactJob.attempts + 1`

Processing:

1. Загрузить историю через `load_user_thread_history(job.user_tg_id, job.thread_id)`.
2. Отформатировать историю в Markdown. Можно вынести общий formatter из `send_to_admin.py`, чтобы worker не дублировал форматирование. Для MVP допустим локальный formatter в worker/service, но лучше переиспользовать.
3. Вызвать `generate_artifacts_from_dialogue(...)`.
4. Сохранить:
   - `input_dialogue_md`
   - `output_markdown`
   - `artifact_prompt_version`
   - `artifact_model_provider`
   - `artifact_model`
   - `status="success"`
   - `finished_at`
5. Отправить Markdown файл админу.

Failure:

1. `status="error"`
2. `error=str(exc)[:reasonable_limit]`
3. `finished_at`
4. `logger.exception(...)`
5. Попытаться отправить короткое уведомление в admin chat. Ошибка уведомления не должна падать поверх исходной ошибки.

Retry policy для MVP:

- Требование говорит `ARTIFACT_GENERATOR_MAX_RETRIES=3`, но базовый status set содержит только `pending/running/success/error`.
- Простая реализация: при ошибке, если `attempts < max_retries`, вернуть job в `pending` с записанным `error`; иначе поставить `error`.
- Если нужен строгий MVP без retry-loop, параметр добавить в config, но worker может сразу ставить `error`. Лучше реализовать retry, так как настройка явно указана.

## 9. Config и `.env.example`

Файлы:

- `apps/bot/app/config.py`
- `.env.example`
- возможно `.env` только если локально нужно запускать worker

Добавить в `BotSettings`:

```python
artifact_worker_poll_interval_sec: int = 5
artifact_generator_temperature: float = 0.3
artifact_generator_max_retries: int = 3
```

Добавить в `.env.example`:

```env
# Artifact Generator
ARTIFACT_WORKER_POLL_INTERVAL_SEC=5
ARTIFACT_GENERATOR_TEMPERATURE=0.3
ARTIFACT_GENERATOR_MAX_RETRIES=3
```

Provider/model для MVP не добавлять: использовать текущий `TEXT_LLM_PROVIDER` и соответствующий text model.

## 10. Docker Compose

Файл:

- `infra/docker-compose.yml`

Добавить service:

```yaml
artifact-worker:
  build:
    context: ..
    dockerfile: apps/bot/Dockerfile
  env_file: ../.env
  command: python -m apps.bot.app.workers.artifact_worker
  depends_on:
    postgres:
      condition: service_healthy
  restart: unless-stopped
```

Публичный порт не нужен.

## 11. Минимальные тесты

Приоритетные тесты:

1. Prompt kind:
   - `artifact_generator_prompt` проходит constraint/model expectations.
   - `create_prompt_version(kind="artifact_generator_prompt", ...)` создает active version.
   - `restore_prompt_version(...)` создает новую active version.
2. Seed:
   - при отсутствии prompt seed создает version 1.
   - повторный seed не создает version 2.
3. `send_to_admin`:
   - создает `AdminNotification`.
   - создает `ArtifactJob`.
   - job получает `trace_id`, `user_tg_id`, `thread_id`, `input_comment`.
   - при ошибке создания job tool не меняет пользовательский success response.
4. Worker/service:
   - claim берет oldest pending job и ставит `running`.
   - mock LLM возвращает Markdown, job становится `success`.
   - при LLM exception job становится `pending` для retry или `error` после max retries.
   - delivery mock вызывается с `.md` content.

Telegram и LLM в тестах только mock/stub.

## 12. Manual QA

1. Запустить миграции:

```bash
docker compose -f infra/docker-compose.yml run --rm bot alembic -c migrations/alembic.ini upgrade head
```

2. Запустить stack:

```bash
cd infra
docker compose up -d --build
```

3. Проверить admin:
   - страница `/admin/prompts/artifact-generator` открывается.
   - active prompt виден.
   - save создает новую version.
   - restore создает новую version, а не перезаписывает старую.

4. Проверить Telegram flow:
   - пройти диалог до вызова `send_to_admin`.
   - admin chat получает старое notification-сообщение.
   - admin chat получает старый history `.md`.
   - позже admin chat получает новый artifacts `.md`.

5. Проверить БД:

```sql
select status, attempts, artifact_prompt_version, artifact_model_provider, artifact_model
from artifact_jobs
order by created_at desc
limit 5;
```

6. Проверить pending scenario:
   - остановить `artifact-worker`.
   - вызвать `send_to_admin`.
   - убедиться, что job остается `pending`.
   - запустить worker.
   - убедиться, что job становится `success`.

## 13. Порядок реализации

Рекомендуемый порядок, чтобы изменения проверялись инкрементально:

1. DB model + migration для prompt kind и `artifact_jobs`.
2. Seed default artifact prompt.
3. Admin prompt page и меню.
4. Config и `.env.example`.
5. `send_to_admin` создает `ArtifactJob`.
6. `artifact_generation.py`.
7. `artifact_delivery.py`.
8. `artifact_worker.py`.
9. Docker Compose service.
10. Unit tests для prompt/job/send_to_admin/worker.
11. Manual QA через Docker Compose.

## 14. Acceptance checklist

- [ ] `artifact_generator_prompt` разрешен constraint'ом `PromptVersion.kind`.
- [ ] Default Artifact Generator prompt seed'ится как version 1.
- [ ] Prompt редактируется на отдельной admin page.
- [ ] Prompt versioning append-only, restore создает новую версию.
- [ ] `send_to_admin` сохраняет прежнее поведение.
- [ ] Каждый успешный DB-save `send_to_admin` создает `ArtifactJob(status="pending")`.
- [ ] Worker запускается отдельным процессом.
- [ ] Worker atomically claims jobs через `FOR UPDATE SKIP LOCKED`.
- [ ] Worker загружает историю по `user_tg_id + thread_id`.
- [ ] Worker вызывает LLM с active `artifact_generator_prompt`.
- [ ] Markdown result сохраняется в `artifact_jobs.output_markdown`.
- [ ] Markdown result отправляется админу `.md` файлом.
- [ ] Ошибки сохраняются в DB и логируются.
- [ ] Не добавлены Redis, Celery, RabbitMQ или внешняя очередь.

