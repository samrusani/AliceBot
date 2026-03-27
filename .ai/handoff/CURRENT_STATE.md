# Current State

## Canonical Truth

- The canonical baseline remains through Phase 3 Sprint 9.
- Phase 4 Sprint 12 is already delivered: task-run linkage to approvals/executions, idempotent proxy execution replay guards, and approval pause/resume continuity for linked runs.
- Active Sprint focus is Phase 4 Sprint 13: run transition observability, explicit stop reasons, bounded retries with persisted posture, explicit failure classes, and deterministic Phase 4 gate runners.
- The accepted baseline includes deterministic Phase 3 gate entrypoints: `python3 scripts/run_phase3_acceptance.py`, `python3 scripts/run_phase3_readiness_gates.py`, and `python3 scripts/run_phase3_validation_matrix.py` (default go/no-go command).
- Phase 4 gate entrypoints now exist at `python3 scripts/run_phase4_acceptance.py`, `python3 scripts/run_phase4_readiness_gates.py`, and `python3 scripts/run_phase4_validation_matrix.py`.
- Gate entrypoints are canonicalized to Phase 3 runner script names; `run_phase2_acceptance.py`, `run_phase2_readiness_gates.py`, `run_phase2_validation_matrix.py`, and `run_mvp_*` aliases remain supported compatibility entrypoints with identical semantics.
- Use [PRODUCT_BRIEF.md](../../PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](../../ARCHITECTURE.md) for implemented boundaries, [ROADMAP.md](../../ROADMAP.md) for forward planning, and [RULES.md](../../RULES.md) for durable operating rules.
- The live sprint reports are [BUILD_REPORT.md](../../BUILD_REPORT.md) and [REVIEW_REPORT.md](../../REVIEW_REPORT.md) at repo root; older accepted sprint history belongs in [docs/archive/sprints](../../docs/archive/sprints), not in this handoff.

## Implemented Surfaces

- `apps/api` is the core shipped product surface. It implements continuity, context compilation, assistant responses, typed memory and open-loop seams, deterministic thread resumption brief reads, unified explicit-signal capture seams, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact chunk retrieval and embeddings, traces, and narrow read-only Gmail and Calendar seams with selected-item ingestion plus bounded Calendar event discovery.
- `apps/web` is also a shipped surface now. The operator shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`, with live reads when API config is present and explicit fixture fallback when it is not.
- `/chat` now ships assistant-response mode, governed-request mode, visible thread selection, compact thread creation, selected-thread transcript continuity, deterministic resumption brief review, thread-linked governed workflow review, ordered task-step timeline review, bounded explain-why trace embedding, manual explicit-signal capture controls for selected `message.user` events, and bounded supporting continuity review over thread sessions and events.
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

## Repo Evidence To Trust

- Backend continuity and response seams: `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`
- Backend Gmail and Calendar seams: `tests/integration/test_gmail_accounts_api.py`, `tests/integration/test_calendar_accounts_api.py`, `tests/unit/test_gmail.py`, `tests/unit/test_calendar.py`, `tests/unit/test_calendar_main.py`, `tests/unit/test_20260316_0026_gmail_accounts.py`, `tests/unit/test_20260319_0030_calendar_accounts_and_credentials.py`
- Web `/chat` continuity + workflow/timeline/explainability adoption: `apps/web/app/chat/page.tsx`, `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.tsx`, `apps/web/components/thread-summary.tsx`, `apps/web/components/thread-event-list.tsx`, `apps/web/components/response-composer.tsx`, `apps/web/components/thread-workflow-panel.tsx`, `apps/web/components/task-step-list.tsx`, `apps/web/components/response-history.tsx`, `apps/web/components/thread-trace-panel.tsx`, and matching component tests.
- Web review workspaces added through the accepted Sprint 6P/6Q/6R sequence: `apps/web/app/memories/page.tsx`, `apps/web/app/memories/page.test.tsx`, `apps/web/app/entities/page.tsx`, `apps/web/app/entities/page.test.tsx`, `apps/web/app/artifacts/page.tsx`, `apps/web/app/artifacts/page.test.tsx`.
- Web Gmail and Calendar workspaces: `apps/web/app/gmail/page.tsx`, `apps/web/app/calendar/page.tsx`, `apps/web/lib/api.ts`, `apps/web/lib/api.test.ts`, `apps/web/components/gmail-account-list.test.tsx`, `apps/web/components/calendar-account-list.test.tsx`, `apps/web/components/calendar-event-ingest-form.test.tsx`
- Shell route inventory and discoverability: `apps/web/components/app-shell.tsx`, `apps/web/app/page.tsx`

## Planning Guardrails

- Plan from the implemented Phase 3 Sprint 9 repo state, not from older Sprint 5-era narratives.
- Do not describe broader Gmail scope, broader Calendar scope beyond bounded read-only event discovery plus selected-event ingestion, richer parsing, broader proxy execution, auth expansion, or runner orchestration as shipped.
- The immediate next move should be chosen from the current shipped backend-plus-web-shell baseline, including `/gmail`, `/calendar`, `/memories`, `/entities`, and `/artifacts`, not assumed to be leftover connector cleanup by default.
