# migrate

A one-shot container that runs `alembic upgrade head` on startup and exits. Run it with `docker compose run` or declare it as a dependency with `condition: service_completed_successfully` before starting the API.

---

## 1. Purpose and boundaries

`migrate` is the single point for applying Alembic migrations to PostgreSQL.

The container reads `DATABASE_URL` from the environment, normalizes the scheme and query parameters, opens a connection via `NullPool`, and runs `alembic upgrade head`. It starts no persistent processes, never downgrades automatically, and does not create the database or roles — both must exist before the container starts.

---

## 2. Configuration

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection URL. Accepted schemes: `postgres://`, `postgresql://`, `postgresql+asyncpg://` |

`DATABASE_URL` takes priority over `sqlalchemy.url` in `alembic.ini`. Before passing the URL to SQLAlchemy, `env.py` normalizes the scheme to `postgresql://` and strips the `sslmode` parameter from the query string.

---

## 3. Startup behavior

On start, `env.py` reads `DATABASE_URL`, normalizes it, and opens a synchronous connection via `NullPool`. No persistent pool is needed; the container lives for seconds. Alembic then applies all migrations absent from `alembic_version` in order. The container exits with code `0` on success and a non-zero code on any connection or migration error.

---

## 4. Running

**One-off (dev / CI):**
```bash
docker compose run --rm migrate
```

**Downgrade (manual):**
```bash
docker compose run --rm migrate downgrade -1
```

---

## 5. Related documents

- `docs/database-contract.md` — DB schema and migration specifications
- `alembic/versions/` — migration files (0001–0003)
- `alembic/env.py` — URL normalization logic
