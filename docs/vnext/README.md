# Alice vNext Public Preview

Alice vNext is the next public wedge for Alice as the continuity layer for AI agents: a local-first memory kernel, governed explicit agent memory commits, reviewable generated briefs, review-only memory consolidation, procedural memory, model-backed source-grounded synthesis, live local connector-backed evidence capture, hardened connector settings/state/secrets, agent-facing context packs and context trees, governed agent proposals, and a local scheduler runtime.

This preview is not a hosted launch. It is a repo-local, deterministic public preview built around the vNext memory-kernel schema and the fixture-safe workflows shipped under `v0.5.1-vnext-preview`.

## Product Shape

Alice vNext has three functional layers:

- **Memory kernel**: the local-first persistence, provenance, policy, and event-log substrate. It owns sources, chunks, memories, revisions, graph edges, projects, open loops, artifacts, evals, and connector evidence.
- **Synthesis workflows**: the reviewable workflows on top of the kernel. They generate daily briefs, weekly syntheses, context packs, memory consolidation artifacts, contradiction reports, connection reports, project updates, open-loop reviews, and reviewable artifacts in deterministic or model-backed mode.
- **Agent integration surface**: exposes continuity through CLI, API, and MCP so external agents can capture, retrieve, resume, explain, generate context, navigate read-only context trees, explicitly commit user-directed memory through policy, propose reviewable memory, and trigger governed scheduler workflows without owning the memory database.

## Preview Surfaces

- Source capture: manual text, local text/Markdown files, Markdown folders, ChatGPT exports.
- Retrieval: hybrid Postgres full-text + pgvector semantic search with reciprocal-rank fusion, domain/sensitivity filters, and provenance; without a configured embedding endpoint (`ALICE_EMBEDDINGS_BASE_URL`/`ALICE_EMBEDDINGS_MODEL`) it runs full-text-only and says so in traces.
- Synthesis workflows: daily brief, weekly synthesis, connection report, contradiction report, project update, open-loop review, review-only memory consolidation, and a review-first staleness sweep that marks expired or long-unconfirmed working-state memories `stale` without deleting anything.
- Procedural memory: typed end to end. Capture recognizes `Procedure:`/`Playbook:`/`How to` lines as `procedure` candidates (and `Happened:`/`Log:` lines as `episode`), retrieval accepts a `memory_type` filter so agents can recall procedures directly, and context packs include a procedures section. Procedures keep the same review, provenance, correction, supersession, and revision model as all other memory; there is no procedure-specific ranking or auto-classification beyond these typed rules.
- Model-backed intelligence: provider/routing abstraction, local-first model policy, source-grounded sections, prompt hashes, context hashes, model metadata, and deterministic-vs-model comparison mode.
- Quality review: artifact ratings for usefulness, accuracy, source grounding, novel connections, actionability, hallucination risk, verbosity, missed context, and comments.
- Agentic control plane: scoped agent identities, permission profiles, policy decisions, explicit trusted memory commits, inline confirmations, memory proposals, undo/correction/forget lifecycle controls, and Agent Activity audit surface.
- Governed scheduler: disabled-by-default workflow controls, a local daemon runner, due scans, run history, trace IDs, failures, duplicate-run locks, and reviewable artifacts.
- Connectors: allowlisted Telegram sync, local folder/Obsidian scan and watch, browser clipper capture endpoint, Hermes/OpenClaw-style agent output ingestion, dedicated settings/state rows, local encrypted secret references, retry/cursor hardening, plus deterministic PDF, DOCX, CSV, screenshot OCR, and voice transcript payload ingestion.
- UI: live/fixture-backed `/vnext` workspace for source review, source archive, capture-to-brief traces, Ask Alice, briefs, queue, projects, Agent Activity, trusted memory commit audit, inline confirmations, Schedules, beliefs, graph, live connector configuration, connector health/defaults/bookmarklet guidance, dogfooding readiness telemetry, doctor/readiness checks, privacy settings, model comparison, and quality ratings.
- Evals: one live suite, `retrieval_quality`, which runs the production hybrid retrieval pipeline against a synthetic corpus (live runs need `ALICEBOT_EVAL_DATABASE_URL`; otherwise the suite is reported as skipped). See [eval/README.md](../../eval/README.md) for what it measures.

## Start Here

1. Follow the [public preview quickstart](../alpha/quickstart.md) for the install path.
2. Use [first-run checklist](../alpha/first-run.md) and [doctor](../alpha/doctor.md) for onboarding.
3. Review [headless Ubuntu install](../alpha/headless-ubuntu-install.md), [Hermes dogfood on Ubuntu](../alpha/hermes-dogfood-ubuntu.md), [agent integration pack](../alpha/agent-integration.md), [MCP tools](../alpha/mcp-tools.md), [Hermes skill](../alpha/hermes-skill.md), and [OpenClaw skill](../alpha/openclaw-skill.md).
4. Follow [vNext quickstart](quickstart.md) for the broader preview path.
5. Review [architecture](architecture.md).
6. Review [security and privacy](security-privacy.md) and the [public-preview security posture](../alpha/security-and-privacy.md).
7. Review [local runtime](local-runtime.md) before running scheduler workflows in the background.
8. Use [example ALICE.md](ALICE.example.md) as the first Brain Charter.
9. Use [demo script](demo-video-script.md) and [demo mode](../alpha/demo-mode.md) for a short walkthrough.
10. Use [release checklist](../release/vnext-public-release-checklist.md) before publishing or tagging.
11. Review [preview release notes](../release/v0.5.1-vnext-preview-release-notes.md), [preview install notes](../alpha/release-notes.md), and [tag plan](../release/v0.5.1-vnext-preview-tag-plan.md).
12. Review the [dogfood daily checklist](../runbooks/vnext-dogfood-daily-checklist.md) before daily local preview use.
13. Historical build-process summaries are archived under [docs/archive/process/](../archive/process/README.md).

## Launch Boundary

The public preview should prove that a technical user can install Alice locally, capture live local evidence, configure local connector defaults safely, run readiness checks, and generate a first daily brief. It should not claim managed connector OAuth, packaged browser extensions, hosted connector polling, cloud sync, hosted SLA, or automatic promotion of generated artifacts into trusted memory.
