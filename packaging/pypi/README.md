# alice-memory

**Alice — the continuity layer for AI agents.**

Alice is a local-first memory service that lets AI agents resume interrupted
work, track open loops, recall decisions with provenance, and improve when
corrected. Agents connect over MCP, HTTP API, or CLI; hybrid retrieval fuses
Postgres full-text and pgvector similarity with reciprocal-rank fusion.

This is an early name-holding release while the packaged runtime is prepared.
Until then, install and run Alice from the repository:

<https://github.com/samrusani/AliceBot>

Planned for this package: the zero-infrastructure SQLite on-ramp
(`uvx alice-memory` → a working MCP memory server in under a minute) and the
full Postgres-backed runtime.
