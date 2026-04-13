<!--
SEO keywords: alice ai memory, ai agent memory, continuity layer, mcp memory server,
durable memory for agents, agent resumption, open loop tracking, local-first ai runtime
-->

# Alice

**The continuity layer for AI agents.**

![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![Python](https://img.shields.io/badge/python-3.12%2B-3776AB)
![Docker](https://img.shields.io/badge/docker-required-2496ED)
![License](https://img.shields.io/badge/license-MIT-2ea043)

Alice helps agents **remember what matters, resume interrupted work, explain why something is true, and improve when corrected**.

Most assistants are still good only in the moment. They can answer the current prompt, but they struggle to preserve decisions, track open loops, recover context across sessions, and stay aligned after memory corrections.

Alice fixes that.

It provides a **local-first memory and continuity engine** for capture, recall, resumption, open-loop tracking, and correction-aware, trust-aware memory, so you do not have to rebuild context from scratch every time work resumes.

**Bring your own models, keep one continuity layer.**

**Works across local, self-hosted, enterprise, and external-agent workflows via CLI, MCP, provider runtime, OpenClaw import, and Hermes integration.**

## Current phase

Phase 10 is complete and shipped.

Phase 11 is complete and shipped:

- `P11-S1` Provider Abstraction + OpenAI-Compatible Base is shipped
- `P11-S2` Ollama + llama.cpp Adapters is shipped
- `P11-S3` vLLM Adapter + Self-Hosted Performance Path is shipped
- `P11-S4` Model Packs Tier 1 is shipped
- `P11-S5` Azure Adapter + AutoGen Integration is shipped
- `P11-S6` Model Packs Tier 2 + Launch Clarity Assets is shipped
- `P11-R1` Provider Runtime Hardening is shipped
- A bridge phase is now active: Hermes Auto-Capture
- `B1` Hermes Provider Contract Foundation is shipped
- `B2` Auto-Capture Pipeline is shipped
- `B3` Review Queue + Explainability is shipped
- `B4` Packaging, Docs, and Smoke Validation is the active sprint
- Historical planning and control docs: [docs/archive/planning/2026-04-08-context-compaction/README.md](docs/archive/planning/2026-04-08-context-compaction/README.md)

## Why Alice exists

AI assistants still fail in the same places:

- important decisions disappear into old chats
- interrupted work is hard to resume
- blockers and waiting-fors get lost
- memory corrections do not reliably improve future behavior
- "memory" often means vague summaries with unclear provenance

Alice is built to solve those problems directly.

## What Alice gives you

Use Alice if you want your agents or workflows to:

- remember decisions, commitments, and context across sessions
- resume work without rereading long threads
- track waiting-fors, blockers, and unresolved follow-ups
- improve deterministically when memory is corrected
- stay portable across CLI, MCP, and imported workflow data

## Why Alice is different

### Built for continuity, not just storage

Alice does not treat memory as a pile of chat history or loose summaries.
It stores **typed continuity objects, revisions, provenance, and open loops** so context can be reused operationally.

### Built for resumption, not just retrieval

Most memory tools help you find something.
Alice is designed to answer the higher-value questions:

- What did we decide?
- What changed?
- What am I waiting on?
- What should happen next?

### Correction-aware by design

Alice supports explicit **review, correction, and supersession** so future answers improve in a traceable way instead of drifting based on hidden summarization.

### Trust-aware by default

Alice does not treat every memory as equally reliable.
Memories carry **trust classification** and **promotion eligibility**, so agents can search broadly without promoting weak, single-source AI-extracted facts into durable truth by default.

### Explainable, not opaque

Recall, resumption, open-loop review, and explain output all expose a shared explanation model with:

- source facts
- trust posture
- evidence segments
- supersession notes
- timestamps

That makes it easier to audit why an answer appeared, how it was derived, and how corrections changed the explanation chain over time.

### Local-first and agent-agnostic

Alice Core runs locally and exposes the same continuity semantics through the CLI and MCP, so you can use it with your own workflows instead of being locked into a closed assistant product.

### Swap providers, not behavior

Alice is now model-flexible.
You can switch or standardize model backends across local, self-hosted, enterprise, and external-agent environments without rewriting Alice's continuity, memory, approval, or provenance behavior.

## Use Alice with your existing agents

Alice is designed to be a **continuity layer**, not a closed assistant silo.

It already supports:

- **MCP-based integrations**
- **OpenClaw import and augmentation**
- **Hermes integration paths**
- **Hermes external memory provider**
- **Provider runtime abstraction for workspace-scoped model/provider integration**
- **Local, self-hosted, enterprise, and external-agent deployment paths**
- imported workflow data from Markdown and ChatGPT exports

That means you can use Alice as shared continuity infrastructure across providers and frameworks instead of rebuilding memory behavior per runtime.

## What ships today

The current open-source surface includes:

- Alice Core
- deterministic CLI workflows
- MCP server
- trust-aware memory classification and promotion controls
- shared explainability across recall, resume, open-loop review, and explain surfaces
- scheduled archive maintenance, ops status reporting, and failure alerting
- Hermes external memory provider for always-on continuity prefetch and Alice memory tools inside Hermes
- provider runtime abstraction with workspace-scoped provider registration, capability snapshots, OpenAI-compatible base adapter, local Ollama/llama.cpp, self-hosted vLLM, enterprise Azure, model packs, and external-agent integration paths
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

### First useful result in 5 minutes

In another terminal, verify the runtime and get a visible result:

```bash
./.venv/bin/python -m alicebot_api status
./.venv/bin/python -m alicebot_api recall --query local-first --limit 5
./.venv/bin/python -m alicebot_api resume --max-recent-changes 5 --max-open-loops 5
./.venv/bin/python -m alicebot_api open-loops --limit 5
```

Capture something new:

```bash
./.venv/bin/python -m alicebot_api capture "Remember that the Q3 board pack is due on Thursday."
```

Inspect why something is in memory:

```bash
./.venv/bin/python -m alicebot_api explain <continuity_object_id>
```

Run archive maintenance manually:

```bash
./scripts/run_archive_maintenance.py --schedule manual
```

Alice also includes a deterministic maintenance runner for archive integrity checks, stale fact surfacing, missing segment re-embedding, trusted-fact pattern candidate recompute, and optional benchmark regeneration.

See the full local setup walkthrough in [docs/quickstart/local-setup-and-first-result.md](docs/quickstart/local-setup-and-first-result.md).

## MCP surface

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

- [docs/integrations/hermes-bridge-operator-guide.md](docs/integrations/hermes-bridge-operator-guide.md)
- [docs/integrations/hermes-provider-plus-mcp-why.md](docs/integrations/hermes-provider-plus-mcp-why.md)
- [docs/integrations/mcp.md](docs/integrations/mcp.md)
- [docs/integrations/hermes.md](docs/integrations/hermes.md)
- [docs/integrations/hermes-memory-provider.md](docs/integrations/hermes-memory-provider.md)
- [docs/integrations/hermes-skill-pack.md](docs/integrations/hermes-skill-pack.md)
- [docs/integrations/phase11-local-provider-adapters.md](docs/integrations/phase11-local-provider-adapters.md)
- [docs/integrations/phase11-azure-autogen.md](docs/integrations/phase11-azure-autogen.md)

Recommended Hermes architecture is provider plus MCP, with MCP-only as a fallback.

One-command Hermes bridge demo:

```bash
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

Hermes runtime smoke tests:

```bash
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
```

If you use Hermes, run provider plus MCP as the recommended mode, add the skill pack for policy guidance, and keep MCP-only available as fallback.

## OpenClaw and imported workflows

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

## Why not just use ChatGPT memory?

ChatGPT memory is convenient.
Alice is structured, explainable, correctable, and portable across agent stacks, with explicit provenance, trust, resumption, and open-loop workflows.

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
