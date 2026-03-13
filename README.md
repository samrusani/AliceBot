# AliceBot

AliceBot is a private, permissioned personal AI operating system. The current repo contains the accepted backend slice through Sprint 5A plus local developer tooling.

## Current Implemented Slice

- `apps/api` is the shipped surface. It includes continuity storage, tracing, deterministic context compilation, governed memory admission and review, embeddings, semantic retrieval, entities, policy and tool governance, approval persistence and resolution, approved-only `proxy.echo` execution, execution budgets, tasks, task steps, explicit manual continuation lineage, step-linked approval/execution synchronization, and deterministic rooted local task-workspace provisioning.
- `apps/web` and `workers` are starter scaffolds only.
- Task workspaces are currently local rooted directories plus durable records. Artifact indexing, document ingestion, connectors, and runner orchestration are not shipped.

## Quick Start

1. Create a local env file: `cp .env.example .env`
2. Start infrastructure: `docker compose up -d`
3. Create a virtualenv and install dependencies: `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
4. Apply migrations: `./scripts/migrate.sh`
5. Start the API: `./scripts/api_dev.sh`

Useful checks:

- API health: [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- Full backend tests: `./.venv/bin/python -m pytest tests/unit tests/integration`
- Web shell: `pnpm --dir apps/web dev`

## Repo Map

- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md): stable product scope and ship gates.
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md): implemented technical boundaries and planned-later boundaries.
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md): forward-looking milestone direction from the current repo position.
- [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md): durable engineering and scope rules.
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md): compact current-state recovery snapshot.
- [.ai/active/SPRINT_PACKET.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/active/SPRINT_PACKET.md): active builder scope.
- [docs/archive/sprints](/Users/samirusani/Desktop/Codex/AliceBot/docs/archive/sprints): archived sprint build and review history.

## Environment Notes

- Postgres is the system of record.
- Local Docker Compose includes Postgres with `pgvector`, Redis, and MinIO.
- The helper scripts source the repo-root `.env` and prefer `.venv/bin/python` when present.
- `TASK_WORKSPACE_ROOT` defaults to `/tmp/alicebot/task-workspaces` and is the only allowed root for task-workspace provisioning.
- `/healthz` performs a live Postgres check; Redis and MinIO are reported as configured but not live-checked.
