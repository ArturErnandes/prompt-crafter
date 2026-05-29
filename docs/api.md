# API Reference

The prompt-crafter API transforms draft prompt text into structured prompts using a local Ollama LLM. Session management — creating sessions and reading history — uses HTTP/JSON. Prompt crafting uses WebSocket: the server streams tokens from the model as they arrive. All REST responses use `Content-Type: application/json`.

**Base URL:** `http://localhost:8000`

---

## 1. REST Endpoints

### POST /api/v1/sessions

Creates a new session. Call this before opening a WebSocket connection — the returned `id` is required as the WebSocket path parameter.

No request body.

**Response**

| Field | Type | Description |
|---|---|---|
| `id` | `uuid` | Session ID. Pass this to `/ws/sessions/{id}`. |
| `template_name` | `string` | Prompt template applied to the session. Always `"default"`. |
| `created_at` | `string (ISO 8601)` | Timestamp when the session was created. |

**Errors**

| Status | Detail | Condition |
|---|---|---|
| `500` | `db_error` | A database operation failed. |
| `500` | `internal_error` | An unhandled server exception occurred. |

---

### GET /api/v1/sessions

Returns all sessions ordered by `updated_at` descending. No pagination.

No request body.

**Response:** array of session objects.

| Field | Type | Description |
|---|---|---|
| `id` | `uuid` | Session ID. |
| `template_name` | `string` | Prompt template for this session. |
| `title` | `string \| null` | Session title. `null` if not yet set. |
| `created_at` | `string (ISO 8601)` | Timestamp when the session was created. |
| `updated_at` | `string (ISO 8601)` | Timestamp of the last message in the session. |

**Errors**

| Status | Detail | Condition |
|---|---|---|
| `500` | `db_error` | A database operation failed. |
| `500` | `internal_error` | An unhandled server exception occurred. |

---

### GET /api/v1/sessions/{session_id}/messages

Returns all messages in a session ordered by `created_at` ascending. Returns an empty array if `session_id` does not exist or the session has no messages.

**Path parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | `uuid` | yes | The session to query. |

**Response:** array of message objects.

| Field | Type | Description |
|---|---|---|
| `id` | `uuid` | Message ID. |
| `session_id` | `uuid` | The session this message belongs to. |
| `role` | `string` | `"user"` or `"assistant"`. |
| `content` | `string` | The full message text. |
| `created_at` | `string (ISO 8601)` | Timestamp when the message was created. |

**Errors**

| Status | Detail | Condition |
|---|---|---|
| `500` | `db_error` | A database operation failed. |
| `500` | `internal_error` | An unhandled server exception occurred. |

---

### GET /healthz

Returns the server status. No request body.

**Response**

| Field | Type | Description |
|---|---|---|
| `status` | `string` | Always `"ok"` when the server is running. |

No error responses.

---

## 2. WebSocket

### /ws/sessions/{session_id}

Streams a crafted prompt response token by token. The server loads the full conversation history for the session, prepends the system prompt from `templates/prompting.md`, sends the request to Ollama, and forwards each token as it arrives. Both the user message and the completed assistant response are saved to the database.

**Path parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `session_id` | `uuid` | yes | A session ID returned by `POST /api/v1/sessions`. |

#### Connecting

Open a standard WebSocket connection to `ws://localhost:8000/ws/sessions/{session_id}`. The server accepts immediately and does not validate `session_id` at connection time. Connecting with a non-existent `session_id` succeeds, but the first message triggers an `"internal_error"` response and closes the connection with code `1011`.

#### Client → Server

Send exactly one JSON message after connecting. Do not send further messages on the same connection.

| Field | Type | Required | Description |
|---|---|---|---|
| `content` | `string` | yes | The draft prompt text to transform. |

If `content` is absent or empty, the server sends `{"type": "error", "content": "bad_request"}` and closes with code `1003`.

#### Server → Client

The server sends JSON objects in the following sequence:

**`token`** — sent once per token as the model generates the response. Concatenate these in order to build the full response text.

```json
{"type": "token", "content": "<token text>"}
```

**`done`** — sent once, after all tokens have been streamed and the assistant message has been saved to the database. No further messages follow.

```json
{"type": "done"}
```

**`error`** — sent instead of `done` when streaming fails. The server closes the connection immediately after sending this message.

```json
{"type": "error", "content": "<error detail>"}
```

`content` values:

| Value | Condition |
|---|---|
| `"bad_request"` | `content` field was absent or empty in the client message. |
| `"internal_error"` | An unhandled server exception occurred. |
| Ollama error string | Ollama returned an error response, or the connection to Ollama failed. The exact string comes from the Ollama service. |

If an Ollama error occurs after the model has already emitted tokens, the server saves the partial response before sending the error message.

#### Close codes

| Code | Meaning |
|---|---|
| `1003` | Client sent a message without a `content` field or with an empty value. |
| `1011` | Server-side failure — Ollama error or unhandled exception. |

---

## 3. Error Reference

| Detail | HTTP status / WS close | Condition |
|---|---|---|
| `db_error` | HTTP `500` | A database operation raised an exception. Check DB connectivity. |
| `internal_error` | HTTP `500` or WS close `1011` | An unhandled exception occurred on the server. |
| `bad_request` | WS close `1003` | The WebSocket message was missing the `content` field or it was empty. |
| Ollama error string | WS close `1011` | Ollama returned an error in the stream, or the HTTP connection to Ollama failed. The `content` field of the error message contains the raw error text from the service. |
