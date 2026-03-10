# AliceBot

AliceBot is a private, permissioned personal AI operating system. This repository currently holds the canonical product, architecture, roadmap, and AI handoff documents that future implementation work should follow.

## Status

- Planning has been distilled into durable operating docs.
- Application code has not been scaffolded yet.
- The first execution target is the foundation sprint in [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md).

## Quick Start Assumptions

- Assumption: local development will use Docker Compose for Postgres, Redis, and S3-compatible storage.
- Assumption: backend work will use Python 3.12 and FastAPI.
- Assumption: frontend work will use Node.js 20, `pnpm`, and Next.js.
- Secrets must stay out of the repo; use `.env` files locally and a secret manager in deployed environments.

## Repo Structure

- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md): permanent product truth.
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md): permanent technical truth.
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md): milestone sequence and delivery risks.
- [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md): durable engineering and scope rules.
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md): fresh-thread recovery snapshot.
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md): current builder sprint.
- `docs/adr/`: architecture decision records.
- `docs/runbooks/`: operational procedures.
- `docs/archive/`: source material and retired planning docs.
- `apps/api/`, `apps/web/`, `workers/`, `tests/`, `scripts/`: planned implementation areas.

## Essential Commands

- `docker compose up -d`: expected local infra start command once the foundation sprint lands.
- `alembic upgrade head`: expected database migration command once the API scaffold exists.
- `pytest`: expected backend and integration test entrypoint.
- `pnpm test`: expected frontend test entrypoint.
- `pnpm lint`: expected frontend lint entrypoint.

## Environment Notes

- Postgres is the planned system of record and must support `pgvector`.
- Redis is planned for queues, locks, and short-lived cache data.
- Object storage is planned for documents and task artifacts.
- Authentication, row-level security, and approval boundaries are first-class requirements from the start.
# AliceBot
