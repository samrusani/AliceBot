# Current State

## Canonical Truth

- The working repo state is current through Sprint 6R.
- Use [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md) for implemented boundaries, [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md) for forward planning, and [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md) for durable operating rules.
- The live sprint reports are [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md) and [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md) at repo root; older accepted sprint history belongs in [docs/archive/sprints](/Users/samirusani/Desktop/Codex/AliceBot/docs/archive/sprints), not in this handoff.

## Implemented Surfaces

- `apps/api` is the core shipped product surface. It implements continuity, context compilation, assistant responses, governed memory and retrieval, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact chunk retrieval and embeddings, traces, and the narrow read-only Gmail seam with selected-message ingestion.
- `apps/web` is also a shipped surface now. The operator shell includes `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/memories`, `/entities`, and `/traces`, with live reads when API config is present and explicit fixture fallback when it is not.
- `/chat` now ships assistant-response mode, governed-request mode, visible thread selection, compact thread creation, selected-thread transcript continuity, thread-linked governed workflow review, ordered task-step timeline review, bounded explain-why trace embedding, and bounded supporting continuity review over thread sessions and events.
- `/memories` ships a bounded memory review workspace: active/queue list posture, selected memory detail, revision review, and memory-label review/submit seams with explicit live/fixture/unavailable states.
- `/entities` ships a bounded entity review workspace: list, selected entity detail, and related edge review with explicit live/fixture/unavailable states.
- `/artifacts` ships a bounded artifact review workspace: list, selected artifact detail, linked task-workspace summary, and ordered chunk evidence with explicit live/fixture/unavailable states.
- `workers` remains scaffold-only.

## Current Boundaries

- Continuity stays explicit and thread-scoped: thread create/list/detail plus session and event review are live; thread rename, archive, search, pagination, and event mutation are not.
- Assistant replies go only through `POST /v0/responses`, persist immutable continuity events, and return linked compile and response traces.
- Explain-why in `/chat` is selected-thread scoped and bounded: it reuses shipped trace list/detail/event reads, shows linked trace shortcuts from transcript/workflow/timeline context, and keeps full trace workspace in `/traces`.
- Governed actions still route through policy, allowlist, approval, and approved-only proxy execution; `proxy.echo` is still the only live execution handler.
- Task workspaces and artifacts remain rooted local boundaries. Ingestion remains narrow to plain text, markdown, narrow PDF text, narrow DOCX text from `word/document.xml`, and narrow RFC822 extraction.
- Gmail remains read-only and selected-message-only, with secret material handled through the dedicated secret-manager seam and the remaining `legacy_db_v0` transition path still present for older credential rows.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Connector breadth, richer parsing, and orchestration are still deferred; docs must stay synchronized with the shipped API-plus-web baseline so planning does not drift again.

## Repo Evidence To Trust

- Backend continuity and response seams: `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`
- Web `/chat` continuity + workflow/timeline/explainability adoption: `apps/web/app/chat/page.tsx`, `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.tsx`, `apps/web/components/thread-summary.tsx`, `apps/web/components/thread-event-list.tsx`, `apps/web/components/response-composer.tsx`, `apps/web/components/thread-workflow-panel.tsx`, `apps/web/components/task-step-list.tsx`, `apps/web/components/response-history.tsx`, `apps/web/components/thread-trace-panel.tsx`, and matching component tests.
- Web review workspaces added through the accepted Sprint 6P/6Q/6R sequence: `apps/web/app/memories/page.tsx`, `apps/web/app/memories/page.test.tsx`, `apps/web/app/entities/page.tsx`, `apps/web/app/entities/page.test.tsx`, `apps/web/app/artifacts/page.tsx`, `apps/web/app/artifacts/page.test.tsx`.
- Shell route inventory and discoverability: `apps/web/components/app-shell.tsx`, `apps/web/app/page.tsx`

## Planning Guardrails

- Plan from the implemented Sprint 6R repo state, not from older Sprint 5-era narratives.
- Do not describe broader Gmail scope, Calendar work, richer parsing, broader proxy execution, auth expansion, or runner orchestration as shipped.
- The immediate next move should be chosen from the current shipped backend-plus-web-shell baseline, including `/memories`, `/entities`, and `/artifacts`, not assumed to be leftover Gmail cleanup by default.
