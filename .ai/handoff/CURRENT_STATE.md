# Current State

## Canonical Truth

- The canonical baseline remains through Phase 3 Sprint 9.
- Earlier Phase 4 work is already delivered: task-run linkage to approvals/executions, idempotent proxy execution replay guards, approval pause/resume continuity for linked runs, run transition observability, explicit stop reasons, bounded retries with persisted posture, explicit failure classes, and deterministic Phase 4 gate runners.
- Active Sprint focus is Phase 4 Sprint 14 release-control ownership as canonical baseline. Current delivery has advanced through Phase 5 Sprint 20 open-loop daily/weekly continuity delivery on top of completed Phase 5 Sprint 17 capture backbone, completed Phase 5 Sprint 18 recall/resumption, completed Phase 5 Sprint 19 review/correction/freshness, and completed Phase 4 Sprint 14-19 release-control/sign-off delivery.
- Active post-Phase-5 packet P6-S21 memory-quality gate alignment and review prioritization is now shipped baseline.
- Phase 6 planning docs now exist and are the control anchors for post-Phase-5 sequencing:
  - `docs/phase6-product-spec.md`
  - `docs/phase6-sprint-21-24-plan.md`
  - `docs/phase6-memory-quality-model.md`
- The accepted baseline includes deterministic Phase 3 gate entrypoints: `python3 scripts/run_phase3_acceptance.py`, `python3 scripts/run_phase3_readiness_gates.py`, and `python3 scripts/run_phase3_validation_matrix.py` (default go/no-go command).
- Phase 4 gate entrypoints are `python3 scripts/run_phase4_acceptance.py`, `python3 scripts/run_phase4_readiness_gates.py`, and `python3 scripts/run_phase4_validation_matrix.py`.
- Phase 4 release-candidate rehearsal entrypoint is `python3 scripts/run_phase4_release_candidate.py`, which writes latest summary evidence at `artifacts/release/phase4_rc_summary.json` and appends retained archive/index evidence under `artifacts/release/archive/` for repeated-run audit, with deterministic archive index lock path `artifacts/release/archive/index.lock`, bounded lock-timeout failure contract, and atomic index replace writes.
- Archive audit verifier entrypoint is `python3 scripts/verify_phase4_rc_archive.py`.
- Phase 4 MVP exit manifest entrypoints are `python3 scripts/generate_phase4_mvp_exit_manifest.py` and `python3 scripts/verify_phase4_mvp_exit_manifest.py`, producing deterministic closeout evidence at `artifacts/release/phase4_mvp_exit_manifest.json` from latest GO RC archive evidence.
- Phase 4 MVP qualification/sign-off entrypoints are `python3 scripts/run_phase4_mvp_qualification.py` and `python3 scripts/verify_phase4_mvp_signoff_record.py`, producing deterministic qualification evidence at `artifacts/release/phase4_mvp_signoff_record.json` with ordered gate statuses, GO/NO_GO, and blocker registry.
- Gate ownership is canonicalized to Phase 4 runner script names; Phase 3/Phase 2/MVP commands remain supported compatibility entrypoints with identical semantics.
- Use [PRODUCT_BRIEF.md](../../PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](../../ARCHITECTURE.md) for implemented boundaries, [ROADMAP.md](../../ROADMAP.md) for forward planning, and [RULES.md](../../RULES.md) for durable operating rules.
- The live sprint reports are [BUILD_REPORT.md](../../BUILD_REPORT.md) and [REVIEW_REPORT.md](../../REVIEW_REPORT.md) at repo root; older accepted sprint history belongs in [docs/archive/sprints](../../docs/archive/sprints), not in this handoff.

## Implemented Surfaces

- `apps/api` is the core shipped product surface. It implements continuity, context compilation, assistant responses, typed memory and open-loop seams, deterministic thread resumption brief reads, unified explicit-signal capture seams, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact chunk retrieval and embeddings, traces, and narrow read-only Gmail and Calendar seams with selected-item ingestion plus bounded Calendar event discovery.
- Phase 5 Sprint 17 adds typed continuity capture seams:
  - `POST /v0/continuity/captures` always appends an immutable capture event and conservatively admits typed durable objects.
  - `GET /v0/continuity/captures` returns inbox rows with admission posture (`DERIVED`/`TRIAGE`) and optional derived object summary.
  - `GET /v0/continuity/captures/{capture_event_id}` returns capture detail with derived object and provenance when admitted.
- Phase 5 Sprint 18 adds continuity recall/resumption seams:
  - `GET /v0/continuity/recall` returns provenance-backed scoped recall results with deterministic ordering metadata, confirmation status, and admission posture.
  - `GET /v0/continuity/resumption-brief` compiles deterministic brief sections (`last_decision`, `open_loops`, `recent_changes`, `next_action`) with explicit empty states.
- Phase 5 Sprint 19 adds continuity review/correction seams:
  - `GET /v0/continuity/review-queue` returns correction-ready continuity objects with deterministic posture filtering.
  - `GET /v0/continuity/review-queue/{continuity_object_id}` returns selected-object review detail, correction-event history, and supersession chain links.
  - `POST /v0/continuity/review-queue/{continuity_object_id}/corrections` applies deterministic `confirm`/`edit`/`delete`/`supersede`/`mark_stale` actions.
  - correction events are append-only and persisted before lifecycle mutation.
  - continuity recall/resumption now reflects correction posture immediately, including freshness/supersession metadata (`last_confirmed_at`, `supersedes_object_id`, `superseded_by_object_id`) and deleted-object exclusion from recall payloads.
- Phase 5 Sprint 20 adds deterministic open-loop review and briefing seams:
  - `GET /v0/continuity/open-loops` returns grouped posture sections (`waiting_for`, `blocker`, `stale`, `next_action`) with deterministic ordering metadata.
  - `GET /v0/continuity/daily-brief` returns deterministic daily sections (`waiting_for_highlights`, `blocker_highlights`, `stale_items`, `next_suggested_action`) with explicit empty states.
  - `GET /v0/continuity/weekly-review` returns deterministic grouped sections plus posture rollup counts.
  - `POST /v0/continuity/open-loops/{continuity_object_id}/review-action` applies deterministic `done`/`deferred`/`still_blocked` actions with auditable correction-event payload mapping.
  - continuity resumption reflects open-loop review-action outcomes immediately.
- Phase 6 Sprint 21 adds canonical memory-quality and deterministic review-priority seams:
  - `GET /v0/memories/quality-gate` returns deterministic canonical gate status (`healthy`, `needs_review`, `insufficient_sample`, `degraded`) with precision/sample/risk counts and explicit computation backing fields.
  - `GET /v0/memories/review-queue` supports deterministic priority modes (`oldest_first`, `recent_first`, `high_risk_first`, `stale_truth_first`) with explicit summary ordering metadata plus per-item priority posture (`is_high_risk`, `is_stale_truth`, `priority_reason`).
  - `/memories` consumes API-backed quality-gate contract and exposes queue priority-mode selection without changing label vocabulary or submit flow semantics.
- `apps/web` is also a shipped surface now. The operator shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`, with live reads when API config is present and explicit fixture fallback when it is not.
- `/chat` now ships assistant-response mode, governed-request mode, visible thread selection, compact thread creation, selected-thread transcript continuity, deterministic resumption brief review, thread-linked governed workflow review, ordered task-step timeline review, bounded explain-why trace embedding, manual explicit-signal capture controls for selected `message.user` events, and bounded supporting continuity review over thread sessions and events.
- `/continuity` now ships the Phase 5 Sprint 17 + Sprint 18 + Sprint 19 + Sprint 20 continuity workspace:
  - capture submit (optional explicit signal), recent capture list, and capture detail with posture/provenance
  - recall query/results panel with scoped filters and provenance-backed result cards
  - deterministic resumption-brief panel with always-present required sections
  - review queue list/filter panel
  - selected-object correction form with correction-event history and supersession chain visibility
  - open-loop dashboard grouped by waiting-for/blocker/stale/next-action posture
  - daily brief panel and weekly review panel with explicit empty-state rendering
  - open-loop review-action controls (`done`, `deferred`, `still_blocked`) with immediate page refresh feedback
- `/gmail` ships a bounded Gmail operator workspace: account list review, selected-account detail, explicit account connection, and explicit single-message ingestion into one selected task workspace.
- `/calendar` ships a bounded Calendar operator workspace: account list review, selected-account detail, explicit account connection, and explicit single-event ingestion into one selected task workspace. The shipped API baseline now also includes bounded read-only event discovery for one selected account (`GET /v0/calendar-accounts/{calendar_account_id}/events`) with deterministic ordering metadata and bounded limits.
- `/memories` ships a bounded memory review workspace: active/queue list posture, selected memory detail, revision review, and memory-label review/submit seams with explicit live/fixture/unavailable states.
- `/entities` ships a bounded entity review workspace: list, selected entity detail, and related edge review with explicit live/fixture/unavailable states.
- `/artifacts` ships a bounded artifact review workspace: list, selected artifact detail, linked task-workspace summary, and ordered chunk evidence with explicit live/fixture/unavailable states.
- `workers` remains scaffold-only.

## Current Boundaries

- Continuity stays explicit and thread-scoped: thread create/list/detail plus session/event review and deterministic thread resumption-brief reads are live; thread rename, archive, search, pagination, and event mutation are not.
- Assistant replies go only through `POST /v0/responses`, persist immutable continuity events, and return linked compile and response traces.
- Explain-why in `/chat` is selected-thread scoped and bounded: it reuses shipped trace list/detail/event reads, shows linked trace shortcuts from transcript/workflow/timeline context, and keeps full trace workspace in `/traces`.
- Governed actions still route through policy, allowlist, approval, and approved-only proxy execution; `proxy.echo` is still the only live execution handler.
- Task workspaces and artifacts remain rooted local boundaries. Ingestion remains narrow to plain text, markdown, narrow PDF text, narrow DOCX text from `word/document.xml`, and narrow RFC822 extraction.
- Gmail and Calendar remain read-only connector surfaces. Calendar now includes bounded event discovery for one selected account plus selected-event ingestion. Secret material stays behind dedicated secret-manager seams, the Gmail `legacy_db_v0` transition path still exists for older credential rows, and the shipped web workspaces stay bounded to account review, explicit connect, and one-item ingestion into one selected task workspace.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Connector breadth, richer parsing, and orchestration are still deferred; docs must stay synchronized with the shipped API-plus-web baseline, including `/gmail` and `/calendar`, so planning does not drift again.
- Phase 5 remaining scope:
  - none from Sprint 17-20 continuity plan.
- Post-Phase-5 active scope:
  - P6-S21 is shipped; next planned seam is P6-S22 retrieval quality evaluation and ranking calibration.

## Repo Evidence To Trust

- Backend continuity and response seams: `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`
- Backend Gmail and Calendar seams: `tests/integration/test_gmail_accounts_api.py`, `tests/integration/test_calendar_accounts_api.py`, `tests/unit/test_gmail.py`, `tests/unit/test_calendar.py`, `tests/unit/test_calendar_main.py`, `tests/unit/test_20260316_0026_gmail_accounts.py`, `tests/unit/test_20260319_0030_calendar_accounts_and_credentials.py`
- Web `/chat` continuity + workflow/timeline/explainability adoption: `apps/web/app/chat/page.tsx`, `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.tsx`, `apps/web/components/thread-summary.tsx`, `apps/web/components/thread-event-list.tsx`, `apps/web/components/response-composer.tsx`, `apps/web/components/thread-workflow-panel.tsx`, `apps/web/components/task-step-list.tsx`, `apps/web/components/response-history.tsx`, `apps/web/components/thread-trace-panel.tsx`, and matching component tests.
- Web review workspaces added through the accepted Sprint 6P/6Q/6R sequence: `apps/web/app/memories/page.tsx`, `apps/web/app/memories/page.test.tsx`, `apps/web/app/entities/page.tsx`, `apps/web/app/entities/page.test.tsx`, `apps/web/app/artifacts/page.tsx`, `apps/web/app/artifacts/page.test.tsx`.
- Web Gmail and Calendar workspaces: `apps/web/app/gmail/page.tsx`, `apps/web/app/calendar/page.tsx`, `apps/web/lib/api.ts`, `apps/web/lib/api.test.ts`, `apps/web/components/gmail-account-list.test.tsx`, `apps/web/components/calendar-account-list.test.tsx`, `apps/web/components/calendar-event-ingest-form.test.tsx`
- Web continuity workspace + retrieval/resumption/review/open-loop briefing surfaces: `apps/web/app/continuity/page.tsx`, `apps/web/app/continuity/page.test.tsx`, `apps/web/components/continuity-recall-panel.tsx`, `apps/web/components/continuity-recall-panel.test.tsx`, `apps/web/components/resumption-brief.tsx`, `apps/web/components/resumption-brief.test.tsx`, `apps/web/components/continuity-review-queue.tsx`, `apps/web/components/continuity-review-queue.test.tsx`, `apps/web/components/continuity-correction-form.tsx`, `apps/web/components/continuity-correction-form.test.tsx`, `apps/web/components/continuity-open-loops-panel.tsx`, `apps/web/components/continuity-open-loops-panel.test.tsx`, `apps/web/components/continuity-daily-brief.tsx`, `apps/web/components/continuity-daily-brief.test.tsx`, `apps/web/components/continuity-weekly-review.tsx`, `apps/web/components/continuity-weekly-review.test.tsx`
- Shell route inventory and discoverability: `apps/web/components/app-shell.tsx`, `apps/web/app/page.tsx`

## Planning Guardrails

- Plan from the implemented Phase 3 Sprint 9 repo state, not from older Sprint 5-era narratives.
- Do not describe broader Gmail scope, broader Calendar scope beyond bounded read-only event discovery plus selected-event ingestion, richer parsing, broader proxy execution, auth expansion, or runner orchestration as shipped.
- The immediate next move should be chosen from the current shipped backend-plus-web-shell baseline, including `/gmail`, `/calendar`, `/memories`, `/entities`, and `/artifacts`, not assumed to be leftover connector cleanup by default.
