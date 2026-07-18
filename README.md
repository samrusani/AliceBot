# Alice

<!-- mcp-name: io.github.samrusani/alice-memory -->

**The continuity layer for AI agents.**

[![LongMemEval](https://img.shields.io/badge/LongMemEval__s-79.4%25-6f42c1)](https://github.com/samrusani/AliceBot/blob/main/docs/benchmarks/longmemeval/README.md)
![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-2ea043)

Alice is a local-first memory service that lets AI agents resume interrupted work, track open loops, recall decisions with provenance, and improve when corrected — instead of re-reading transcripts or trusting opaque summaries.

In one historical run dated 2026-07-07, it scored **79.4%** on [LongMemEval](https://github.com/samrusani/AliceBot/blob/main/docs/benchmarks/longmemeval/README.md), a long-term-memory benchmark. That is a single-run receipt, not a repeated-run estimate or a measurement of the current release; it includes one disclosed trade-off on the abstention subset (25/30 → 22/30). The full per-question evidence, methodology, and reproduction script are committed to this repo. Open source, local-first, MIT-licensed.

Agents connect over MCP, HTTP API, or CLI. Humans stay in control: agent writes land as policy-checked commits or reviewable proposals, and a local review console is where memory gets approved, corrected, or forgotten. That review boundary is a feature, not a limitation — it is what makes the memory trustworthy enough to act on.

## How Alice compares

Most agent memory tools — mem0, Zep, Letta, and similar — focus on extracting facts from conversations and retrieving them later. That solves recall, and they do it well. Alice focuses on continuity: it stores typed continuity objects (decisions, open loops, resumption briefs) alongside plain memories; source-backed answers trace to the evidence that was supplied; and writes are review-governed, so an agent cannot silently promote a bad extraction into durable truth. Explicit commits may legitimately have no source reference. If you mainly need conversational fact recall, those tools are solid choices. If your agents need to resume work, honor past decisions, and explain why they believe something, that is what Alice is built for.

Alice is a layer, not a lock-in: it runs happily alongside other memory tools, and plenty of stacks will want both — a fact-extraction memory for conversational recall and Alice for governed continuity.

## What Alice stores

- **Memories** — typed, revisioned facts with trust classification and, when
  evidence was supplied, provenance links to that source evidence.
- **Decisions** — what was decided, when, and what superseded it.
- **Open loops** — blockers, waiting-fors, and follow-ups that agents can query, create, and close.
- **Resumption briefs** — "here is where work stopped, and what should happen next" for a project or thread.
- **Provenance and audit** — source-backed memories identify their supplied
  sources; reviews and corrections preserve their audit chain. Explicit
  commits may legitimately have no source reference.

Corrections are first-class: when a memory is corrected or superseded, future recall reflects the correction and the explanation chain shows why.

## Quickstart

The fastest path is the packaged runtime from PyPI — Python 3.12+ and nothing else, no Docker, Node, or Postgres. It serves the eleven core MCP tools against a single local SQLite file:

```bash
uvx alice-memory mcp --data-dir ~/.alice
# or: pip install alice-memory && alice-memory mcp --data-dir ~/.alice
```

MCP client config (Claude Desktop, IDEs) — note there is no `DATABASE_URL`:

```json
{
  "mcpServers": {
    "alice": {
      "command": "uvx",
      "args": ["alice-memory", "mcp", "--data-dir", "/ABSOLUTE/PATH/TO/.alice"]
    }
  }
}
```

SQLite mode is the trial and single-agent path: it serves the eleven core tools for one user, and memory review happens through `alice_memory_review` / `alice_memory_correct` instead of the web console. Boundaries are listed in [known limitations](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/known-limitations.md).

> **Install note:** the PyPI package is [`alice-memory`](https://pypi.org/project/alice-memory/). The name `alice-core` on PyPI belongs to an unrelated project.

### Full stack (Postgres + review console)

For the full experience — Postgres/pgvector, the web review console, and core
memory scheduler workflows — run from a repo checkout. Requirements: Python
3.12+, Node 20+, pnpm, Docker, Git.

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

Open the review console at `http://localhost:3000/vnext`. The detailed walkthrough — demo data, smoke checks, first memory — is in [the alpha quickstart](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/quickstart.md).

## Connect an agent

### MCP

Point any MCP-capable agent or IDE at the Alice server. For the packaged SQLite runtime, use the `uvx` config from the Quickstart above. For the full Postgres stack from a checkout:

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

The core MCP surface is eleven tools:

- `alice_capture` — submit new information as source-backed, reviewable memory
- `alice_memory_commit` — write an explicit "remember this" memory through policy: committed, confirmation-required, review-required, or rejected
- `alice_recall` — search memory (full-text plus vector, fused ranking; hard-scopable by thread, task, project, person, time, and memory type)
- `alice_resume` — resumption brief for a project or thread
- `alice_context_pack` — project/person/time-scoped context for a task, with a bounded unique-content budget and a complete serialized-size estimate
- `alice_open_loops` — list and manage open loops
- `alice_recent_decisions` — recent decision log
- `alice_memory_review` — inspect items pending review
- `alice_memory_correct` — propose a correction to an existing memory
- `alice_memory_manage` — confirm, undo, or forget a committed memory, audit trail intact
- `alice_explain` — provenance and trust explanation for a memory

Calling directly from a human client (Claude Desktop, an IDE)? `alice_memory_commit` needs only `title` and `canonical_text` — no identity fields. Agent integrations declare `agent_id` and `agent_type`; see [agent integration](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/agent-integration.md).

The write verbs follow one contract — outcomes, audit guarantees, and honest boundaries per verb are documented in the [Memory Operations Protocol](https://github.com/samrusani/AliceBot/blob/main/docs/memory-operations-protocol.md). Removed backing services no longer have MCP tools. Retained long-tail memory tools require `ALICE_MCP_LEGACY_TOOLS=1`; exactly `alice_task_brief`, `alice_task_brief_show`, and `alice_task_brief_compare` additionally require `ALICE_LEGACY_SURFACES=1`. All legacy tools require a deliberately keyless local-operator deployment; a server bound with `ALICE_AGENT_API_KEY` exposes only the policy-complete core surface.

Custom agents calling the HTTP API authenticate with per-agent API keys. See [agent integration](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/agent-integration.md).

### Embeddings

Semantic search works with any OpenAI-compatible embeddings endpoint — Ollama, LM Studio, or OpenAI:

```bash
ALICE_EMBEDDINGS_BASE_URL=http://localhost:11434/v1
ALICE_EMBEDDINGS_MODEL=nomic-embed-text
ALICE_EMBEDDINGS_API_KEY=            # only if the endpoint requires one
```

Search fuses Postgres full-text results with pgvector 0.8+ (iterative HNSW)
similarity using reciprocal-rank fusion. If no embedding endpoint is configured,
search degrades to full-text only and says so explicitly in the retrieval trace.

## Status

`v0.11.1` is the latest published release; the `v0.12.0` candidate (structural
refactor, zero behavior change) is in release gating. Its
tag, release record, and published artifacts remain immutable.

`v0.11.1` is the latest published release and remains the install, checksum,
and release-note baseline.
The uncommitted Phase 3 carrier targets `v0.12.0` with **Structure only. Zero
behavior change.** It splits oversized HTTP, store, contract, MCP, and CLI
modules behind stable imports and entrypoints. Both governed version sources
remain `0.11.1` until the release engineer verifies and cuts the release; the
pending v0.12.0 notes do not authorize tagging or publication.
The published `v0.11.0` runtime narrows the default product to the agent
interface and retrieval/memory core.
Alice is a public-alpha, pre-1.0 project.
What that means in practice:

- **Local-first, single-user.** One operator, one machine (or one headless server reached over SSH).
- **Review-governed writes.** Agents propose or commit through policy; outcomes are commit, confirm, review, or reject. The review console is the trust boundary for durable memory.
- **No hosted service.** There is no cloud offering yet; you run Alice yourself.
- **No channels or bundled chat runtime.** Telegram, hosted administration,
  chief-of-staff/chat/model-pack features, and the public `/v0/responses` chat
  endpoint are not part of the current product. Retained `/v1/runtime/invoke`
  still uses internal durable response-job/provider machinery.
- **No managed OAuth or automatic polling.** Temporary manual-token Gmail and
  Calendar compatibility is unmounted by default behind
  `ALICE_LEGACY_SURFACES=1`; Alice does not provide managed consent or syncing.
- **No automatic capture from arbitrary conversation.** Durable memory comes from explicit commits, reviewable proposals, or captured sources, never from silent transcript mining.
- **No OCR or transcription execution.** Alice accepts text extracted by an
  external tool; it does not run OCR or transcription models.

## Docs

- [Quickstart walkthrough](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/quickstart.md)
- [Agent integration](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/agent-integration.md)
- [MCP tools](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/mcp-tools.md)
- [Custom agent guide](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/custom-agent-guide.md)
- [Known limitations](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/known-limitations.md)
- [Backup and restore](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/backup-and-restore.md)
- [Security and privacy](https://github.com/samrusani/AliceBot/blob/main/docs/alpha/security-and-privacy.md)
- [v0.10.4 release notes](https://github.com/samrusani/AliceBot/blob/main/docs/release/v0.10.4-release-notes.md)
- [v0.11.0 release notes](https://github.com/samrusani/AliceBot/blob/main/docs/release/v0.11.0-release-notes.md)
- [v0.11.1 release notes](https://github.com/samrusani/AliceBot/blob/main/docs/release/v0.11.1-release-notes.md)
- [pending v0.12.0 release notes](https://github.com/samrusani/AliceBot/blob/main/docs/release/v0.12.0-release-notes.md)
- [Release procedure](https://github.com/samrusani/AliceBot/blob/main/RELEASING.md)
- [Architecture](https://github.com/samrusani/AliceBot/blob/main/ARCHITECTURE.md)
- [Roadmap](https://github.com/samrusani/AliceBot/blob/main/ROADMAP.md)
- [Changelog](https://github.com/samrusani/AliceBot/blob/main/CHANGELOG.md)

## Contributing

Issues, integrations, importers, and eval contributions are welcome. See [CONTRIBUTING.md](https://github.com/samrusani/AliceBot/blob/main/CONTRIBUTING.md).

## Security

If you discover a security issue, follow the process in [SECURITY.md](https://github.com/samrusani/AliceBot/blob/main/SECURITY.md).

## License

MIT — see [LICENSE](https://github.com/samrusani/AliceBot/blob/main/LICENSE).
