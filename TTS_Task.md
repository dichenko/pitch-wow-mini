# Задача: интегрировать мультиязычный TTS по принципам проекта `uz-stomatolog`

## Цель

Нужно перенести в новый проект архитектурные принципы мультиязычной озвучки из текущего проекта. TTS не должен быть одним большим `if` внутри Telegram-хендлера или бизнес-логики. Он должен быть отдельным speech-слоем с единым интерфейсом, маршрутизацией по языку, провайдерскими адаптерами, безопасной обработкой ошибок, временными файлами и fallback на текстовый ответ.

В текущем проекте TTS используется в Telegram voice pipeline:

1. Пользователь выбирает язык: `ru`, `uz`, `en`.
2. Пользователь отправляет voice-сообщение.
3. Бот скачивает входное аудио во временный файл.
4. STT распознает речь через провайдера, выбранного по языку.
5. LLM/agent формирует текстовый ответ на выбранном языке.
6. Бот сначала отправляет текстовый ответ.
7. Затем TTS синтезирует этот же ответ в аудио.
8. Аудио приводится к формату, пригодному для Telegram `sendVoice`.
9. Бот отправляет voice-сообщение.
10. Все временные файлы удаляются.

Главный принцип: текстовый ответ является основным результатом, голосовой ответ является дополнительным. Если TTS упал, бот не должен падать и не должен терять ответ пользователю.

## Исходные файлы-ориентиры в текущем проекте

- `apps/bot/app/speech/base.py` - единые типы, протоколы и ошибка `SpeechProviderError`.
- `apps/bot/app/speech/factory.py` - маршрутизация STT/TTS-провайдеров по языку.
- `apps/bot/app/speech/openai_provider.py` - OpenAI STT/TTS.
- `apps/bot/app/speech/aisha_provider.py` - Aisha STT/TTS для узбекского.
- `apps/bot/app/speech/yandex_provider.py` - Yandex SpeechKit TTS для русского.
- `apps/bot/app/speech/azure_provider.py` - Azure TTS как альтернативный адаптер.
- `apps/bot/app/speech/temp_files.py` - временные аудиофайлы, лимиты размера, cleanup, ffmpeg-конвертация.
- `apps/bot/app/telegram/handlers_messages.py` - полный voice pipeline: STT -> agent -> text reply -> TTS -> Telegram voice.
- `apps/bot/app/config.py` и `.env.example` - настройки провайдеров.
- `apps/bot/tests/test_speech.py` - тесты маршрутизации, провайдерских payload, ошибок и cleanup.

## Поддерживаемые языки

В новом проекте нужно явно ввести поддерживаемые языки:

```python
Language = Literal["ru", "uz", "en"]
SUPPORTED_LANGUAGES = ("ru", "uz", "en")
DEFAULT_LANGUAGE = "ru"
```

Нужно сделать функцию нормализации:

```python
def normalize_language(language: str | None) -> Language:
    if language in SUPPORTED_LANGUAGES:
        return language
    return DEFAULT_LANGUAGE
```

Нельзя передавать произвольные значения языка напрямую в провайдеры. Все входные значения должны сначала проходить через `normalize_language`.

## Маршрутизация TTS по языку

В текущем проекте используется такая логика:

```text
uz -> Aisha TTS
ru -> Yandex SpeechKit TTS
en -> OpenAI TTS
```

Для STT логика отличается:

```text
uz -> Aisha STT
ru -> OpenAI STT
en -> OpenAI STT
```

В новом проекте нужно реализовать фабрику speech-провайдеров, чтобы остальной код не знал, какой API используется для конкретного языка.

Пример целевого контракта:

```python
@dataclass(frozen=True)
class SpeechProviders:
    openai: OpenAISpeechProvider
    aisha: AishaSpeechProvider
    yandex: YandexSpeechKitProvider
    azure: AzureSpeechProvider

    def stt_for_language(self, language: str) -> SpeechToTextProvider:
        language = normalize_language(language)
        if language == "uz":
            return self.aisha
        return self.openai

    def tts_for_language(self, language: str) -> TextToSpeechProvider:
        language = normalize_language(language)
        if language == "uz":
            return self.aisha
        if language == "ru":
            return self.yandex
        return self.openai
```

Важно: Azure в текущем проекте есть как готовый альтернативный TTS-адаптер, но фабрика по умолчанию его не выбирает. В новом проекте можно оставить Azure как резервный или конфигурируемый вариант для русского языка.

## Единый интерфейс TTS

Все TTS-провайдеры должны реализовывать один интерфейс:

```python
class TextToSpeechProvider(Protocol):
    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        ...
```

Результат TTS должен быть структурированным:

```python
@dataclass(frozen=True)
class TextToSpeechResult:
    file_path: str
    mime_type: str
    format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]
    provider: Literal["openai", "aisha", "yandex", "azure", "mock"]
    model: str
    voice: str | None = None
```

Провайдер возвращает путь к локальному временному файлу, а не bytes наружу. Это упрощает дальнейшую отправку в Telegram, конвертацию через ffmpeg и cleanup.

## Единая ошибка speech-слоя

Нужно завести общую ошибку:

```python
class SpeechProviderError(RuntimeError):
    pass
```

Все провайдерские ошибки, ошибки ключей, таймауты, пустой результат, невалидный payload и превышение лимитов должны приводиться к `SpeechProviderError` или к подклассу, который затем превращается в `SpeechProviderError` на верхнем уровне.

В Telegram/business pipeline нельзя отдавать пользователю техническую ошибку провайдера. Пользователь получает локализованную фразу вроде:

```text
Я подготовил ответ текстом, но сейчас не смог озвучить его голосом.
```

## Провайдер Aisha TTS для узбекского языка

Используется для `language = "uz"`.

### Настройки

```env
AISHA_API_KEY=
AISHA_BASE_URL=https://back.aisha.group
AISHA_TTS_TIMEOUT_MS=60000
AISHA_TTS_MAX_CHARS=1000
AISHA_TTS_LANGUAGE=uz
AISHA_TTS_MODEL=Gulnoza
AISHA_TTS_MOOD=Neutral
AISHA_TTS_SPEED=1.0
```

### Payload

Aisha TTS вызывается через multipart form:

```text
POST {AISHA_BASE_URL}/api/v1/tts/post/
Headers:
  X-Api-Key: <AISHA_API_KEY>
  Accept-Language: uz

Form fields:
  transcript=<prepared_text>
  language=uz
  model=Gulnoza
  mood=Neutral
  speed=1.0
```

Ответ содержит `audio_path`. После POST нужно скачать готовое аудио:

```text
GET {AISHA_BASE_URL}/{audio_path}
```

Результат сохраняется во временный `.wav` файл:

```python
TextToSpeechResult(
    file_path=str(output_path),
    mime_type="audio/wav",
    format="wav",
    provider="aisha",
    model="aisha-tts",
    voice=settings.aisha_tts_model,
)
```

### Особенности

- Перед отправкой текст очищается от Markdown, ссылок, emoji, лишних пробелов.
- Если текст длиннее `AISHA_TTS_MAX_CHARS`, он обрезается до лимита, желательно по последнему пробелу.
- `mood` используется для built-in голоса `Gulnoza`.
- В логах можно писать `language`, `model`, `mood`, `speed`, но нельзя логировать API key.
- Aisha возвращает WAV, поэтому перед отправкой в Telegram voice нужно конвертировать в OGG/Opus.

## Провайдер Yandex SpeechKit TTS для русского языка

Используется для `language = "ru"` в текущей фабрике.

### Настройки

```env
YANDEX_SPEECHKIT_API_KEY=
YANDEX_TTS_BASE_URL=https://tts.api.cloud.yandex.net
YANDEX_TTS_MODEL=yandex-speechkit-tts-v1
YANDEX_TTS_LANGUAGE=ru-RU
YANDEX_TTS_VOICE=alena
YANDEX_TTS_EMOTION=good
YANDEX_TTS_SPEED=1.15
YANDEX_TTS_FORMAT=oggopus
YANDEX_TTS_TIMEOUT_MS=60000
YANDEX_TTS_MAX_CHARS=5000
```

### Payload

Yandex вызывается form-url-encoded запросом:

```text
POST {YANDEX_TTS_BASE_URL}/speech/v1/tts:synthesize
Headers:
  Authorization: Api-Key <YANDEX_SPEECHKIT_API_KEY>

Data:
  text=<prepared_text>
  lang=ru-RU
  voice=alena
  emotion=good
  speed=1.15
  format=oggopus
```

Результат приходит сразу bytes аудио. Его нужно сохранить во временный `.ogg` файл:

```python
TextToSpeechResult(
    file_path=str(output_path),
    mime_type="audio/ogg",
    format="opus",
    provider="yandex",
    model=settings.yandex_tts_model,
    voice=settings.yandex_tts_voice,
)
```

### Особенности

- `format=oggopus` выбран специально, чтобы Telegram мог отправлять результат как voice-сообщение.
- Перед отправкой текст чистится от Markdown, ссылок, emoji.
- Символы валют и процентов лучше заменять словами, например `₽ -> рублей`, `$ -> долларов`, `% -> процентов`.
- Если текст длиннее `YANDEX_TTS_MAX_CHARS`, его нужно обрезать по лимиту.
- В логах должны быть `voice`, `emotion`, `speed`, `format`, `duration_ms`, `file_size_bytes`, но не API key.

## Провайдер OpenAI TTS для английского языка

Используется для `language = "en"` в текущей фабрике. Также OpenAI используется для STT русского и английского.

### Настройки

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=marin
OPENAI_TTS_FALLBACK_VOICE=cedar
OPENAI_TTS_RESPONSE_FORMAT=opus
OPENAI_TTS_TIMEOUT_MS=60000
OPENAI_TTS_MAX_CHARS=4096
OPENAI_TTS_SPEED=1.1
OPENAI_TTS_INSTRUCTIONS=
```

### API-вызов

```python
response = await client.audio.speech.create(
    model=settings.openai_tts_model,
    voice=settings.openai_tts_voice,
    input=text,
    instructions=resolved_instructions or "",
    response_format=settings.openai_tts_response_format,
    speed=settings.openai_tts_speed,
)
```

Результат нужно сохранить во временный файл с suffix по `response_format`, например `.opus`.

### Особенности

- Перед API-вызовом проверять `OPENAI_TTS_MAX_CHARS`. В текущем проекте OpenAI не обрезается автоматически, а кидает ошибку, если текст длиннее лимита.
- `instructions` могут приходить из админки по языку или из env `OPENAI_TTS_INSTRUCTIONS`.
- OpenAI TTS поддерживает voice style instructions, поэтому для него параметр `instructions` реально передается.
- OpenAI клиент создается лениво и переиспользуется.
- Используется retry на сетевые ошибки, таймауты и статусы `429`, `500`, `502`, `503`, `504`.

## Azure TTS как альтернативный адаптер

В текущем проекте Azure реализован, но не выбран фабрикой по умолчанию.

### Настройки

```env
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope
AZURE_SPEECH_ENDPOINT=https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1
AZURE_TTS_LANGUAGE=ru-RU
AZURE_TTS_VOICE=ru-RU-SvetlanaNeural
AZURE_TTS_OUTPUT_FORMAT=ogg-24khz-16bit-mono-opus
AZURE_TTS_RATE=20%
AZURE_TTS_PITCH=
AZURE_TTS_RANGE=
AZURE_TTS_TIMEOUT_MS=60000
AZURE_TTS_MAX_CHARS=5000
```

### Принцип работы

Azure получает SSML:

```xml
<speak version="1.0" xml:lang="ru-RU">
  <voice name="ru-RU-SvetlanaNeural">
    <prosody rate="20%">Текст ответа</prosody>
  </voice>
</speak>
```

В коде нужно экранировать текст через `html.escape`, чтобы пользовательский текст не ломал SSML.

Azure удобен как fallback, если Yandex недоступен или нужно другое качество русского голоса.

## TTS prompts / instructions по языкам

В текущем проекте есть админская настройка:

```json
{
  "tts.prompts": {
    "ru": "",
    "uz": "",
    "en": ""
  }
}
```

Перед TTS-вызовом pipeline читает prompt по текущему языку:

```python
tts_instructions = await get_tts_prompt(db_session, language)

tts_result = await providers.tts_for_language(language).synthesize(
    response_text,
    language,
    instructions=tts_instructions.strip() or None,
)
```

Правила:

- Если prompt пустой, не передавать пустую инструкцию как смысловую настройку.
- Если провайдер поддерживает instructions, использовать их. Сейчас это актуально для OpenAI.
- Если провайдер не поддерживает instructions, параметр должен оставаться в интерфейсе, но адаптер может его игнорировать.
- Хранить prompts по языкам, а не один общий prompt на все языки.

## Подготовка текста перед TTS

Перед синтезом текст нужно привести к форме, которую TTS хорошо читает.

Минимальная функция:

```python
def prepare_text_for_tts(text: str) -> str:
    prepared = text.strip()
    prepared = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", prepared)
    prepared = re.sub(r"https?://\S+", "", prepared)
    prepared = re.sub(r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", "", prepared)
    prepared = prepared.replace("**", "")
    prepared = prepared.replace("__", "")
    prepared = prepared.replace("`", "")
    prepared = prepared.replace("\u2022", ". ")
    prepared = prepared.replace("-", " ")
    prepared = re.sub(r"\s+", " ", prepared)
    return prepared.strip()
```

Для русского дополнительно полезно:

```python
prepared = prepared.replace("₽", " рублей")
prepared = prepared.replace("$", " долларов")
prepared = prepared.replace("%", " процентов")
```

Принципы:

- Не отправлять Markdown в TTS.
- Не озвучивать URL.
- Убирать emoji.
- Делать короткие фразы.
- Не отправлять пустую строку.
- Ограничивать длину по лимиту провайдера.
- Желательно просить LLM заранее формировать voice-friendly ответы: 1-3 предложения, без markdown, цифры и цены словами там, где это критично для озвучки.

## Временные аудиофайлы

Нужен отдельный модуль для временных файлов.

### Настройка

```env
SPEECH_TEMP_DIR=/tmp/dental-bot-audio
```

### Создание файла

```python
def create_temp_audio_path(*, suffix: str) -> Path:
    temp_dir = Path(settings.speech_temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="dental-bot-",
        suffix=suffix,
        dir=temp_dir,
        delete=False,
    )
    path = Path(handle.name)
    handle.close()
    return path
```

### Cleanup

Любой входной и выходной аудиофайл должен удаляться в `finally`:

```python
finally:
    await cleanup_temp_file(input_path, reason="telegram_voice_input_cleanup")
    await cleanup_temp_file(output_path, reason="telegram_voice_output_cleanup")
    await cleanup_temp_file(tts_original_path, reason="telegram_tts_original_cleanup")
```

### Лимиты

До STT/TTS нужно проверять размер:

```python
def validate_file_size(file_path: str | Path, *, max_size_mb: int) -> None:
    size_bytes = Path(file_path).stat().st_size
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise AudioValidationError(...)
```

Для входных voice-сообщений также проверять duration. В текущем проекте лимит 60 секунд.

## Формат для Telegram voice

Telegram `sendVoice` ожидает voice-friendly аудио. Практичный стандарт:

```text
OGG / Opus
mono
16000 Hz
bitrate 16k
```

Если провайдер вернул `.ogg` или `.opus`, можно отправлять сразу. Если провайдер вернул `.wav`, `.mp3` или другой формат, нужно конвертировать через ffmpeg:

```bash
ffmpeg -y -i input.wav -c:a libopus -b:a 16k -ar 16000 -ac 1 output.ogg
```

В коде:

```python
async def ensure_ogg(file_path: str) -> Path:
    path = Path(file_path)
    if path.suffix.casefold() in (".ogg", ".opus"):
        return path

    output_path = Path(str(path) + ".ogg")
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-c:a",
        "libopus",
        "-b:a",
        "16k",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(...)
    return output_path
```

После конвертации отправлять именно voice:

```python
audio = FSInputFile(output_path, filename="voice.ogg")
await message.answer_voice(audio)
```

Не отправлять TTS как обычный `audio`, если цель - Telegram voice-сообщение.

## Полный voice pipeline

Целевой алгоритм:

1. Проверить, что у пользователя выбран язык.
2. Нормализовать язык.
3. Скачать Telegram voice во временный `.ogg`.
4. Проверить duration и размер файла.
5. Выбрать STT-провайдера через `providers.stt_for_language(language)`.
6. Распознать текст.
7. Если STT вернул пустой текст, кинуть `SpeechProviderError`.
8. Сохранить входящее сообщение в БД с `message_type="voice"` и `stt_provider/stt_model`.
9. Передать распознанный текст в основной agent/LLM.
10. Получить `response_text`.
11. Сначала отправить пользователю текстовый ответ.
12. Сохранить текстовый исходящий ответ в БД.
13. Получить `tts_prompt` для языка из настроек.
14. Выбрать TTS-провайдера через `providers.tts_for_language(language)`.
15. Вызвать `synthesize(response_text, language, instructions=...)`.
16. Привести результат к OGG/Opus через `ensure_ogg`.
17. Отправить `answer_voice`.
18. Сохранить voice-ответ в БД с `tts_provider`, `tts_model`, `tts_format`, `tts_mime_type`, `voice`.
19. Если TTS упал, залогировать ошибку, уведомить dev-admin при необходимости и отправить локализованную текстовую ошибку про невозможность озвучки.
20. В `finally` удалить входной файл, оригинальный TTS-файл и сконвертированный OGG-файл.

Важно: пункты 11-12 идут до TTS. Пользователь должен получить текст даже при поломке озвучки.

## Логирование и безопасность

Логировать:

- `provider`
- `operation`: `stt` или `tts`
- `model`
- `language`
- `voice`
- `format` / `response_format`
- `duration_ms`
- `file_size_bytes`
- `trace_id`
- retry attempt
- HTTP status провайдера при ошибке
- укороченный body ошибки, например первые 1000 символов

Не логировать:

- API keys
- Telegram token
- полный Authorization header
- слишком длинные пользовательские тексты
- приватные данные без необходимости

Ключи должны жить в `.env` или secrets, не в коде.

## Retry policy

Для провайдеров нужен retry на временные ошибки.

В текущем проекте OpenAI и Aisha используют задержки:

```python
delays = (0, 2, 5)
```

Повторять можно:

```text
429
500
502
503
504
network timeout
transport error
connection error
```

Не повторять:

```text
400 bad request
401/403 auth error
404 wrong endpoint
422 invalid payload
```

После исчерпания retries бросать `SpeechProviderError`.

## Конфигурация нового проекта

Добавить в настройки нового проекта:

```env
SPEECH_TEMP_DIR=/tmp/project-audio

OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=marin
OPENAI_TTS_RESPONSE_FORMAT=opus
OPENAI_TTS_TIMEOUT_MS=60000
OPENAI_TTS_MAX_CHARS=4096
OPENAI_TTS_SPEED=1.0
OPENAI_TTS_INSTRUCTIONS=

AISHA_API_KEY=
AISHA_BASE_URL=https://back.aisha.group
AISHA_TTS_TIMEOUT_MS=60000
AISHA_TTS_MAX_CHARS=1000
AISHA_TTS_LANGUAGE=uz
AISHA_TTS_MODEL=Gulnoza
AISHA_TTS_MOOD=Neutral
AISHA_TTS_SPEED=1.0

YANDEX_SPEECHKIT_API_KEY=
YANDEX_TTS_BASE_URL=https://tts.api.cloud.yandex.net
YANDEX_TTS_MODEL=yandex-speechkit-tts-v1
YANDEX_TTS_LANGUAGE=ru-RU
YANDEX_TTS_VOICE=alena
YANDEX_TTS_EMOTION=good
YANDEX_TTS_SPEED=1.15
YANDEX_TTS_FORMAT=oggopus
YANDEX_TTS_TIMEOUT_MS=60000
YANDEX_TTS_MAX_CHARS=5000

AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope
AZURE_SPEECH_ENDPOINT=
AZURE_TTS_LANGUAGE=ru-RU
AZURE_TTS_VOICE=ru-RU-SvetlanaNeural
AZURE_TTS_OUTPUT_FORMAT=ogg-24khz-16bit-mono-opus
AZURE_TTS_RATE=20%
AZURE_TTS_PITCH=
AZURE_TTS_RANGE=
AZURE_TTS_TIMEOUT_MS=60000
AZURE_TTS_MAX_CHARS=5000
```

Если в новом проекте не нужны все провайдеры, все равно сохранить архитектуру адаптеров. Например, можно оставить только:

```text
uz -> Aisha
ru -> Yandex
en -> OpenAI
```

Но интерфейс должен позволять заменить провайдера без переписывания Telegram-хендлера.

## База данных и история сообщений

Если в новом проекте есть БД, сохранять для voice-ответов минимум:

```json
{
  "message_type": "voice",
  "language": "ru",
  "text": "Текст, который был озвучен",
  "raw_payload": {
    "tts_provider": "yandex",
    "tts_model": "yandex-speechkit-tts-v1",
    "tts_format": "opus",
    "tts_mime_type": "audio/ogg",
    "voice": "alena"
  }
}
```

Для входящего voice после STT:

```json
{
  "message_type": "voice",
  "text": "Распознанный текст",
  "raw_payload": {
    "transcribed": true,
    "stt_provider": "openai",
    "stt_model": "gpt-4o-transcribe"
  }
}
```

## Mock provider для тестов

Добавить `MockSpeechProvider`, который не ходит во внешние API:

```python
class MockSpeechProvider:
    async def transcribe(self, file_path: str, language: str) -> SpeechToTextResult:
        return SpeechToTextResult(...)

    async def synthesize(
        self,
        text: str,
        language: str,
        instructions: str | None = None,
    ) -> TextToSpeechResult:
        output_path = create_temp_audio_path(suffix=".mp3")
        output_path.write_bytes(b"mock-audio")
        return TextToSpeechResult(...)
```

Mock нужен для unit-тестов voice pipeline без API keys.

## Тесты, которые нужно добавить

Минимальный набор:

1. Фабрика маршрутизирует языки правильно:
   - `uz` TTS -> Aisha
   - `ru` TTS -> Yandex
   - `en` TTS -> OpenAI
2. `normalize_language(None)` и неизвестный язык возвращают `ru`.
3. OpenAI TTS отклоняет слишком длинный текст до API-вызова.
4. Aisha TTS отправляет правильный multipart payload и скачивает `audio_path`.
5. Yandex TTS отправляет правильные параметры `voice`, `emotion`, `speed`, `format`.
6. Azure TTS формирует валидный SSML и экранирует текст.
7. Ошибки провайдеров логируются без API keys.
8. Временный файл создается в `SPEECH_TEMP_DIR` и удаляется через `cleanup_temp_file`.
9. Если TTS падает, pipeline все равно отправляет текстовый ответ.
10. Если провайдер вернул WAV, `ensure_ogg` конвертирует его в OGG/Opus.

## Критерии приемки

- В новом проекте есть отдельный speech-слой, а не TTS-логика внутри хендлера.
- Все TTS-провайдеры реализуют единый `synthesize(text, language, instructions=None)`.
- Выбор TTS-провайдера зависит от нормализованного языка.
- `uz`, `ru`, `en` работают через разные провайдеры по заданной маршрутизации.
- TTS prompt/instructions хранится и выбирается по языку.
- Провайдеры не логируют секреты.
- Слишком длинный или пустой текст обрабатывается до отправки или безопасно обрезается.
- Telegram получает voice-сообщение в OGG/Opus.
- Временные аудиофайлы удаляются после отправки или ошибки.
- При падении TTS пользователь получает текстовый ответ и локализованное сообщение о невозможности озвучки.
- Есть unit-тесты маршрутизации, payload провайдеров, cleanup и fallback-поведения.

## Рекомендуемая структура файлов в новом проекте

```text
app/
  speech/
    __init__.py
    base.py
    factory.py
    temp_files.py
    openai_provider.py
    aisha_provider.py
    yandex_provider.py
    azure_provider.py
    mock_provider.py
  telegram/
    handlers_messages.py
    texts.py
  admin/
    settings_reader.py
  config.py
tests/
  test_speech.py
```

## Главное правило интеграции

Хендлер должен работать с абстракцией:

```python
providers = create_speech_providers(settings)
tts_provider = providers.tts_for_language(language)
tts_result = await tts_provider.synthesize(
    response_text,
    language,
    instructions=tts_prompt or None,
)
```

Хендлер не должен знать, какие headers, payload, voice, model, endpoint и response format нужны конкретному TTS API. Это ответственность адаптера провайдера.
