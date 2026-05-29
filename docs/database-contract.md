# Database Contract

## 1. Migration overview

### `001_create_sessions`

Creates table `sessions` with trigger function `set_updated_at()` and trigger `sessions_updated_at`.

### `002_create_messages`

Creates table `messages` with index `ix_messages_session_id`.

---

## 2. Table specifications

### 1. `sessions`

One session groups a multi-turn conversation. `title` is set by the service after the first exchange. `updated_at` is maintained by a DB trigger, not application code.

| Column | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `uuid` | yes | `gen_random_uuid()` | Session ID |
| `template_name` | `text` | yes | `'default'` | Prompt template name |
| `title` | `text` | no | — | Session title |
| `created_at` | `timestamptz` | yes | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | yes | `now()` | Last update timestamp (via trigger) |

Constraints:

| Type | Name | Expression |
|---|---|---|
| `PRIMARY KEY` | `sessions_pkey` | `id` |

Trigger: `sessions_updated_at` — BEFORE UPDATE, calls `set_updated_at()`.

---

### 2. `messages`

Stores the full conversation history for a session. `role` is either `'user'` or `'assistant'`. Messages are never updated.

| Column | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `uuid` | yes | `gen_random_uuid()` | Message ID |
| `session_id` | `uuid` | yes | — | Session (FK → `sessions.id`) |
| `role` | `text` | yes | — | `'user'` or `'assistant'` |
| `content` | `text` | yes | — | Message text |
| `created_at` | `timestamptz` | yes | `now()` | Creation timestamp |

Constraints:

| Type | Name | Expression |
|---|---|---|
| `PRIMARY KEY` | `messages_pkey` | `id` |
| `FOREIGN KEY` | `messages_session_id_fkey` | `FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE` |
| `INDEX` | `ix_messages_session_id` | `messages(session_id, created_at ASC)` |

---

## Functions

### `set_updated_at()`

Trigger function. Sets `NEW.updated_at = NOW()` and returns `NEW`. Used by the `sessions_updated_at` trigger on the `sessions` table.
