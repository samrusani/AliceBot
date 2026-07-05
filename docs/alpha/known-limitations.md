# Public Alpha Known Limitations

This alpha is intentionally limited.

- local setup is still technical
- no hosted cloud
- no production SLA
- no Gmail OAuth
- no Calendar OAuth
- no live email polling
- no live calendar polling
- Telegram webhook automation is not packaged
- Telegram voice transcription is not packaged
- OCR execution is not packaged
- PDF OCR is not packaged
- voice transcription execution is not packaged
- browser clipper is a bookmarklet/MVP path
- scheduler is local
- model providers require user configuration
- secrets fallback is alpha-grade unless OS or managed secret provider is configured
- no automatic trusted-memory promotion
- passive memory capture is structured and English-biased; general conversation is not guaranteed to become memory
- `/vnext` is the operator console, not the main agent interface
- team accounts, billing, cloud sync, mobile app, and hosted deployment are out of scope

SQLite mode (`alice-memory mcp`) is the trial/single-agent path and carries extra boundaries:

- core MCP tools only (11 as of this release); the legacy continuity surfaces are Postgres-only
- no web console review — review runs through `alice_memory_review` / `alice_memory_correct`
- no scheduler
- one user per local database file
- no automatic migration to Postgres; `alice-memory export` gets your data out and `alice-memory import` loads an export into another local database (ids and timestamps preserved)
- embedding vectors are not exported: after `alice-memory import`, memories are keyword-searchable (FTS) immediately but stay out of vector search until re-embedded — configure `ALICE_EMBEDDINGS_*` and touch or re-commit the imported memories
- import never overwrites existing rows: colliding ids are skipped (default) or abort the import (`--mode fail`)
- users, agent identities/API keys, and entity relationship history are not part of the export/import surface; soft-deleted rows stay behind

Do not describe this alpha as hosted SaaS, production-ready, or automatic memory autopilot.
