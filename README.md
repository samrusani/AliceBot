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

### It is temporal, not just current-state

Alice does not just tell you what it believes now.
It can reconstruct entity state at a specific point in time, show a chronological timeline of changes, and explain historical truth with trust, provenance, and supersession chains.

That makes it useful for questions like:

- What was true about this entity last week?
- When did this change?
- Why is this the effective fact as of this timestamp?

### It is identity-aware, not just text-matched

Alice does not rely only on raw text labels for people, projects, and topics.
It resolves aliases to canonical entities, keeps merge history explicit, and prefers FK-backed entity bindings in recall and resumption so continuity stays stable even when names vary over time.

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
- temporal state, timelines, and explain surfaces across HTTP, CLI, and MCP
- canonical entity identity with alias resolution, merge audit, and FK-backed continuity bindings
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
```

Inspect temporal state and history:

```bash
./.venv/bin/python -m alicebot_api state-at <entity_id> --at 2026-03-12T09:45:00+00:00
./.venv/bin/python -m alicebot_api timeline <entity_id> --limit 20
./.venv/bin/python -m alicebot_api explain --entity-id <entity_id> --at 2026-03-12T09:45:00+00:00
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
- `alice_state_at`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_timeline`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_explain`
- `alice_context_pack`

This makes it straightforward to plug Alice into MCP-capable assistants and development environments without changing the underlying continuity model.

`alice_explain` supports either continuity-object evidence inspection or temporal entity explain output.

See:

- [docs/integrations/mcp.md](docs/integrations/mcp.md)
- [docs/integrations/hermes.md](docs/integrations/hermes.md)
- [docs/integrations/hermes-skill-pack.md](docs/integrations/hermes-skill-pack.md)

Hermes runtime smoke test:

```bash
./scripts/run_hermes_mcp_smoke.py
```

### Import and augment existing workflows

Alice includes importer paths for existing memory and conversation data so you can upgrade an existing workflow instead of starting from zero.
Imported records preserve source text while binding to canonical entities when aliases resolve, which keeps imported continuity usable across recall and resumption.

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
- temporal state reconstruction over memory revisions and effective edges
- canonical entity bindings with alias-aware recall and resumption
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
