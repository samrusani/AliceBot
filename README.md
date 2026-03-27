# AliceBot

AliceBot is a private, permissioned personal AI operating system. The canonical baseline remains through Phase 3 Sprint 9, with earlier Phase 4 work already delivering run linkage/idempotent replay safety and run observability/retry-failure discipline, and Phase 4 Sprint 14 establishing canonical MVP release-gate ownership in Phase 4 gate scripts.

## Current Implemented Slice

- `apps/api` is the core shipped surface. It includes continuity, context compilation, assistant responses, typed memory admission/review and open-loop lifecycle seams, deterministic thread resumption brief reads, explicit-signal capture, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact retrieval, traces, and narrow read-only Gmail and Calendar seams with bounded event discovery plus selected-item ingestion.
- `apps/web` is shipped operator UI, not scaffold-only. The shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback otherwise.
- `/chat` supports both assistant and governed-request modes, selected-thread continuity, compact thread creation, deterministic resumption brief review, thread-linked governed workflow review, ordered task-step timeline review, bounded explain-why trace embedding, manual explicit-signal capture controls for selected `message.user` events, and bounded supporting continuity review.
- `/gmail` and `/calendar` are shipped bounded connector workspaces for account review, selected-account detail, explicit account connection, and explicit single-item ingestion into one selected task workspace.
- `/artifacts`, `/memories`, and `/entities` are shipped bounded operator review workspaces for artifact, memory, and entity evidence.
- `workers` includes bounded task-run ticking and approved proxy execution progression under the workflow-style durable run model.

## Quick Start

1. Create a local env file: `cp .env.example .env`
2. Start infrastructure: `docker compose up -d`
3. Create a virtualenv and install dependencies: `python3 -m venv .venv && ./.venv/bin/python -m pip install -e '.[dev]'`
4. Apply migrations: `./scripts/migrate.sh`
5. Start the API: `./scripts/api_dev.sh`

Useful checks:

- Canonical gate entrypoints: `scripts/run_phase4_*.py` are the control-plane canonical MVP release gates; `scripts/run_phase3_*.py`, `scripts/run_phase2_*.py`, and `scripts/run_mvp_*.py` remain compatibility entrypoints with identical semantics.
- Phase 4 entrypoints: `python3 scripts/run_phase4_acceptance.py`, `python3 scripts/run_phase4_readiness_gates.py`, `python3 scripts/run_phase4_validation_matrix.py`
- API health: [http://127.0.0.1:8000/healthz](http://127.0.0.1:8000/healthz)
- Phase 3 acceptance gate: `python3 scripts/run_phase3_acceptance.py`
- Phase 3 readiness gates: `python3 scripts/run_phase3_readiness_gates.py`
- Phase 3 default go/no-go validation gate: `python3 scripts/run_phase3_validation_matrix.py`
- Phase 2 compatibility validation gate: `python3 scripts/run_phase2_validation_matrix.py`
- MVP alias gates (identical semantics): `python3 scripts/run_mvp_acceptance.py`, `python3 scripts/run_mvp_readiness_gates.py`, `python3 scripts/run_mvp_validation_matrix.py`
- Backend tests: `./.venv/bin/python -m pytest tests/unit tests/integration`
- Web tests: `pnpm --dir apps/web test`
- Web shell: `pnpm --dir apps/web dev`

## Repo Map

- [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md): stable product scope and release-readiness anchors
- [ARCHITECTURE.md](ARCHITECTURE.md): implemented technical boundaries
- [ROADMAP.md](ROADMAP.md): forward planning from the current repo state
- [RULES.md](RULES.md): durable engineering and scope rules
- [.ai/handoff/CURRENT_STATE.md](.ai/handoff/CURRENT_STATE.md): compact recovery snapshot
- [BUILD_REPORT.md](BUILD_REPORT.md): current sprint build report
- [REVIEW_REPORT.md](REVIEW_REPORT.md): current sprint review report
- [docs/archive/sprints](docs/archive/sprints): accepted historical sprint build and review artifacts

## Environment Notes

- Postgres is the system of record.
- Local Docker Compose includes Postgres with `pgvector`, Redis, and MinIO.
- Helper scripts source the repo-root `.env` and prefer `.venv/bin/python` when present.
- `TASK_WORKSPACE_ROOT` defaults to `/tmp/alicebot/task-workspaces`.
- `/healthz` performs a live Postgres check; Redis and MinIO are reported as configured but not live-checked.
