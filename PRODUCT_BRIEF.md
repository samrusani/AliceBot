# Product Brief

## Product Summary

AliceBot is a private, permissioned personal AI operating system for a single primary user. It is designed to preserve durable personal context, retrieve the right context at the right time, and move safely from conversation to action without hiding why it acted.

## Problem

General-purpose assistants forget preferences, prior decisions, and relationships across sessions. They also make it difficult to audit why they answered a certain way or whether a tool action was properly governed. The result is low trust, repeated user effort, and unsafe action handling.

## Target Users

- Primary v1 user: one power user with recurring life and work workflows.
- Delivery model: a human lead working with AI builders and reviewers.
- Architectural assumption: v1 UX is single-user, but the data model must support strict per-user isolation from day one.

## Core Value Proposition

- Durable memory for preferences, relationships, prior decisions, and recurring tasks.
- Deterministic context compilation instead of ad hoc prompt stuffing.
- Safe action orchestration with policy checks, approvals, and budgets.
- Clear explainability through traces, memory evidence, and tool history.

## V1 Scope

- Web-based chat and task orchestration.
- Immutable thread and session continuity.
- Structured memory with admission controls, revision history, and user review.
- Entity and relationship tracking for people, merchants, products, projects, and routines.
- Hybrid retrieval across memories, entities, relationships, and documents.
- Policy engine, tool proxy, approval workflows, and task budgets.
- Scoped task workspaces and artifact storage.
- Read-only document ingestion plus read-only Gmail and Calendar connectors.
- Hot consolidation for immediate truth updates and cold consolidation for cleanup and summarization.
- Explain-why views for important responses and actions.

## Non-Goals

- Autonomous side effects without user approval.
- Multi-user collaboration UX in v1.
- Mobile-first delivery.
- Dedicated graph or vector infrastructure in v1.
- Browser automation, write-capable connectors, proactive automations, and voice at launch.

## Key User Journeys

1. Ask a question that depends on prior preferences, purchases, or relationships and get a context-aware answer without restating history.
2. Correct a preference or fact and have the next turn reflect the new truth immediately.
3. Inspect why the system answered or proposed an action by reviewing memories, retrieval choices, and tool traces.
4. Run a repeat-purchase workflow that gathers prior context, proposes the order, pauses for approval, and records the outcome.
5. Retrieve relevant context from documents, Gmail, or Calendar without granting write access.

## Constraints

- Single-user product experience, multi-tenant-safe architecture.
- Web-first v1.
- Explicit approval for consequential actions.
- Operational simplicity beats platform sprawl in v1.
- Memory quality, retrieval quality, and explainability are ship-gating concerns.

## Success Criteria

- The system recalls relevant preferences, past purchases, relationships, and prior decisions without repeated user restatement.
- The repeat magnesium reorder workflow succeeds end to end with approval gating and memory write-back.
- Every consequential action is explainable through trace, memory, rule, and tool evidence.
- Purchases, emails, bookings, and other side effects never occur without explicit approval.
- Standard retrieval-plus-response interactions reach p95 latency under 5 seconds.
- Prompt and cache reuse exceeds 70% on repeated patterns.
- Memory extraction precision exceeds 80% at ship.

## Product Non-Negotiables

- The user stays in control of consequential actions.
- Durable context must come from governed storage, not raw transcript stuffing.
- Explainability is a product requirement, not a debugging feature.
- Preference contradictions must be reflected immediately.
- The repeat magnesium reorder scenario is the canonical v1 ship gate.
