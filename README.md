# AliceBot

AliceBot is a private, permissioned personal AI operating system. The canonical baseline remains through Phase 3 Sprint 9, with earlier Phase 4 work already delivering run linkage/idempotent replay safety and run observability/retry-failure discipline, Phase 4 Sprint 14 establishing canonical MVP release-gate ownership in Phase 4 gate scripts, Phase 4 Sprint 15 adding deterministic release-candidate rehearsal evidence packaging, Phase 4 Sprint 16 adding durable archive/index evidence retention for repeated RC rehearsal runs, Phase 4 Sprint 17 hardening archive index writes with deterministic locking and atomic replace behavior under contention, Phase 4 Sprint 18 adding deterministic MVP exit manifest generation/verification for formal phase closeout, and Phase 4 Sprint 19 adding deterministic MVP qualification orchestration plus a formal GO/NO_GO sign-off record/verifier. Phase 5 Sprint 17 shipped the typed continuity capture backbone, Phase 5 Sprint 18 shipped provenance-backed recall plus deterministic continuity resumption briefs, Phase 5 Sprint 19 shipped continuity review/correction with explicit freshness and supersession posture, Phase 5 Sprint 20 shipped open-loop dashboard plus deterministic daily/weekly review flows, Phase 6 Sprint 21 shipped canonical memory-quality gate semantics plus deterministic memory review-queue prioritization, Phase 6 Sprint 22 shipped retrieval-quality evaluation plus continuity-recall ranking calibration, Phase 6 Sprint 23 shipped correction-impact and freshness-hygiene weekly reliability signals, and Phase 6 Sprint 24 shipped trust dashboard and quality release evidence seams. Phase 6 is complete, Phase 7 is complete (`P7-S25` through `P7-S28`), Phase 8 Sprint 29 (P8-S29) and Sprint 30 (P8-S30) are shipped baseline, and the active sprint packet is Phase 8 Sprint 31 (P8-S31): governed execution routing. Phase 8 planning anchors are `docs/phase8-product-spec.md` and `docs/phase8-sprint-29-32-plan.md`.

## Current Implemented Slice

- `apps/api` is the core shipped surface. It includes continuity, context compilation, assistant responses, typed memory admission/review and open-loop lifecycle seams, deterministic thread resumption brief reads, explicit-signal capture, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact retrieval, traces, and narrow read-only Gmail and Calendar seams with bounded event discovery plus selected-item ingestion.
- `apps/api` now also ships Phase 7 Sprint 27 chief-of-staff preparation and resumption seams:
  - `GET /v0/chief-of-staff` continues deterministic P7-S25/P7-S26 ranking/follow-through output and now also includes:
    - `preparation_brief`
    - `what_changed_summary`
    - `prep_checklist`
    - `suggested_talking_points`
    - `resumption_supervision`
  - preparation and resumption recommendations are provenance-backed and trust-calibrated with explicit confidence posture.
  - low-trust memory posture visibly downgrades recommendation confidence in preparation and resumption artifacts.
  - `draft_follow_up` remains draft-only artifact output with explicit approval-bounded non-send posture (`mode=draft_only`, `approval_required=true`, `auto_send=false`).
  - all chief-of-staff composition still reuses shipped continuity + trust inputs (`continuity/recall`, `continuity/open-loops`, `continuity/resumption-brief`, `memories/trust-dashboard`) without widening connector or side-effect scope.
- `apps/api` now also ships Phase 7 Sprint 28 chief-of-staff weekly review and outcome-learning seams:
  - `GET /v0/chief-of-staff` now also includes deterministic `weekly_review_brief`, `recommendation_outcomes`, `priority_learning_summary`, and `pattern_drift_summary`.
  - `POST /v0/chief-of-staff/recommendation-outcomes` captures explicit recommendation outcomes (`accept`, `defer`, `ignore`, `rewrite`) as auditable continuity records.
  - weekly-review guidance is explicit and deterministic for close/defer/escalate decisions.
- `apps/api` now also ships Phase 8 Sprint 29 chief-of-staff action handoff seams:
  - `GET /v0/chief-of-staff` now also includes deterministic `action_handoff_brief`, `handoff_items`, `task_draft`, `approval_draft`, and `execution_posture`.
  - handoff items deterministically map top recommendations from priority/follow-through/preparation/weekly-review signals into governed task/approval-ready draft structures with explicit rationale and provenance.
  - execution posture is explicit and non-autonomous (`approval_bounded_artifact_only`, approval required, no autonomous execution or external side effects).
- `apps/api` now also ships Phase 8 Sprint 30 chief-of-staff handoff queue and review seams:
  - `GET /v0/chief-of-staff` now also includes deterministic `handoff_queue_summary`, `handoff_queue_groups`, and `handoff_review_actions`.
  - queue lifecycle posture is explicit (`ready`, `pending_approval`, `executed`, `stale`, `expired`) with deterministic grouped ordering metadata.
  - `POST /v0/chief-of-staff/handoff-review-actions` captures explicit operator review actions for lifecycle transitions as auditable continuity records.
  - stale and expired handoff items remain visible in grouped queue output and are not silently dropped.
- `apps/api` now also ships Phase 8 Sprint 31 chief-of-staff governed execution routing seams:
  - `GET /v0/chief-of-staff` now also includes deterministic `execution_routing_summary`, `routed_handoff_items`, `routing_audit_trail`, and `execution_readiness_posture`.
  - `POST /v0/chief-of-staff/execution-routing-actions` captures explicit routing transitions into governed draft targets (`task_workflow_draft`, `approval_workflow_draft`, `follow_up_draft_only`).
  - routing transitions are explicit and auditable (`routed`, `reaffirmed`) while keeping approval-required, draft-only non-autonomous posture.
- `apps/api` now also ships Phase 6 Sprint 21 memory-quality seams:
  - `GET /v0/memories/quality-gate` for canonical server-side quality posture (`healthy`, `needs_review`, `insufficient_sample`, `degraded`) with deterministic computation counts.
  - `GET /v0/memories/review-queue` supports explicit deterministic priority modes:
    - `oldest_first`
    - `recent_first`
    - `high_risk_first`
    - `stale_truth_first`
  - review-queue payloads include explicit ordering metadata and per-item priority posture fields.
- `apps/api` now also ships Phase 6 Sprint 22 retrieval-quality seams:
  - `GET /v0/continuity/retrieval-evaluation` returns deterministic fixture-backed precision summaries and top-result ordering evidence.
  - `GET /v0/continuity/recall` ranking metadata now explicitly surfaces freshness, provenance quality, and supersession posture contributions in deterministic ordering output.
- `apps/api` now also ships Phase 6 Sprint 24 trust/evidence seams:
  - `GET /v0/memories/trust-dashboard` aggregates canonical memory-quality gate posture, queue posture/aging summary, retrieval-quality summary, correction recurrence/freshness drift summary, and deterministic recommended next review action.
  - `python3 scripts/run_phase6_quality_evidence.py` writes deterministic quality evidence at `artifacts/release/phase6_quality_evidence.json`.
  - Phase 4 reporting scripts now include additive quality evidence summary sections without changing GO/NO_GO pass/fail semantics.
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
  - weekly review rollup includes deterministic correction/freshness evidence metrics: `correction_recurrence_count` and `freshness_drift_count`.
- `apps/web` is shipped operator UI, not scaffold-only. The shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/chief-of-staff`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback otherwise.
- `/chief-of-staff` now ships P7-S27 preparation/resumption supervision on top of P7-S25/P7-S26: deterministic priority dashboard, deterministic follow-through panel, and deterministic preparation panel with what-changed, checklist, talking points, and resumption supervision artifacts.
- `/chief-of-staff` now also ships P7-S28 weekly review and outcome-learning supervision: deterministic weekly review guidance, explicit recommendation outcome-capture controls, and visible priority-learning/pattern-drift summaries.
- `/chief-of-staff` now also ships P8-S29 action handoff supervision: explicit approval-bounded execution posture, deterministic handoff brief, and visible task/approval draft artifacts with provenance-backed rationale.
- `/chief-of-staff` now also ships P8-S30 queue and operational review supervision: deterministic grouped handoff queue posture, explicit stale/expired visibility, and operator lifecycle review controls with auditable review-action history.
- `/chief-of-staff` now also ships P8-S31 governed execution routing supervision: explicit execution-readiness posture, route controls for governed draft targets, and auditable routing transition history.
- `/memories` is aligned to Phase 6 Sprint 21 canonical memory-quality semantics:
  - quality gate posture is consumed from API-backed `GET /v0/memories/quality-gate` contract via the web API layer.
  - queue review mode can be selected explicitly (`oldest_first`, `recent_first`, `high_risk_first`, `stale_truth_first`) without breaking existing `submit` / `submit_and_next` labeling flow.
- `apps/web` now also includes `/continuity` as the Phase 5 continuity workspace with:
  - Sprint 17 fast-capture inbox submit/list/detail
  - Sprint 18 recall query/results panel with provenance-backed cards
  - Sprint 22 recall ranking posture evidence in UI (`freshness`, `provenance`, `supersession`)
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
- Phase 6 quality evidence command: `python3 scripts/run_phase6_quality_evidence.py` (writes deterministic trust-dashboard evidence artifact for release/readiness reporting).
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
- [docs/phase8-product-spec.md](docs/phase8-product-spec.md): Phase 8 product scope and constraints
- [docs/phase8-sprint-29-32-plan.md](docs/phase8-sprint-29-32-plan.md): Phase 8 sprint sequencing
- [docs/archive/sprints](docs/archive/sprints): accepted historical sprint build and review artifacts

## Environment Notes

- Postgres is the system of record.
- Local Docker Compose includes Postgres with `pgvector`, Redis, and MinIO.
- Helper scripts source the repo-root `.env` and prefer `.venv/bin/python` when present.
- `TASK_WORKSPACE_ROOT` defaults to `/tmp/alicebot/task-workspaces`.
- `/healthz` performs a live Postgres check; Redis and MinIO are reported as configured but not live-checked.
