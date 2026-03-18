# Current State

## Canonical Truth

- The working repo state is current through Sprint 6I.
- Use [PRODUCT_BRIEF.md](/Users/samirusani/Desktop/Codex/AliceBot/PRODUCT_BRIEF.md) for product scope, [ARCHITECTURE.md](/Users/samirusani/Desktop/Codex/AliceBot/ARCHITECTURE.md) for implemented boundaries, [ROADMAP.md](/Users/samirusani/Desktop/Codex/AliceBot/ROADMAP.md) for forward planning, and [RULES.md](/Users/samirusani/Desktop/Codex/AliceBot/RULES.md) for durable operating rules.
- The live sprint reports are [BUILD_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md) and [REVIEW_REPORT.md](/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md) at repo root; older accepted sprint history belongs in [docs/archive/sprints](/Users/samirusani/Desktop/Codex/AliceBot/docs/archive/sprints), not in this handoff.

## Implemented Surfaces

- `apps/api` is the core shipped product surface. It implements continuity, context compilation, assistant responses, governed memory and retrieval, policy/tool/approval governance, execution budgets, tasks and task steps, rooted local workspaces and artifacts, artifact chunk retrieval and embeddings, traces, and the narrow read-only Gmail seam with selected-message ingestion.
- `apps/web` is also a shipped surface now. The operator shell includes `/`, `/chat`, `/approvals`, `/tasks`, and `/traces`, with live reads when API config is present and explicit fixture fallback when it is not.
- `/chat` now ships assistant-response mode, governed-request mode, visible thread selection, compact thread creation, and bounded continuity review over thread sessions and events.
- `workers` remains scaffold-only.

## Current Boundaries

- Continuity stays explicit and thread-scoped: thread create/list/detail plus session and event review are live; thread rename, archive, search, pagination, and event mutation are not.
- Assistant replies go only through `POST /v0/responses`, persist immutable continuity events, and return linked compile and response traces.
- Governed actions still route through policy, allowlist, approval, and approved-only proxy execution; `proxy.echo` is still the only live execution handler.
- Task workspaces and artifacts remain rooted local boundaries. Ingestion remains narrow to plain text, markdown, narrow PDF text, narrow DOCX text from `word/document.xml`, and narrow RFC822 extraction.
- Gmail remains read-only and selected-message-only, with secret material handled through the dedicated secret-manager seam and the remaining `legacy_db_v0` transition path still present for older credential rows.

## Active Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth is still incomplete beyond database user context.
- Connector breadth, richer parsing, and orchestration are still deferred, but the bigger short-term risk is planning from stale docs instead of the shipped API-plus-web baseline.

## Repo Evidence To Trust

- Backend continuity and response seams: `tests/integration/test_continuity_api.py`, `tests/integration/test_continuity_store.py`, `tests/integration/test_responses_api.py`
- Web continuity adoption: `apps/web/app/chat/page.tsx`, `apps/web/app/chat/page.test.tsx`, `apps/web/components/thread-list.tsx`, `apps/web/components/thread-summary.tsx`, `apps/web/components/thread-event-list.tsx`, `apps/web/components/response-composer.tsx`
- Broader shipped shell: `apps/web/app/approvals/page.tsx`, `apps/web/app/tasks/page.tsx`, `apps/web/app/traces/page.tsx`

## Planning Guardrails

- Plan from the implemented Sprint 6I repo state, not from older Sprint 5-era narratives.
- Do not describe broader Gmail scope, Calendar work, richer parsing, broader proxy execution, auth expansion, or runner orchestration as shipped.
- The immediate next move should be chosen from the current shipped backend-plus-web-shell baseline, not assumed to be leftover Gmail cleanup by default.
