# AliceBot

AliceBot is a private, permissioned personal AI operating system. The canonical baseline remains through Phase 3 Sprint 9, with earlier Phase 4 work already delivering run linkage/idempotent replay safety and run observability/retry-failure discipline, Phase 4 Sprint 14 establishing canonical MVP release-gate ownership in Phase 4 gate scripts, Phase 4 Sprint 15 adding deterministic release-candidate rehearsal evidence packaging, Phase 4 Sprint 16 adding durable archive/index evidence retention for repeated RC rehearsal runs, Phase 4 Sprint 17 hardening archive index writes with deterministic locking and atomic replace behavior under contention, Phase 4 Sprint 18 adding deterministic MVP exit manifest generation/verification for formal phase closeout, and Phase 4 Sprint 19 adding deterministic MVP qualification orchestration plus a formal GO/NO_GO sign-off record/verifier. Phase 5 Sprint 17 shipped the typed continuity capture backbone, Phase 5 Sprint 18 shipped provenance-backed recall plus deterministic continuity resumption briefs, Phase 5 Sprint 19 shipped continuity review/correction with explicit freshness and supersession posture, Phase 5 Sprint 20 shipped open-loop dashboard plus deterministic daily/weekly review flows, and Phase 6 Sprint 21 shipped canonical memory-quality gate semantics plus deterministic memory review-queue prioritization.

## Current Implemented Slice

- `apps/api` is the core shipped surface. It includes continuity, context compilation, assistant responses, typed memory admission/review and open-loop lifecycle seams, deterministic thread resumption brief reads, explicit-signal capture, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact retrieval, traces, and narrow read-only Gmail and Calendar seams with bounded event discovery plus selected-item ingestion.
- `apps/api` now also ships Phase 6 Sprint 21 memory-quality seams:
  - `GET /v0/memories/quality-gate` for canonical server-side quality posture (`healthy`, `needs_review`, `insufficient_sample`, `degraded`) with deterministic computation counts.
  - `GET /v0/memories/review-queue` supports explicit deterministic priority modes:
    - `oldest_first`
    - `recent_first`
    - `high_risk_first`
    - `stale_truth_first`
  - review-queue payloads include explicit ordering metadata and per-item priority posture fields.
- `apps/api` now also ships Phase 5 continuity capture/retrieval/review seams:
  - capture backbone endpoints from Sprint 17:
    - `POST /v0/continuity/captures`
    - `GET /v0/continuity/captures`
    - `GET /v0/continuity/captures/{capture_event_id}`
  - Sprint 18 retrieval/resumption endpoints:
    - `GET /v0/continuity/recall`
    - `GET /v0/continuity/resumption-brief`
  - Sprint 19 review/correction endpoints:
    - `GET /v0/continuity/review-queue`
    - `GET /v0/continuity/review-queue/{continuity_object_id}`
    - `POST /v0/continuity/review-queue/{continuity_object_id}/corrections`
  - Sprint 20 open-loop and review briefing endpoints:
    - `GET /v0/continuity/open-loops`
    - `GET /v0/continuity/daily-brief`
    - `GET /v0/continuity/weekly-review`
    - `POST /v0/continuity/open-loops/{continuity_object_id}/review-action`
  - recall/resumption responses expose scoped filters, deterministic ordering metadata, confirmation/admission posture, and provenance references.
  - correction flows append immutable correction events before lifecycle mutation and expose freshness/supersession metadata (`last_confirmed_at`, `supersedes_object_id`, `superseded_by_object_id`).
  - open-loop review actions (`done`, `deferred`, `still_blocked`) are deterministic, auditable, and reflected immediately in continuity resumption output.
- `apps/web` is shipped operator UI, not scaffold-only. The shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback otherwise.
- `/memories` is aligned to Phase 6 Sprint 21 canonical memory-quality semantics:
  - quality gate posture is consumed from API-backed `GET /v0/memories/quality-gate` contract via the web API layer.
  - queue review mode can be selected explicitly (`oldest_first`, `recent_first`, `high_risk_first`, `stale_truth_first`) without breaking existing `submit` / `submit_and_next` labeling flow.
- `apps/web` now also includes `/continuity` as the Phase 5 continuity workspace with:
  - Sprint 17 fast-capture inbox submit/list/detail
  - Sprint 18 recall query/results panel with provenance-backed cards
  - Sprint 18 deterministic resumption-brief panel with required explicit sections
  - Sprint 19 review queue and correction form with correction history and supersession chain visibility
  - Sprint 20 open-loop dashboard with grouped posture sections and review-action controls
  - Sprint 20 deterministic daily brief and weekly review panels with explicit empty states
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
- Phase 4 MVP qualification command: `python3 scripts/run_phase4_mvp_qualification.py` (runs RC rehearsal -> RC archive verify -> MVP exit manifest generation -> MVP exit manifest verify; writes `artifacts/release/phase4_mvp_signoff_record.json`)
- Phase 4 MVP sign-off verifier: `python3 scripts/verify_phase4_mvp_signoff_record.py` (validates sign-off schema, required references, and GO/NO_GO consistency)
- Phase 4 RC rehearsal command: `python3 scripts/run_phase4_release_candidate.py` (writes latest summary `artifacts/release/phase4_rc_summary.json` and appends archive evidence in `artifacts/release/archive/`)
- RC archive hardening contract: index updates are serialized by `artifacts/release/archive/index.lock`; lock timeout exits with code `2` and explicit failure message
- Phase 4 RC archive verifier: `python3 scripts/verify_phase4_rc_archive.py` (validates `artifacts/release/archive/index.json` against retained archive artifacts)
- Phase 4 MVP exit manifest generator: `python3 scripts/generate_phase4_mvp_exit_manifest.py` (writes deterministic closeout artifact `artifacts/release/phase4_mvp_exit_manifest.json` from latest GO RC archive evidence)
- Phase 4 MVP exit manifest verifier: `python3 scripts/verify_phase4_mvp_exit_manifest.py` (validates manifest schema, required fields, and source archive/index references)
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
