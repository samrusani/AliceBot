# Product Brief

## Product Summary
Alice is a shipped continuity platform for AI agents and agent-assisted workflows. It provides typed memory, provenance, correction-aware recall, open-loop tracking, resumable context, and cross-surface continuity through CLI, MCP, provider runtime, and Hermes bridge paths.

The current control-tower objective is not a new feature phase. It is a pre-1.0 public release pass that packages the shipped platform into `v0.2.0`.

## Who It Is For
- Teams building or operating MCP-capable agents that need durable continuity instead of chat-only context.
- Developers who want model-agnostic memory infrastructure across local, self-hosted, enterprise, and external-agent runtimes.
- Hermes users who want always-on continuity prefetch, capture, review, and explainability without forking memory semantics.

## Problem
Most agent stacks still lose decisions, commitments, blockers, and corrections across sessions. When teams switch models, runtimes, or agent shells, continuity behavior often fragments as well.

## Why It Matters
- Preserves continuity semantics across providers and agent surfaces.
- Makes memory quality auditable through provenance, correction, and review flows.
- Reduces operator friction by supporting both explicit workflows and Hermes lifecycle automation.

## Shipped Baseline Truth
- Phase 9 shipped the local continuity core, CLI, MCP, importers, approvals, and evaluation harness.
- Phase 10 shipped the hosted/product layer.
- Phase 11 shipped provider runtime abstraction, adapters, and model packs across local, self-hosted, enterprise, and external-agent paths.
- Bridge `B1` through `B4` shipped Hermes provider lifecycle hooks, auto-capture, review queue, explainability, packaging docs, smoke validation, and demoable operator setup.

## Current Release Scope
- `R1` prepares `v0.2.0` as the next public tag for the shipped baseline above.
- Scope is limited to release docs, verification evidence, and repo-facing release clarity.

## Non-Goals
- No new runtime, provider, agent, or channel features in the release sprint.
- No widening into `v1.0.0` positioning or long-term compatibility guarantees.
- No reopening already shipped Phase 11 or bridge implementation work except where a release gate exposes a genuine defect.

## Success Criteria
- A technically literate external user can understand what Alice ships today from the repo docs alone.
- Public release docs match the actual shipped surface through Phase 11 + Bridge `B4`.
- `v0.2.0` can be tagged with evidence-backed confidence and without overstating maturity.
