# Rules

## Product / Scope Rules

- Treat Alice as a memory and continuity layer first, not a broad autonomous agent platform.
- Do not widen channels, deep automation, or connector write breadth without an explicit roadmap change.
- Keep the public v0.1 contract focused on capture, recall, resume, correction, and open loops.
- Do not block Phase 9 on hosted SaaS, Telegram, WhatsApp, or deep vertical workflows.

## Architecture Rules

- Preserve shipped P5/P6/P7/P8 semantics while packaging for Phase 9.
- Keep public interop surfaces narrow and deterministic before broadening them.
- Always compile context from durable sources, not transcript replay.
- Treat Postgres as the primary system of record unless a measured decision changes it.
- Keep MCP tools small, stable, and schema-driven.

## Coding Rules

- Build public packaging on top of existing seams instead of reimplementing continuity behavior.
- Keep CLI, MCP, importer, and adapter code module-scoped and test-backed.
- Prefer deterministic outputs and explicit provenance in public-facing commands and tools.
- Do not introduce public packaging shortcuts that bypass trust or approval boundaries.

## Data / Schema Rules

- Preserve append-only continuity, correction, and revision history.
- Keep imported data provenance explicit.
- Default memory admission to conservative behavior; do not loosen admission discipline for launch convenience.
- Do not silently overwrite stale or superseded truth.

## Deployment / Ops Rules

- Support one documented local startup path before adding alternative runtimes.
- For `P9-S33`, canonical startup is: `docker compose up -d` -> `./scripts/migrate.sh` -> `./scripts/load_sample_data.sh` -> `./scripts/api_dev.sh`.
- Public docs must match real install behavior on a clean machine.
- Keep machine-independent commands and links in canonical docs and runbooks.
- Archive obsolete planning or bootstrap material instead of deleting it when traceability matters.

## Testing Rules

- New public surfaces require install or smoke validation, not just unit tests.
- CLI commands need deterministic golden-output tests.
- MCP tools need stable contract tests.
- Importers need fixture-backed success, dedupe, and failure-path tests.
- Do not make public memory-quality or recall-quality claims without evaluation evidence.

## Legacy Compatibility Marker

Historical continuity keeps the v1 release-readiness validation scenario available for baseline evidence.
