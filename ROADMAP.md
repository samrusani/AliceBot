# Roadmap

## Current Position

- The accepted repo state is current through Sprint 7G.
- The backend baseline now includes continuity APIs, deterministic context compilation, governed request routing, approvals and execution review, explicit task and task-step lifecycle seams, rooted local workspaces and artifact ingestion, artifact retrieval and embeddings, narrow read-only Gmail and Calendar seams with selected-item ingestion, bounded read-only Calendar event discovery for one connected account, and the no-tools assistant-response seam.
- The frontend baseline is now real product surface, not scaffolding: the Next.js operator shell ships `/`, `/chat`, `/approvals`, `/tasks`, `/artifacts`, `/gmail`, `/calendar`, `/memories`, `/entities`, and `/traces`, with live-backend reads when configured and explicit fixture fallback when they are not.
- `/chat` now uses selected-thread continuity instead of a raw thread-id-first flow, keeps bounded thread review visible beside both assistant and governed-request composition, and ships thread-linked governed workflow, ordered task-step timeline review, and bounded explain-why trace embedding.
- `/gmail` and `/calendar` are shipped bounded connector workspaces in the shell: account review, selected-account detail, explicit connect, and one selected-item ingestion path into one chosen task workspace. The API baseline also includes bounded Calendar event discovery for one connected account with deterministic ordering and bounded limits.
- `/memories`, `/entities`, and `/artifacts` are shipped bounded review workspaces in the shell, not planned surface.
- Sprint 7G also established deterministic MVP release-candidate validation tooling; `python3 scripts/run_mvp_validation_matrix.py` is the default MVP go/no-go command.
- Historical sprint detail belongs in build and review artifacts, not in this roadmap.

## Next Delivery Focus

### Build From The Shipped API Plus Web-Shell Baseline

- Plan the next sprint from the implemented Sprint 7G backend-plus-web baseline, not from older pre-7G narratives.
- Treat transcript continuity, thread-linked workflow review, task-step timeline review, bounded explain-why embedding in `/chat`, the shipped review workspaces (`/memories`, `/entities`, `/artifacts`), the shipped connector workspaces (`/gmail`, `/calendar`), and bounded Calendar event discovery as baseline, not pending work.
- Treat the deterministic validation matrix command (`python3 scripts/run_mvp_validation_matrix.py`) as the default MVP release-candidate gate.
- Favor one narrow seam that deepens operator use of already shipped contracts before widening connector breadth or orchestration scope.
- Reuse the existing continuity, response, approval, task, workspace-artifact, memory, entity, execution, and trace surfaces instead of introducing parallel contracts.

### Keep New Scope Narrow

- Do not bundle broader Gmail or Calendar breadth, auth expansion, richer document parsing, runner orchestration, or proxy breadth into the next sprint by default.
- Do not reopen schema or API design unless the next sprint explicitly requires it.
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
