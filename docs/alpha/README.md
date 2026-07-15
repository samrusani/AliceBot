# Alice vNext Public Preview

This folder keeps the legacy `docs/alpha` path name, but the current release posture is Alice vNext public preview.

Alice vNext public preview is a technical, local-first package for people who want agent memory and continuity without hosted storage or direct database writes by agents. Alice is the continuity layer for AI agents.

Alice is agent-first, not dashboard-first:

1. Install Alice locally.
2. Connect an existing agent through MCP/API/CLI.
3. Let agents request scoped context packs, submit reviewable outputs, and commit only explicit user-directed memories through Alice policy.
4. Use `/vnext` to review, govern, audit, undo, correct, forget, configure, and troubleshoot.

Start here:

- [Quickstart](quickstart.md)
- [First-run checklist](first-run.md)
- [First memory guide](first-memory.md)
- [Local runtime](local-runtime.md)
- [Doctor](doctor.md)
- [Demo mode](demo-mode.md)
- [Headless Ubuntu install](headless-ubuntu-install.md)
- [Agent integration](agent-integration.md)
- [MCP tools](mcp-tools.md)
- [Hermes dogfood on Ubuntu](hermes-dogfood-ubuntu.md)
- [Hermes skill](hermes-skill.md)
- [OpenClaw skill](openclaw-skill.md)
- [Custom agent guide](custom-agent-guide.md)
- [Context-pack recipes](context-pack-recipes.md)
- [Memory proposal recipes](memory-proposal-recipes.md)
- [Agent output ingestion examples](agent-output-ingestion.md)
- [Dogfooding guide](dogfooding-guide.md)
- [Troubleshooting](troubleshooting.md)
- [Known limitations](known-limitations.md)
- [Security and privacy](security-and-privacy.md)
- [Alpha onboarding](onboarding.md)
- [Alpha release notes](release-notes.md)

Current alpha posture:

- local runtime, not hosted SaaS
- headless Ubuntu install path for SSH-only dogfood hosts
- technical setup, not consumer install
- reviewable source, artifact, and agent memory proposal flows
- explicit trusted-agent memory commits with confirmation/review/reject policy gates
- no direct Postgres writes by agents
- supported alpha connectors: local folder, browser clipper MVP, document text
  payloads, externally produced voice transcripts, externally extracted
  screenshot text, and agent output ingestion; Alice does not execute OCR or
  transcription
- `/vnext` is the operator console, not the main agent interface
