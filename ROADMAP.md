# Roadmap

## Current Position

- The accepted repo state is current through Sprint 5R.
- Milestone 5 now ships the rooted local workspace and artifact baseline end to end: workspace provisioning, artifact registration, narrow text ingestion, narrow PDF/DOCX/RFC822 ingestion, durable chunk storage, lexical artifact retrieval, compile-path artifact inclusion, artifact-chunk embeddings, direct semantic artifact retrieval, compile-path semantic artifact retrieval, and deterministic hybrid lexical-plus-semantic artifact merge in compile.
- The same milestone also now ships the narrow Gmail seam: read-only Gmail account persistence, secret-free account reads, protected credential storage in `gmail_account_credentials`, refresh-token renewal for expired access tokens, rotated refresh-token persistence when the provider returns a replacement token, and one explicit selected-message ingestion path that lands in the existing RFC822 artifact pipeline.
- This roadmap is future-facing from that shipped baseline; historical sprint-by-sprint detail lives in accepted build and review artifacts, not here.

## Next Delivery Focus

### Open One More Narrow Gmail Auth Seam On Top Of The Shipped Baseline

- Keep the next sprint auth-adjacent and narrow, building on the shipped protected-credential-backed Gmail seam rather than widening connector breadth.
- The next best seam is external secret-manager integration for the existing `gmail_account_credentials` boundary, without changing the read-only account contract or the single-message ingestion contract.
- Do not combine that work with Gmail search, mailbox sync, attachment ingestion, Calendar scope, UI work, or broader connector orchestration.

### Preserve Current Document, Compile, Governance, And Task Guarantees

- Keep the shipped PDF, DOCX, and RFC822 ingestion seams narrow and deterministic; richer parsing, OCR, layout reconstruction, attachment handling, and broader email processing still need separate later seams.
- Keep approvals, execution budgets, task/task-step state, and trace visibility deterministic as Milestone 5 continues.
- Preserve the shipped compile contract of one merged artifact section with explicit source provenance, deterministic lexical-first precedence, and trace-visible inclusion and exclusion decisions.
- Do not widen the current no-external-I/O proxy surface or introduce broader connector, runner, or UI scope until those areas are explicitly opened.

## After The Next Narrow Sprint

- Reassess broader connector work only after the current Gmail protected-credential boundary remains stable under externalized secret storage and the truth artifacts stay synchronized.
- Revisit workflow UI only after backend document and connector seams are accepted and the truth artifacts stay current.
- Revisit broader task orchestration only after the current explicit task-step seams remain stable under workspace, artifact, document, and connector flows.
- Continue to defer broader tool execution breadth and production auth/deployment hardening until the current governed surface remains stable.

## Dependencies

- Live truth docs must stay synchronized with accepted repo state so sprint planning does not start from stale assumptions.
- Rich document parsing work should continue to build on the shipped rooted local workspace, durable artifact chunk, and hybrid compile retrieval contracts.
- Connector work should remain read-only, single-message-only, approval-aware, and protected-credential-backed until a later sprint explicitly opens broader scope.
- Runner-style orchestration should stay deferred until the repo no longer depends on narrow current-step assumptions for safety and explainability.

## Ongoing Risks

- Memory extraction and retrieval quality remain the largest product risk.
- Auth beyond database user context is still missing.
- Milestone 5 can drift if Gmail auth hardening, broader connector breadth, UI, richer parsing, and orchestration work are mixed into one sprint instead of landing as narrow seams on top of the shipped document-ingestion and Gmail baseline.
