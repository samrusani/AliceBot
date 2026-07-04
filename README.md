# Alice

**The continuity layer for AI agents.**

![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-2ea043)

Alice is a local-first memory service that lets AI agents resume interrupted work, track open loops, recall decisions with provenance, and improve when corrected — instead of re-reading transcripts or trusting opaque summaries.

Agents connect over MCP, HTTP API, or CLI. Humans stay in control: agent writes land as policy-checked commits or reviewable proposals, and a local review console is where memory gets approved, corrected, or forgotten. That review boundary is a feature, not a limitation — it is what makes the memory trustworthy enough to act on.

## How Alice compares

Most agent memory tools — mem0, Zep, Letta, and similar — focus on extracting facts from conversations and retrieving them later. That solves recall, and they do it well. Alice focuses on continuity: it stores typed continuity objects (decisions, open loops, resumption briefs) alongside plain memories; every answer carries explainable provenance back to source evidence; and writes are review-governed, so an agent cannot silently promote a bad extraction into durable truth. If you mainly need conversational fact recall, those tools are solid choices. If your agents need to resume work, honor past decisions, and explain why they believe something, that is what Alice is built for.

## What Alice stores

- **Memories** — typed, revisioned facts with trust classification and provenance links to source evidence.
- **Decisions** — what was decided, when, and what superseded it.
- **Open loops** — blockers, waiting-fors, and follow-ups that agents can query, create, and close.
- **Resumption briefs** — "here is where work stopped, and what should happen next" for a project or thread.
- **Provenance and audit** — every memory can explain which sources, reviews, and corrections produced it.

Corrections are first-class: when a memory is corrected or superseded, future recall reflects the correction and the explanation chain shows why.

## Quickstart

Requirements: Python 3.12+, Node 20+, pnpm, Docker, Git.

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
make setup
make migrate
make doctor
make dev
```

- `make setup` creates `.env` files from checked-in examples and installs Python and web dependencies.
- `make migrate` starts local services (Postgres via Docker) and runs database migrations.
- `make doctor` runs readiness checks and applies safe fixes.
- `make dev` runs the API on port 8000 and the web review console on port 3000.

Open the review console at `http://localhost:3000/vnext`. The detailed walkthrough — demo data, smoke checks, first memory — is in [docs/alpha/quickstart.md](docs/alpha/quickstart.md).

> **Install note:** Alice currently runs from a repo checkout. The PyPI name [`alice-memory`](https://pypi.org/project/alice-memory/) is claimed with a placeholder release; the packaged runtime (including a zero-infrastructure SQLite mode) will ship under it. The name `alice-core` on PyPI belongs to an unrelated project.

## Connect an agent

### MCP

Point any MCP-capable agent or IDE at the Alice server:

```json
{
  "mcpServers": {
    "alice": {
      "command": "/ABSOLUTE/PATH/TO/AliceBot/.venv/bin/python",
      "args": ["-m", "alicebot_api.mcp_server"],
      "cwd": "/ABSOLUTE/PATH/TO/AliceBot",
      "env": {
        "DATABASE_URL": "postgresql://alicebot_app:alicebot_app@localhost:5432/alicebot",
        "ALICEBOT_AUTH_USER_ID": "00000000-0000-0000-0000-000000000001"
      }
    }
  }
}
```

The core MCP surface is nine tools:

- `alice_capture` — submit new information as source-backed, reviewable memory
- `alice_recall` — search memory (full-text plus vector, fused ranking)
- `alice_resume` — resumption brief for a project or thread
- `alice_context_pack` — scoped context bundle for a task
- `alice_open_loops` — list and manage open loops
- `alice_recent_decisions` — recent decision log
- `alice_memory_review` — inspect items pending review
- `alice_memory_correct` — propose a correction to an existing memory
- `alice_explain` — provenance and trust explanation for a memory

The legacy long-tail tool surface stays available behind `ALICE_MCP_LEGACY_TOOLS=1` for existing integrations.

Custom agents calling the HTTP API authenticate with per-agent API keys. See [docs/alpha/agent-integration.md](docs/alpha/agent-integration.md).

### Embeddings

Semantic search works with any OpenAI-compatible embeddings endpoint — Ollama, LM Studio, or OpenAI:

```bash
ALICE_EMBEDDINGS_BASE_URL=http://localhost:11434/v1
ALICE_EMBEDDINGS_MODEL=nomic-embed-text
ALICE_EMBEDDINGS_API_KEY=            # only if the endpoint requires one
```

Search fuses Postgres full-text results with pgvector (HNSW) similarity using reciprocal-rank fusion. If no embedding endpoint is configured, search degrades to full-text only and says so explicitly in the retrieval trace.

## Status

Alice is pre-1.0. What that means in practice:

- **Local-first, single-user.** One operator, one machine (or one headless server reached over SSH).
- **Review-governed writes.** Agents propose or commit through policy; outcomes are commit, confirm, review, or reject. The review console is the trust boundary for durable memory.
- **No hosted service.** There is no cloud offering yet; you run Alice yourself.
- **No OAuth connectors.** Capture paths are local files, explicit API/CLI/MCP calls, and agent output ingestion — not automatic syncing of external accounts.
- **No automatic capture from arbitrary conversation.** Durable memory comes from explicit commits, reviewable proposals, or captured sources, never from silent transcript mining.

## Docs

- [Quickstart walkthrough](docs/alpha/quickstart.md)
- [Agent integration](docs/alpha/agent-integration.md)
- [MCP tools](docs/alpha/mcp-tools.md)
- [Custom agent guide](docs/alpha/custom-agent-guide.md)
- [Known limitations](docs/alpha/known-limitations.md)
- [Security and privacy](docs/alpha/security-and-privacy.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Contributing

Issues, integrations, importers, and eval contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

If you discover a security issue, follow the process in [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
