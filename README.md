# AliceBot

AliceBot is a private, permissioned personal AI operating system. The current repo contains the accepted slice through Sprint 6R: a FastAPI backend plus a bounded Next.js operator shell.

## Current Implemented Slice

- `apps/api` is the core shipped surface. It includes continuity, context compilation, assistant responses, governed memory and retrieval, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact retrieval, traces, and the narrow read-only Gmail seam.
- `apps/web` is shipped operator UI, not scaffold-only. The shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/memories`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback otherwise.
- `/chat` supports both assistant and governed-request modes, selected-thread continuity, compact thread creation, thread-linked governed workflow review, ordered task-step timeline review, bounded explain-why trace embedding, and bounded supporting continuity review.
- `/artifacts`, `/memories`, and `/entities` are shipped bounded operator review workspaces for artifact, memory, and entity evidence.
- `workers` remains scaffold-only.

## Quick Start

1. Create a local env file: `cp .env.example .env`
2. Start infrastructure: `docker compose up -d`
3. Create a virtualenv and install dependencies: `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
4. Apply migrations: `./scripts/migrate.sh`
5. Start the API: `./scripts/api_dev.sh`

Useful checks:

- API health: [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- Backend tests: `./.venv/bin/python -m pytest tests/unit tests/integration`
- Web tests: `pnpm --dir apps/web test`
- Web shell: `pnpm --dir apps/web dev`

## Repo Map

- [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md): stable product scope and ship gates
- [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md): implemented technical boundaries
- [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md): forward planning from the current repo state
- [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md): durable engineering and scope rules
- [.ai/handoff/CURRENT_STATE.md](/Users/samirusani/Desktop/Codex/AliceBot/.ai/handoff/CURRENT_STATE.md): compact recovery snapshot
- [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md): current sprint build report
- [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md): current sprint review report
- [docs/archive/sprints](/Users/samirusani/Desktop/Codex/AliceBot/docs/archive/sprints): accepted historical sprint build and review artifacts

## Environment Notes

- Postgres is the system of record.
- Local Docker Compose includes Postgres with `pgvector`, Redis, and MinIO.
- Helper scripts source the repo-root `.env` and prefer `.venv/bin/python` when present.
- `TASK_WORKSPACE_ROOT` defaults to `/tmp/alicebot/task-workspaces`.
- `/healthz` performs a live Postgres check; Redis and MinIO are reported as configured but not live-checked.
