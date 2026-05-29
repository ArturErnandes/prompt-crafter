# Database Contract

## 1. Migration overview

### `001_create_users`

Creates table `users`.

### `002_create_sessions`

Creates table `sessions` with index `ix_sessions_user_id`, trigger function `set_updated_at()`, and trigger `sessions_updated_at`.

### `003_create_messages`

Creates table `messages` with index `ix_messages_session_id`.

---

## 2. Table specifications

### 1. `users`

One row per user. MVP uses a single hardcoded user (`id = 1`); schema supports multiple users.

| Column | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `serial` | yes | auto | User ID |
| `name` | `text` | yes | — | User display name |
| `created_at` | `timestamptz` | yes | `now()` | Creation timestamp |

Constraints:

| Type | Name | Expression |
|---|---|---|
| `PRIMARY KEY` | `users_pkey` | `id` |

---

### 2. `sessions`

One session groups a multi-turn conversation. `title` is set by the service after the first exchange. `updated_at` is maintained by a DB trigger, not application code.

| Column | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `uuid` | yes | `gen_random_uuid()` | Session ID |
| `user_id` | `integer` | yes | — | Owner (FK → `users.id`) |
| `template_name` | `text` | yes | `'default'` | Prompt template name |
| `title` | `text` | no | — | Session title |
| `created_at` | `timestamptz` | yes | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | yes | `now()` | Last update timestamp (via trigger) |

Constraints:

| Type | Name | Expression |
|---|---|---|
| `PRIMARY KEY` | `sessions_pkey` | `id` |
| `FOREIGN KEY` | `sessions_user_id_fkey` | `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` |
| `INDEX` | `ix_sessions_user_id` | `sessions(user_id)` |

Trigger: `sessions_updated_at` — BEFORE UPDATE, calls `set_updated_at()`.

---

### 3. `messages`

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
