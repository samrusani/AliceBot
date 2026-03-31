# Roadmap

## Current Position

- The canonical repo baseline remains through Phase 3 Sprint 9.
- Earlier Phase 4 increments are delivered on top of that baseline: run-aware execution linkage, idempotent replay controls, approval-to-run pause/resume linkage, explicit run transitions/stop reasons, bounded retry posture, explicit failure classes, and deterministic gate runners.
- Phase 4 Sprint 14 established the release-control layer: Phase 4 release-control is complete and remains the gate baseline, Phase 4 owns acceptance/readiness/validation semantics directly, canonical magnesium reorder ship-gate evidence is first-class, and compatibility gates stay green.
- Phase 4 Sprint 14 is the active release-control layer for gate-ownership semantics and compatibility validation commands.
- Phase 4 Sprint 15 adds deterministic MVP release-candidate rehearsal orchestration via `python3 scripts/run_phase4_release_candidate.py`, producing `artifacts/release/phase4_rc_summary.json` with explicit per-step evidence and final GO/NO_GO.
- Phase 4 Sprint 16 adds durable RC evidence retention: each rehearsal run now writes an archive copy plus append-only audit ledger at `artifacts/release/archive/index.json`, while preserving the latest-summary compatibility path.
- Phase 4 Sprint 17 hardens RC archive/index writes for concurrency: deterministic lock path (`artifacts/release/archive/index.lock`), bounded lock-timeout contract, and atomic index replace persistence.
- Phase 4 Sprint 18 adds formal closeout evidence tooling: deterministic MVP exit manifest generation (`python3 scripts/generate_phase4_mvp_exit_manifest.py`) and manifest verification (`python3 scripts/verify_phase4_mvp_exit_manifest.py`) from latest GO RC archive evidence.
- Phase 4 Sprint 19 adds deterministic MVP qualification orchestration (`python3 scripts/run_phase4_mvp_qualification.py`) and formal sign-off record verification (`python3 scripts/verify_phase4_mvp_signoff_record.py`) with explicit GO/NO_GO blocker registry.
- Phase 5 Sprint 17 adds the typed continuity capture backbone: immutable `continuity_capture_events`, typed `continuity_objects`, conservative admission posture (`DERIVED`/`TRIAGE`), and the fast capture inbox UI/API surface at `/continuity`.
- Phase 5 Sprint 18 adds provenance-backed recall and deterministic continuity resumption surfaces: `GET /v0/continuity/recall`, `GET /v0/continuity/resumption-brief`, and `/continuity` recall/resumption panels with always-present required sections.
- Phase 5 Sprint 19 adds continuity review/correction and freshness posture: `GET /v0/continuity/review-queue`, `GET /v0/continuity/review-queue/{continuity_object_id}`, `POST /v0/continuity/review-queue/{continuity_object_id}/corrections`, append-only correction events, and immediate recall/resumption correction impact with supersession-chain visibility.
- Phase 5 Sprint 20 adds deterministic open-loop/daily/weekly executive-function seams: `GET /v0/continuity/open-loops`, `GET /v0/continuity/daily-brief`, `GET /v0/continuity/weekly-review`, `POST /v0/continuity/open-loops/{continuity_object_id}/review-action`, grouped posture ordering (`waiting_for`, `blocker`, `stale`, `next_action`), and immediate resumption refresh after `done`/`deferred`/`still_blocked` actions.
- Phase 6 Sprint 21 adds canonical memory-quality gate and deterministic review prioritization seams: `GET /v0/memories/quality-gate` with canonical statuses (`healthy`, `needs_review`, `insufficient_sample`, `degraded`), deterministic queue ordering modes (`oldest_first`, `recent_first`, `high_risk_first`, `stale_truth_first`) on `GET /v0/memories/review-queue`, and `/memories` UI alignment to API-backed quality-gate semantics plus priority-mode selection.
- Phase 6 Sprint 22 adds retrieval-quality evaluation and recall ranking calibration seams: deterministic fixture-backed precision reporting via `GET /v0/continuity/retrieval-evaluation`, calibrated recall ordering that favors confirmed/fresher/current truth over stale/superseded alternatives, and explicit ordering posture evidence (`freshness`, `provenance`, `supersession`) in continuity recall API/UI surfaces.
- Phase 6 Sprint 23 adds correction-impact and freshness-hygiene reliability seams, including deterministic weekly review evidence fields for correction recurrence and freshness drift (`correction_recurrence_count`, `freshness_drift_count`) while preserving P6-S21/P6-S22 contracts.
- Phase 6 Sprint 24 adds trust dashboard and quality release evidence seams: `GET /v0/memories/trust-dashboard`, deterministic evidence generation via `python3 scripts/run_phase6_quality_evidence.py`, and additive quality evidence summary integration in Phase 4 readiness/release/validation reporting paths without changing GO/NO_GO semantics.
- Phase 6 is complete (`P6-S21` through `P6-S24` shipped).
- Phase 7 Sprint 25 adds deterministic chief-of-staff priority seams:
  - `GET /v0/chief-of-staff` for ranked priorities with explicit posture labels, provenance-backed rationale, trust-aware confidence posture, and deterministic recommended next action.
  - `/chief-of-staff` web dashboard for current priorities, rationale visibility, and explicit low-trust confidence downgrade rendering.
- Phase 7 Sprint 26 adds deterministic follow-through supervision seams on top of shipped P7-S25:
  - `GET /v0/chief-of-staff` now includes deterministic `overdue_items`, `stale_waiting_for_items`, `slipped_commitments`, `escalation_posture`, and governed `draft_follow_up` artifact fields.
  - follow-through recommendation actions are deterministic and explicit (`nudge`, `defer`, `escalate`, `close_loop_candidate`) with rationale per item.
  - draft follow-ups remain approval-bounded artifacts only (`draft_only`, no autonomous external send).
  - `/chief-of-staff` web now renders a dedicated follow-through supervision panel alongside the priority panel.
- Phase 7 Sprint 27 adds deterministic preparation and resumption supervision seams on top of shipped P7-S25/P7-S26:
  - `GET /v0/chief-of-staff` now also includes deterministic `preparation_brief`, `what_changed_summary`, `prep_checklist`, `suggested_talking_points`, and `resumption_supervision`.
  - preparation and resumption artifacts are provenance-backed and explicitly trust-calibrated.
  - low-trust memory posture explicitly downgrades preparation/resumption recommendation confidence.
  - `/chief-of-staff` web now renders a dedicated preparation panel with rationale and provenance visibility.
- Phase 7 Sprint 28 adds deterministic weekly review and recommendation outcome-learning seams on top of shipped P7-S25/P7-S26/P7-S27:
  - `GET /v0/chief-of-staff` now also includes `weekly_review_brief`, `recommendation_outcomes`, `priority_learning_summary`, and `pattern_drift_summary`.
  - `POST /v0/chief-of-staff/recommendation-outcomes` captures explicit recommendation handling outcomes (`accept`, `defer`, `ignore`, `rewrite`) as auditable continuity records.
  - weekly review guidance now explicitly ranks close/defer/escalate actions with deterministic rationale.
  - `/chief-of-staff` web now renders a weekly review and learning panel with outcome-capture controls and drift visibility.
- Phase 8 Sprint 29 adds deterministic chief-of-staff action handoff artifacts on top of shipped P7 outputs:
  - `GET /v0/chief-of-staff` now also includes `action_handoff_brief`, `handoff_items`, `task_draft`, `approval_draft`, and explicit `execution_posture`.
  - handoff mapping deterministically selects top recommendations from priority/follow-through/preparation/weekly-review signals and emits governed task/approval draft structures with rationale + provenance.
  - execution posture is explicit and non-autonomous (`approval_bounded_artifact_only`, `approval_required=true`, no autonomous side effects).
  - `/chief-of-staff` web now renders an action handoff panel showing posture, primary task/approval drafts, and per-item rationale/provenance.
- Phase 7 is complete (`P7-S25` through `P7-S28` shipped).
- Active post-Phase-7 sprint is Phase 8 Sprint 29: chief-of-staff action handoff artifacts.
- Phase 8 planning anchors are:
  - `docs/phase8-product-spec.md`
  - `docs/phase8-sprint-29-32-plan.md`
- The backend baseline now includes continuity APIs, deterministic context compilation, governed request routing, approvals and execution review, typed memory and open-loop seams, deterministic thread resumption brief reads, unified explicit-signal capture seams, explicit task and task-step lifecycle seams, rooted local workspaces and artifact ingestion, artifact retrieval and embeddings, narrow read-only Gmail and Calendar seams with selected-item ingestion, bounded read-only Calendar event discovery for one connected account, and the no-tools assistant-response seam.
- The frontend baseline is now real product surface, not scaffolding: the Next.js operator shell ships `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/chief-of-staff`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback when they are not.
- `/chat` now uses selected-thread continuity instead of a raw thread-id-first flow, keeps bounded thread review and deterministic resumption brief review visible beside both assistant and governed-request composition, ships thread-linked governed workflow, ordered task-step timeline review, and bounded explain-why trace embedding, and includes manual explicit-signal capture controls for selected `message.user` events.
- `/gmail` and `/calendar` are shipped bounded connector workspaces in the shell: account review, selected-account detail, explicit connect, and one selected-item ingestion path into one chosen task workspace. The API baseline also includes bounded Calendar event discovery for one connected account with deterministic ordering and bounded limits.
- `/memories`, `/entities`, and `/artifacts` are shipped bounded review workspaces in the shell, not planned surface.
- Gate ownership is canonicalized to Phase 4 runner scripts (`scripts/run_phase4_*.py`), while `python3 scripts/run_phase3_validation_matrix.py`, `python3 scripts/run_phase2_validation_matrix.py`, and `python3 scripts/run_mvp_validation_matrix.py` remain compatibility guarantees.
- Historical sprint detail belongs in build and review artifacts, not in this roadmap.

## Next Delivery Focus

### Build From The Shipped API Plus Web-Shell Baseline

- Plan the next sprint from the implemented Phase 3 Sprint 9 backend-plus-web baseline, not from older pre-Phase-3 narratives.
- Treat transcript continuity, thread-linked workflow review, task-step timeline review, bounded explain-why embedding in `/chat`, deterministic resumption brief review, manual explicit-signal capture controls, the shipped review workspaces (`/memories`, `/entities`, `/artifacts`), the shipped connector workspaces (`/gmail`, `/calendar`), and bounded Calendar event discovery as baseline, not pending work.
- Treat `python3 scripts/run_phase4_release_candidate.py` as the canonical MVP release-candidate rehearsal command and evidence contract (latest summary + append-only archive ledger).
- Treat `python3 scripts/verify_phase4_rc_archive.py` as the canonical archive audit verification command.
- Treat `python3 scripts/generate_phase4_mvp_exit_manifest.py` and `python3 scripts/verify_phase4_mvp_exit_manifest.py` as required Phase 4 closeout commands for deterministic MVP phase-exit evidence.
- Treat `python3 scripts/run_phase4_mvp_qualification.py` and `python3 scripts/verify_phase4_mvp_signoff_record.py` as the canonical Sprint 19 MVP qualification/sign-off commands.
- Treat archive index hardening as baseline behavior (deterministic lock and atomic index replace), not optional operational guidance.
- Treat the deterministic validation matrix command (`python3 scripts/run_phase4_validation_matrix.py`) as the canonical Phase 4 validation step inside the RC rehearsal chain, while keeping Phase 3/Phase 2/MVP validation commands as compatibility checks.
- Treat Phase 5 Sprint 17 through Sprint 20 continuity surfaces as shipped baseline:
  - `/v0/continuity/captures*`
  - `/v0/continuity/recall`
  - `/v0/continuity/resumption-brief`
  - `/v0/continuity/review-queue*`
  - `/v0/continuity/open-loops`
  - `/v0/continuity/daily-brief`
  - `/v0/continuity/weekly-review`
  - `/v0/continuity/open-loops/{continuity_object_id}/review-action`
  - `/continuity` capture/recall/resumption/review/open-loop/daily/weekly workspace
- Do not relitigate continuity backbone, recall ordering contracts, correction-event append semantics, open-loop posture contracts, or required resumption/brief section contracts.
- Favor one narrow seam that deepens operator use of already shipped contracts before widening connector breadth or orchestration scope.
- Reuse the existing continuity, response, approval, task, workspace-artifact, memory, entity, execution, and trace surfaces instead of introducing parallel contracts.

### Keep New Scope Narrow

- Do not bundle broader Gmail or Calendar breadth, auth expansion, richer document parsing, runner orchestration, or proxy breadth into the next sprint by default.
- Do not reopen schema or API design unless the next sprint explicitly requires it.
- Keep Phase 5 follow-up scope explicit:
  - no additional Sprint 17-20 continuity scope remains
  - P6-S21 memory-quality gate alignment and deterministic review prioritization is now shipped baseline
  - P6-S22 retrieval-quality calibration is now shipped baseline
  - P6-S23 correction impact and freshness hygiene is now shipped baseline
  - P6-S24 trust dashboard and quality release evidence is now shipped baseline
  - P7-S25 priority engine and chief-of-staff dashboard is now shipped baseline
  - P7-S26 follow-through supervision is now shipped baseline
  - P7-S27 preparation briefs and resumption supervision is now shipped baseline
  - P7-S28 weekly review and outcome learning is now shipped baseline
  - active post-Phase-7 packet is P8-S29 chief-of-staff action handoff artifacts
  - do not reopen P6-S21/P6-S22/P6-S23/P6-S24 contracts while operating on post-P6-S24 follow-up scope
  - do not reopen P7-S25/P7-S26/P7-S27/P7-S28 semantics while executing P8-S29
  - do not fold post-Phase-5 work back into shipped Sprint 20 seams
- Keep live docs synchronized with shipped reality so planning does not drift behind the repo again.

## Ongoing Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth remains incomplete beyond the current database user-context model.
- The operator shell is now shipped surface, including `/gmail` and `/calendar`, so future drift between web UI behavior, backend seams, and canonical docs is a planning and review risk.
- Connector and document boundaries are still intentionally narrow; broadening them safely will require separate explicit sprints.

## Deferred Until Explicitly Opened

- Gmail search, mailbox sync, attachment ingestion, write-capable Gmail actions, and broader Calendar capabilities such as recurrence expansion, sync, and write actions
- runner-style orchestration and automatic multi-step progression
- richer document parsing, OCR, and layout-aware ingestion
- broader tool execution breadth beyond the current governed `proxy.echo` seam
