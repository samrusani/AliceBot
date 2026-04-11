<!--
SEO keywords: alice ai memory, ai agent memory, continuity layer, mcp memory server,
durable memory for agents, agent resumption, open loop tracking, local-first ai runtime
-->

# Alice

**Durable memory and resumption for AI agents.**

![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![License](https://img.shields.io/badge/license-MIT-2ea043)

AI assistants are good at replying in the moment. They are still weak at remembering what matters, resuming interrupted work, and staying aligned after corrections.

Alice is the continuity layer that fixes that.

It gives agents and workflows a local-first system for capture, recall, resumption, open-loop tracking, and correction-aware, trust-aware memory, so you do not have to rebuild context from scratch every time work resumes.

## Why use Alice

Use Alice if you want your agents or workflows to:

- remember decisions, commitments, and context across sessions
- resume work without rereading long threads
- track waiting-fors, blockers, and unresolved follow-ups
- improve deterministically when memory is corrected
- stay portable across CLI, MCP, and imported workflow data

## What makes Alice different

### It is built for continuity, not just storage

Alice does not treat memory as a pile of chat history or vague summaries.
It stores typed continuity objects, revisions, provenance, and open loops so context can be reused operationally.

### It is built for resumption, not just retrieval

Most memory tools help you find something.
Alice is designed to answer the higher-value questions:

- What did we decide?
- What changed?
- What am I waiting on?
- What should happen next?

### It is correction-aware

Alice supports explicit review, correction, and supersession so future answers improve in a traceable way instead of drifting based on hidden summarization.

### It is trust-aware

Alice does not treat every memory as equally reliable.
Memories carry trust classification and promotion eligibility, so agents can search broadly without promoting weak, single-source AI-extracted facts into durable truth by default.

Trust metadata flows through admission, retrieval, explain output, review behavior, and CLI/MCP responses, which makes memory quality visible instead of implicit.

### It makes retrieval explainable, not just accurate

Alice does not only return answers.
Recall, resumption, open-loop review, and explain output all expose a shared explanation model with source facts, trust posture, evidence segments, supersession notes, and timestamps.

That makes it easier to audit why an answer appeared, how it was derived, and how corrections changed the explanation chain over time.

### It is local-first and agent-agnostic

Alice Core runs locally and exposes the same continuity semantics through the CLI and MCP, so you can use it with your own workflows instead of being locked into a closed assistant product.

## Who Alice is for

Alice is useful for:

- agent builders
- technical teams
- founders and operators
- consultants and researchers
- anyone who needs reliable memory and clean resumption across days or weeks of work

## What ships today

The open-source surface includes:

- Alice Core
- deterministic CLI workflows
- MCP server
- trust-aware memory classification and promotion controls
- shared explainability across recall, resume, open-loop review, and explain surfaces
- scheduled archive maintenance, ops status reporting, and failure alerting
- Hermes external memory provider for always-on continuity prefetch and Alice memory tools inside Hermes
- importers for OpenClaw, Markdown, and ChatGPT exports
- OpenClaw adapter and demo path
- evaluation harness and integration docs

## Quickstart

Clone the repo and install the local runtime:

```bash
git clone https://github.com/samrusani/AliceBot.git
cd AliceBot
cp .env.example .env
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
```

Start the local services and seed sample data:

```bash
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
APP_RELOAD=false ./scripts/api_dev.sh
```

In another terminal, verify the runtime and get a first useful result:

```bash
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
./.venv/bin/python -m alicebot_api open-loops --limit 5
./scripts/run_archive_maintenance.py --schedule manual
```

Alice also includes a deterministic maintenance runner for archive integrity checks, stale fact surfacing, missing segment re-embedding, trusted-fact pattern candidate recompute, and optional benchmark regeneration.

Recall-derived surfaces now expose a shared explanation payload, and `explain` uses the same structure for continuity evidence:

```bash
./.venv/bin/python -m alicebot_api explain <continuity_object_id>
```

Capture something new:

```bash
./.venv/bin/python -m alicebot_api capture "Remember that the Q3 board pack is due on Thursday."
```

See the full local setup walkthrough in [docs/quickstart/local-setup-and-first-result.md](docs/quickstart/local-setup-and-first-result.md).

## Use Alice with your agents

Alice is designed to be a continuity layer, not a closed assistant silo.

### MCP

Alice exposes a narrow MCP surface for continuity workflows:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

This makes it straightforward to plug Alice into MCP-capable assistants and development environments without changing the underlying continuity model.

See:

- [docs/integrations/mcp.md](docs/integrations/mcp.md)
- [docs/integrations/hermes.md](docs/integrations/hermes.md)
- [docs/integrations/hermes-memory-provider.md](docs/integrations/hermes-memory-provider.md)
- [docs/integrations/hermes-skill-pack.md](docs/integrations/hermes-skill-pack.md)

Hermes runtime smoke test:

```bash
./scripts/run_hermes_mcp_smoke.py
```

If you use Hermes, Alice now supports three integration modes: MCP, skill pack, and a first-class external memory provider for turn prefetch plus recall, resumption, and open-loop tools.

### Import and augment existing workflows

Alice includes importer paths for existing memory and conversation data so you can upgrade an existing workflow instead of starting from zero.

With the current integration surface, you can:

- import OpenClaw memory into Alice
- normalize imported data into Alice continuity objects
- run recall and resumption against imported work
- add Alice MCP workflows on top of an existing setup

OpenClaw demo:

```bash
./scripts/use_alice_with_openclaw.sh
```

See:

- [docs/integrations/importers.md](docs/integrations/importers.md)
- [docs/integrations/openclaw.md](docs/integrations/openclaw.md)

## Example outcomes

### Founder and operator continuity

- keep strategic decisions from disappearing into old chats
- resume fundraising, hiring, or product threads quickly
- stay on top of commitments and follow-ups

### Consulting and client work

- preserve client-specific decisions and context
- restart project work without reconstructing the last week
- maintain open loops without building a manual CRM ritual

### Agent memory upgrades

- add durable continuity to an existing agent stack
- improve recall and resumption without rebuilding your runtime
- keep correction and provenance explicit

## Architecture at a glance

Alice is built around a shared continuity core with:

- structured memory revisions
- provenance- and trust-aware recall
- shared explanation chains across recall-derived workflows
- deterministic archive maintenance with ops-visible health summaries
- deterministic resumption briefs
- open-loop objects
- CLI and MCP surfaces on the same semantics

That means the system behaves consistently across local workflows, MCP-connected agents, and imported data sources.

## Roadmap

### Available now

- local-first core
- CLI
- MCP
- importers
- OpenClaw adapter
- reproducible eval harness

### In progress

- Alice Connect
- hosted identity and workspace bootstrap
- Telegram-first conversational surface
- chat-native approvals
- daily continuity briefs

## Docs

- [Quickstart](docs/quickstart/local-setup-and-first-result.md)
- [Architecture](ARCHITECTURE.md)
- [MCP](docs/integrations/mcp.md)
- [Hermes Guide](docs/integrations/hermes.md)
- [Hermes Memory Provider](docs/integrations/hermes-memory-provider.md)
- [Hermes Skill Pack](docs/integrations/hermes-skill-pack.md)
- [Importers](docs/integrations/importers.md)
- [OpenClaw Guide](docs/integrations/openclaw.md)
- [Examples](docs/examples/phase9-command-walkthrough.md)

## Contributing

Issues, adapters, importers, eval contributions, and integration examples are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

If you discover a security issue, follow the process in [SECURITY.md](SECURITY.md).

## License

See [LICENSE](LICENSE).
