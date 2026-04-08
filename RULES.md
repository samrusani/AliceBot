# Rules

## Product / Scope Rules

- Treat Alice as a memory and continuity layer first, not a broad autonomous agent platform.
- Keep the public v0.1 contract focused on capture, recall, resume, correction, and open loops.
- Do not widen channels, deep automation, or connector write breadth without explicit roadmap change.
- Do not block Phase 9 on hosted SaaS, Telegram, WhatsApp, or vertical workflow expansion.

## Architecture Rules

- Preserve shipped P5/P6/P7/P8 semantics while packaging for Phase 9.
- Keep public interop surfaces narrow and deterministic before broadening.
- Always compile context from durable sources, not transcript replay.
- Keep MCP tools small, stable, and schema-driven.

## Data / Import Rules

- Preserve append-only continuity, correction, and revision history.
- Keep imported provenance explicit with source-specific dedupe keys.
- Importers must map or reject unknown external lifecycle/status values; do not silently coerce to `active`.
- Do not silently overwrite stale or superseded truth.

## Launch Docs / Release Rules

- Public docs are product surface in `P9-S38` and must match runnable commands.
- Every public claim must be anchored to shipped code paths, fixtures, tests, or committed evidence artifacts.
- Do not introduce launch copy that implies unshipped features.
- Keep release checklists and runbooks machine-independent and local-first.
- Any release-gating command that is stateful by user scope (for example eval harnesses) must include deterministic preconditions (fresh user scope or clean database scope).

## Deployment / Ops Rules

- Canonical local startup path is: `docker compose up -d` -> `./scripts/migrate.sh` -> `./scripts/load_sample_data.sh` -> `APP_RELOAD=false ./scripts/api_dev.sh`.
- Keep docs and runbooks aligned with clean-machine behavior.
- Archive obsolete planning/runbook material instead of deleting when traceability matters.

## Testing Rules

- New public surfaces require smoke validation, not only unit tests.
- CLI/MCP/importer/evaluation claims must be reproducible from documented commands.
- Do not make public recall-quality or memory-quality claims without evidence artifacts.

## Legacy Compatibility Marker

Historical continuity keeps the v1 release-readiness validation scenario available for baseline evidence.
