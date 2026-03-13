# Changelog

## 2026-03-11

- Redacted embedded Redis credentials from `/healthz` so the endpoint no longer echoes `REDIS_URL` secrets back to callers.
- Added readiness gating to `./scripts/dev_up.sh` so bootstrap waits for Postgres and `alicebot_app` role initialization before running migrations.
- Bound local Postgres, Redis, and MinIO ports to `127.0.0.1` by default and removed the unnecessary runtime-role `CONNECT` grant on the shared `postgres` database.
- Removed the redundant `(thread_id, sequence_no)` events index from the base continuity migration because the unique constraint already provides that index.
- Tightened architecture, roadmap, handoff, and builder-report wording so exposed routes and environment-specific verification claims stay accurate.
- Tightened the runtime Postgres role so the continuity tables are insert/select-only in the migration chain and for upgraded databases.
- Stopped the base migration downgrade from dropping shared `pgcrypto` and `vector` extensions.
- Made the local helper scripts prefer `.venv/bin/python` when the project virtualenv exists, falling back to `python3` otherwise.
- Corrected `/healthz` so only Postgres is reported as live-checked, while Redis and MinIO are surfaced as configured but `not_checked`.
- Fixed Alembic runtime URL handling so migrations use the installed `psycopg` SQLAlchemy driver instead of the missing `psycopg2` default.
- Fixed concurrent event append sequencing by acquiring the per-thread advisory lock before reading the next `sequence_no`.
- Verified the local foundation runtime with `docker compose up -d`, `./scripts/migrate.sh`, `./.venv/bin/python -m pytest tests/unit tests/integration`, and a live `GET /healthz`.

## 2026-03-10

- Bootstrapped the canonical project operating files.
- Created the initial AI handoff snapshot and first sprint packet.
- Added the recommended repo scaffolding directories for implementation work.
- Added local Docker Compose infrastructure for Postgres with `pgvector`, Redis, and MinIO.
- Added the FastAPI foundation scaffold, configuration loading, `/healthz`, and Alembic migration plumbing.
- Added continuity tables for `users`, `threads`, `sessions`, and append-only `events` with RLS and isolation tests.
- Fixed the local quick-start path so repo scripts source `.env`, use `python3`, and keep migrations pointed at the `alicebot` database.
- Serialized same-thread event appends before sequence allocation and added an integration test for concurrent event numbering.
