# Roadmap

## Current Position

- The accepted repo state is current through Sprint 6N.
- The backend baseline now includes continuity APIs, deterministic context compilation, governed request routing, approvals and execution review, explicit task and task-step lifecycle seams, rooted local workspaces and artifact ingestion, artifact retrieval and embeddings, the narrow read-only Gmail seam, and the no-tools assistant-response seam.
- The frontend baseline is now real product surface, not scaffolding: the Next.js operator shell ships `/`, `/chat`, `/approvals`, `/tasks`, and `/traces`, with live-backend reads when configured and explicit fixture fallback when they are not.
- `/chat` now uses selected-thread continuity instead of a raw thread-id-first flow, keeps bounded thread review visible beside both assistant and governed-request composition, and ships thread-linked governed workflow, ordered task-step timeline review, and bounded explain-why trace embedding.
- Historical sprint detail belongs in build and review artifacts, not in this roadmap.

## Next Delivery Focus

### Build From The Shipped API Plus Web-Shell Baseline

- Plan the next sprint from the current backend-plus-web baseline, not from the older Gmail-cleanup-only narrative.
- Treat transcript continuity, thread-linked workflow review, task-step timeline review, and bounded explain-why embedding in `/chat` as the baseline to build from, not as pending work.
- Favor one narrow seam that deepens operator use of already shipped contracts before widening connector breadth or orchestration scope.
- Reuse the existing continuity, response, approval, task, execution, and trace surfaces instead of introducing parallel contracts.

### Keep New Scope Narrow

- Do not bundle broader Gmail work, Calendar work, auth expansion, richer document parsing, runner orchestration, or proxy breadth into the next sprint by default.
- Do not reopen schema or API design unless the next sprint explicitly requires it.
- Keep live docs synchronized with shipped reality so planning does not drift behind the repo again.

## Ongoing Risks

- Memory extraction and retrieval quality remain the main product risk.
- Auth remains incomplete beyond the current database user-context model.
- The operator shell is now shipped surface, so future drift between web UI behavior, backend seams, and canonical docs is a planning and review risk.
- Connector and document boundaries are still intentionally narrow; broadening them safely will require separate explicit sprints.

## Deferred Until Explicitly Opened

- Gmail search, mailbox sync, attachment ingestion, write-capable Gmail actions, and Calendar connectors
- runner-style orchestration and automatic multi-step progression
- richer document parsing, OCR, and layout-aware ingestion
- broader tool execution breadth beyond the current governed `proxy.echo` seam
