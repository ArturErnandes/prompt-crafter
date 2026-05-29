# BUGS.md — Code & Security Review Findings

**Обновлён:** 2026-05-29 (все исправлены)
**Источник:** Code review + Security review (2026-05-29)
**Статусы:** ⬜ не исправлен · 🔄 в работе · ✅ исправлен

---

## Доска задач

| # | Баг | Severity | Файл | Статус |
|---|-----|----------|------|--------|
| B-1 | Ollama client: unhandled exceptions + timeout | High | `services/ollama.py` | ✅ |
| B-2 | WebSocket: error handling, info leakage, partial save | High | `api/ws/session.py` | ✅ |
| B-3 | `update_title` молча успешен при отсутствующей сессии | Medium | `repositories/sessions.py` | ✅ |
| B-4 | Сообщение сохраняется для несуществующей сессии | Medium | `repositories/messages.py` | ✅ |
| B-5 | `NullPool` в production API | Medium | `db/session.py` | ✅ |
| B-6 | Отсутствие `prompting.md` не прерывает старт | Medium | `app.py` | ✅ |
| B-7 | `setup_logging()` вызывается при каждом `get_logger()` | Low | `logger.py` | ✅ |
| B-8 | `APP_HOST`/`APP_PORT` читаются в обход pydantic | Low | `main.py` | ✅ |
| B-9 | CORS: `allow_origins=["*"]` + `allow_credentials=True` | Low | `app.py` | ✅ |
| B-10 | Мёртвый обработчик `NotFoundError` в messages router | Low | `api/routers/messages.py` | ✅ |
| B-11 | Лишний `get_by_id` round-trip в `create_session` | Low | `api/routers/sessions.py` | ✅ |

---

## B-1 ✅ — Ollama client: unhandled exceptions + timeout

**Severity:** High
**Источник:** Code review C-4, C-15

**Проблема:**
1. Если Ollama возвращает строку с валидным JSON без ключа `"done"` (например `{"error":"model not found"}`) — `data["done"]` поднимает `KeyError`. Это **не** `httpx.HTTPError`, поэтому хендлер его не поймает, и необработанное исключение всплывает наверх.
2. Если Ollama обрывает соединение посреди потока и присылает неполную строку — `json.loads(line)` поднимает `json.JSONDecodeError`, которое также не поймается.
3. `timeout=None` означает, что зависший Ollama-процесс удерживает WebSocket открытым бесконечно.

**Критерий готовности:**
- Запрос с недоступной/неизвестной моделью Ollama не приводит к необработанному исключению — клиент получает `OllamaError`.
- Невалидная строка в ndjson-потоке не роняет весь стрим.
- Задан явный `read`-таймаут (не `None`).

**Затрагиваемые файлы:**
- Изменить: `api/app/services/ollama.py`

**Исправление:**

```python
# 1. Проверять ключ "done" через .get(), ловить ошибку ответа Ollama
data = json.loads(line)
if data.get("error"):
    raise OllamaError(f"ollama error: {data['error']}")
if data.get("done"):
    break

# 2. Расширить except в генераторе
except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
    raise OllamaError(f"chat: {e}") from e

# 3. Заменить timeout=None на явный таймаут
httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=5.0))
```

---

## B-2 ✅ — WebSocket: error handling, info leakage, partial save

**Severity:** High
**Источник:** Code review C-2, C-3, C-10; Security review S-1

**Проблема:**
1. **KeyError на `data["content"]`** (строка 27): если клиент присылает JSON без ключа `"content"`, исключение происходит до блока `try/except`, и клиент получает сырую строку `KeyError: 'content'`.
2. **Утечка внутренних деталей** (строки 53–55): `str(e)` от asyncpg/SQLAlchemy может содержать имена таблиц, колонок, SQL-запросы и строку подключения к БД — всё это отправляется клиенту.
3. **Потеря ответа ассистента** (строка 46): при `OllamaError` в середине стрима `full_response` выбрасывается; сообщение пользователя уже сохранено в БД, а ответа ассистента нет — история становится несогласованной.
4. **WebSocket закрывается до гарантированной доставки JSON-фрейма** (строки 48–55): `send_json` + немедленный `close()` не гарантирует доставку на всех клиентах.

**Критерий готовности:**
- Отсутствие `"content"` в payload возвращает `{"type": "error", "content": "bad_request"}`, без стека.
- Внутренние исключения (DB, KeyError) возвращают `{"type": "error", "content": "internal_error"}` — детали остаются в логах.
- При сбое Ollama в середине стрима: если накоплена частичная строка, она сохраняется в БД; если нет — сообщение пользователя откатывается или факт обрыва логируется явно.
- `websocket.close(code=1011)` вызывается после `send_json`.

**Затрагиваемые файлы:**
- Изменить: `api/app/api/ws/session.py`

**Исправление:**

```python
await websocket.accept()
try:
    data = await websocket.receive_json()
    user_message = data.get("content")
    if not user_message:
        await websocket.send_json({"type": "error", "content": "bad_request"})
        await websocket.close(code=1003)
        return
    # ... остальная логика ...
except OllamaError as e:
    logger.error("ws_session ollama_error | session_id=%s | error=%s", session_id, str(e))
    if full_response:
        await message_repo.create(session_id, "assistant", full_response)
    await websocket.send_json({"type": "error", "content": str(e)})
    await websocket.close(code=1011)
except Exception as e:
    logger.error("ws_session error | session_id=%s | error=%s", session_id, str(e))
    await websocket.send_json({"type": "error", "content": "internal_error"})
    await websocket.close(code=1011)
```

---

## B-3 ✅ — `update_title` молча успешен при отсутствующей сессии

**Severity:** Medium
**Источник:** Code review C-5

**Проблема:**
`UPDATE sessions SET title = :title WHERE id = :session_id` затрагивает 0 строк при несуществующем `session_id` и коммитит без ошибки. Вызывающий код не может отличить успех от no-op.

**Критерий готовности:**
`session_repo.update_title("несуществующий-uuid", "title")` поднимает `NotFoundError`.

**Затрагиваемые файлы:**
- Изменить: `api/app/repositories/sessions.py`

**Исправление:**

```python
# Добавить RETURNING id к UPDATE, проверить результат
result = await self._session.execute(
    text("UPDATE sessions SET title = :title WHERE id = :session_id RETURNING id"),
    {"session_id": session_id, "title": title},
)
row = result.mappings().one_or_none()
await self._session.commit()
# Проверка after commit — same pattern as get_by_id
if row is None:
    logger.warning("Сессия не найдена | session_id=%s", session_id)
    raise NotFoundError(f"session_not_found session_id={session_id}")
```

---

## B-4 ✅ — Сообщение сохраняется для несуществующей сессии

**Severity:** Medium
**Источник:** Code review C-9

**Проблема:**
В `MessageRepository.create()` выполняется `INSERT INTO messages` и затем `UPDATE sessions SET updated_at`. Если `session_id` не существует, `INSERT` проходит (FK `session_id REFERENCES sessions(id) ON DELETE CASCADE` должен бы это блокировать, но если FK не объявлен как `NOT NULL` или сессия была удалена между запросами — зависит от точной DDL), а `UPDATE` молча даёт 0 строк. Фактически: DDL уже защищает через FK — но `UPDATE` не сигнализирует об ошибке при 0 затронутых строках.

**Критерий готовности:**
`message_repo.create("несуществующий-uuid", "user", "text")` либо поднимает `RepositoryError` (FK violation от БД), либо явно проверяет `rowcount` UPDATE и поднимает `NotFoundError`.

**Затрагиваемые файлы:**
- Изменить: `api/app/repositories/messages.py`

**Исправление:**

```python
# Добавить проверку UPDATE rowcount
result_upd = await self._session.execute(
    text("UPDATE sessions SET updated_at = NOW() WHERE id = :session_id"),
    {"session_id": session_id},
)
if result_upd.rowcount == 0:
    logger.warning("Сессия не найдена при создании сообщения | session_id=%s", session_id)
    raise NotFoundError(f"session_not_found session_id={session_id}")
```

---

## B-5 ✅ — `NullPool` в production API

**Severity:** Medium
**Источник:** Code review C-6

**Проблема:**
`create_async_engine(url, poolclass=NullPool)` открывает и закрывает TCP-соединение к PostgreSQL на каждый запрос. `NullPool` подходит для Alembic-миграций (короткоживущий процесс), но не для долгоживущего FastAPI-сервиса — при любой нагрузке это становится bottleneck'ом.

**Критерий готовности:**
`db/session.py` использует `AsyncAdaptedQueuePool` (дефолт для asyncpg) с явными `pool_size` / `max_overflow`.

**Затрагиваемые файлы:**
- Изменить: `api/app/db/session.py`

**Исправление:**

```python
# Убрать poolclass=NullPool, добавить параметры пула
engine = create_async_engine(url, pool_size=5, max_overflow=10)
```

---

## B-6 ✅ — Отсутствие `prompting.md` не прерывает старт

**Severity:** Medium
**Источник:** Code review C-8

**Проблема:**
Когда `templates/prompting.md` не найден, `app.state.system_prompt` устанавливается в `""` и сервис продолжает работу. Для prompt-crafter это функционально сломанное состояние: Ollama получает пустой system prompt и не выполняет трансформацию промтов.

**Критерий готовности:**
Если `prompting.md` отсутствует при старте — приложение завершается с ненулевым кодом выхода и явным сообщением об ошибке в логах. Допустимо сделать поведение конфигурируемым через переменную `REQUIRE_SYSTEM_PROMPT` (default: `true`).

**Затрагиваемые файлы:**
- Изменить: `api/app/app.py`

**Исправление:**

```python
# Заменить silent fallback на явный raise
try:
    _app.state.system_prompt = (Path(settings.TEMPLATES_DIR) / "prompting.md").read_text(encoding="utf-8")
except FileNotFoundError:
    logger.error("prompting.md не найден: %s — завершение", Path(settings.TEMPLATES_DIR) / "prompting.md")
    raise RuntimeError("prompting.md not found")
```

---

## B-7 ✅ — `setup_logging()` вызывается при каждом `get_logger()`

**Severity:** Low
**Источник:** Code review C-11

**Проблема:**
`get_logger(name)` вызывает `setup_logging()` при каждом импорте модуля. Идемпотентность защищена проверками `_has_stream_stdout_handler`/`_has_file_handler`, но `LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)` всё равно вызывается при каждом импорте. Правильный паттерн — вызов `setup_logging()` один раз в точке входа.

**Критерий готовности:**
`setup_logging()` вызывается явно ровно один раз — в `lifespan` приложения или в `main()`.

**Затрагиваемые файлы:**
- Изменить: `api/app/logger.py` (убрать `setup_logging()` из `get_logger()`)
- Изменить: `api/app/app.py` (добавить `setup_logging()` в `lifespan`)
- Изменить: `api/app/main.py` (добавить `setup_logging()` в `main()`)

**Исправление:**

```python
# logger.py
def get_logger(name: str):
    return logging.getLogger(name)

# app.py — в lifespan, первой строкой
async def lifespan(_app: FastAPI):
    setup_logging()
    init_session_factory()
    ...

# main.py — в main(), первой строкой
def main() -> None:
    setup_logging()
    host = os.environ["APP_HOST"]
    ...
```

---

## B-8 ✅ — `APP_HOST`/`APP_PORT` читаются в обход pydantic

**Severity:** Low
**Источник:** Code review C-12

**Проблема:**
`main.py` читает `APP_HOST` и `APP_PORT` через `os.environ[...]` напрямую, минуя `settings` из `config.py`. Это обходит валидацию типов pydantic (например, `APP_PORT` не проверяется как `int`), дефолтные значения из `Settings` не применяются.

**Критерий готовности:**
`main.py` использует `settings.APP_HOST` и `settings.APP_PORT` вместо `os.environ`.

**Затрагиваемые файлы:**
- Изменить: `api/app/main.py`

**Исправление:**

```python
from api.app.config import settings

def main() -> None:
    host = settings.APP_HOST
    port = settings.APP_PORT
    ...
    uvicorn.run("api.app.app:app", host=host, port=port)
```

---

## B-9 ✅ — CORS: `allow_origins=["*"]` + `allow_credentials=True`

**Severity:** Low
**Источник:** Code review C-13

**Проблема:**
Комбинация `allow_origins=["*"]` и `allow_credentials=True` нарушает CORS-спецификацию: браузеры блокируют credentialed-ответы с wildcard-origin. Starlette отправляет оба заголовка одновременно — это работает для non-browser клиентов, но браузерный фронтенд фазы 2 будет получать CORS-ошибки при любом credentialed-запросе.

**Критерий готовности:**
Либо `allow_credentials=False` (при wildcard), либо явный список `allow_origins` (при `allow_credentials=True`).

**Затрагиваемые файлы:**
- Изменить: `api/app/app.py`

**Исправление:**

```python
# Вариант A — без credentials (для локального инструмента достаточно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Вариант B — явный origin (для Phase 2 web-фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## B-10 ✅ — Мёртвый обработчик `NotFoundError` в messages router

**Severity:** Low
**Источник:** Code review C-14

**Проблема:**
`MessageRepository.list_by_session()` при отсутствующем `session_id` возвращает пустой список, но никогда не поднимает `NotFoundError`. Блок `except NotFoundError` в `list_messages` — мёртвый код, создающий ложное ощущение защищённости.

**Критерий готовности:**
Либо `list_by_session` проверяет существование сессии и поднимает `NotFoundError` → обработчик остаётся. Либо обработчик удаляется как мёртвый код.

**Затрагиваемые файлы:**
- Изменить: `api/app/api/routers/messages.py` (удалить мёртвый `except`)
- (Опционально) Изменить: `api/app/repositories/messages.py` (добавить проверку сессии)

**Рекомендация:**
Для MVP удалить мёртвый except. Если позже понадобится 404 при обращении к несуществующей сессии — добавить проверку в репозиторий и вернуть обработчик.

---

## B-11 ✅ — Лишний `get_by_id` round-trip в `create_session`

**Severity:** Low
**Источник:** Code review C-16

**Проблема:**
`create_session` в `routers/sessions.py` вызывает `repo.create()` → получает `session_id` → затем вызывает `repo.get_by_id(session_id)` чтобы построить ответ. Второй запрос к БД лишний: `create()` возвращает только `id`, тогда как `SessionCreateResponse` требует `{id, template_name, created_at}` — всё это можно получить через `RETURNING id, template_name, created_at` в самом INSERT.

**Критерий готовности:**
`POST /api/v1/sessions` выполняет ровно один запрос к БД (INSERT RETURNING). `get_by_id` не вызывается из `create_session`.

**Затрагиваемые файлы:**
- Изменить: `api/app/repositories/sessions.py` — расширить `RETURNING id` до `RETURNING id, template_name, created_at`
- Изменить: `api/app/api/routers/sessions.py` — возвращать `SessionCreateResponse(**row)` напрямую из `create()`

**Исправление:**

```python
# repositories/sessions.py — изменить RETURNING
text("INSERT INTO sessions (user_id, template_name) VALUES (:user_id, :template_name)"
     " RETURNING id, template_name, created_at")

# Изменить сигнатуру create() → возвращать RowMapping вместо str
async def create(self, user_id: int, template_name: str) -> RowMapping: ...

# routers/sessions.py — убрать вызов get_by_id
row = await repo.create(user_id=1, template_name="default")
return SessionCreateResponse(**row)
```

---

## Приоритет исправлений

| Группа | Баги | Когда |
|--------|------|-------|
| Блокируют smoke test | B-1, B-2 | До первого запуска |
| Целостность данных | B-3, B-4 | В рамках MVP |
| Надёжность | B-5, B-6 | В рамках MVP |
| Технический долг | B-7, B-8, B-9, B-10, B-11 | После MVP |
