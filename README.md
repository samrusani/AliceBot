<!--
SEO keywords: alice ai memory, ai agent memory, continuity layer, mcp memory server,
durable memory for agents, agent resumption, open loop tracking, local-first ai runtime
-->

# Alice

**The memory and continuity layer for AI agents.**

![Local-first](https://img.shields.io/badge/local--first-core-0A7B61)
![MCP](https://img.shields.io/badge/MCP-supported-1f6feb)
![License](https://img.shields.io/badge/license-MIT-2ea043)

Alice gives agents something most assistants still lack:
**durable memory, clean resumption, open-loop continuity, and correction-aware context.**

Instead of forcing you to restate context over and over, Alice helps your tools and agents remember what matters, resume work intelligently, and improve when corrected.

## What Alice does

Alice helps agents and users:

- **Capture** important notes, decisions, and commitments quickly
- **Recall** what was decided about a person, project, or topic
- **Resume** work without rereading long threads
- **Track open loops** like waiting-fors, blockers, and stale items
- **Correct memory** so future answers improve deterministically

## Why Alice exists

Most AI assistants still break in the same places:

- they forget why decisions were made
- they lose context between sessions
- they treat memory as vague summaries
- they make correction hard
- they do not help you resume interrupted work

Alice is built to solve that.

It is a **local-first continuity engine** with:

- structured memory revisions
- deterministic recall and resumption
- provenance-aware corrections
- open-loop management
- MCP access for external agents
- importers for existing workflows

## Who it is for

Alice is built for:

- founders
- operators
- consultants
- researchers
- technical teams
- agent builders
- anyone who wants their AI systems to remember and resume work properly

## What makes Alice different

### Memory that can be corrected

Alice does not just store chats.
It keeps explicit continuity objects and supports review, correction, and supersession.

### Resumption, not just search

Alice is designed to answer:

- What did we decide?
- What changed?
- What am I waiting on?
- Get me back into this project.

### Agent-agnostic by design

Use Alice on its own, through the CLI, through MCP, or alongside external agent systems.

### Local-first core

Alice Core runs locally and keeps continuity close to the user.

## Current surfaces

Today, Alice ships with:

- **Alice Core**
- **CLI**
- **MCP server**
- **OpenClaw adapter**
- **Importers**
  - OpenClaw
  - Markdown
  - ChatGPT exports

## Quickstart

> Replace these commands with your exact final install path before launch.

```bash
git clone https://github.com/your-org/alice.git
cd alice
cp .env.example .env
docker compose up -d
```

Check status:

```bash
alice status
```

Capture something:

```bash
alice capture "Remember that the Q3 board pack is due on Thursday."
```

Recall it later:

```bash
alice recall "What do I know about the Q3 board pack?"
```

Resume work:

```bash
alice resume q3-board-pack
```

Review open loops:

```bash
alice open-loops
```

Correct memory:

```bash
alice correct-memory
```

## Use Alice with your agents

Alice is designed to be a continuity layer, not a closed assistant silo.

### MCP

Alice exposes a narrow, stable MCP surface for continuity workflows:

- `alice_capture`
- `alice_recall`
- `alice_resume`
- `alice_open_loops`
- `alice_recent_decisions`
- `alice_recent_changes`
- `alice_memory_review`
- `alice_memory_correct`
- `alice_context_pack`

This makes it easy to connect Alice to MCP-capable assistants and development environments.

See:

- [docs/integrations/mcp.md](docs/integrations/mcp.md)

### OpenClaw

Alice includes an OpenClaw integration path for import and augmentation.

You can:

- import existing OpenClaw memory into Alice
- normalize it into Alice continuity objects
- use Alice recall and resumption on imported work
- augment OpenClaw workflows through Alice MCP tools

See:

- [docs/integrations/importers.md](docs/integrations/importers.md)

## Example workflows

### Founder continuity

- capture strategic decisions
- resume fundraising or product threads
- track waiting-fors and follow-ups
- stop losing context across days and weeks

### Consulting continuity

- recall client decisions
- resume project threads fast
- maintain open loops without building a manual CRM ritual

### Agent memory upgrade

- plug Alice into your existing agent stack
- improve recall, resumption, and correction
- avoid rebuilding your whole runtime

## Architecture at a glance

Alice is built around a shared continuity core:

- immutable events
- structured memory revisions
- provenance-aware recall
- deterministic resumption briefs
- open-loop objects
- MCP and CLI surfaces on the same semantics

This means Alice behaves consistently whether you use:

- CLI
- MCP
- imported data
- external adapters

## Why people share Alice

Because Alice solves a very real problem:
your AI can only be useful if it can remember, resume, and stay aligned with how you actually work.

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
- [Integrations](docs/integrations/importers.md)
- [Examples](docs/examples/phase9-command-walkthrough.md)

## Tags

`ai-memory` `agent-memory` `durable-memory` `continuity-layer` `mcp` `local-first` `resumption` `open-loops` `ai-agents` `memory-correction`

## GitHub Topics To Set

Use these in GitHub repository settings (`About` -> `Edit` -> `Topics`):

- [ ] `ai-memory`
- [ ] `agent-memory`
- [ ] `mcp`
- [ ] `local-first`
- [ ] `continuity-layer`
- [ ] `durable-memory`
- [ ] `context-engineering`
- [ ] `developer-tools`
- [ ] `openclaw`
- [ ] `memory-correction`

## Contributing

We welcome issues, adapters, importers, eval contributions, and integration examples.

See:

- [CONTRIBUTING.md](CONTRIBUTING.md)

## Security

If you discover a security issue, please report it through the process in:

- [SECURITY.md](SECURITY.md)

## License

See:

- [LICENSE](LICENSE)
