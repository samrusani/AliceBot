# Product Brief

## Product Summary

Alice Connect is the Phase 10 product layer on top of shipped Phase 9 Alice Core. Alice Core remains the open-source local-first continuity engine; Alice Connect adds hosted identity, workspace bootstrap, Telegram-first access, chat-native continuity actions, and a daily brief loop for non-developer beta users.

## Problem

Phase 9 proved Alice can be installed, interoperate, remember, and resume deterministically. It does not yet make Alice usable every day for someone who will not touch a repo, CLI, or MCP setup.

## Target Users

- Non-developer beta users who want a personal continuity assistant in chat.
- Individual professionals who need capture, recall, resume, open-loop review, and lightweight approvals in Telegram.
- OSS adopters who start local-first and may later opt into a hosted product layer.

## Why It Matters

- turns continuity from a technical engine into a daily habit
- makes chat the default interface without forking core semantics
- creates a clear OSS-to-product path instead of a separate product rewrite

## Shipped Baseline

Phase 9 is complete and shipped. Baseline truth is:

- Alice Core local-first runtime
- deterministic CLI continuity commands
- deterministic MCP transport with a narrow tool surface
- OpenClaw, Markdown, and ChatGPT importers
- continuity engine, approvals, and evaluation harness
- public quickstart, integration, release, and runbook docs for the OSS wedge

## V1 Scope (Phase 10)

### Open Source Surface

- Alice Core
- CLI
- MCP
- importers
- OpenClaw adapter

### Product / Beta Surface

- Alice Connect account
- hosted workspace bootstrap
- device and channel linking
- Telegram access
- chat-native capture, recall, resume, correction, and open-loop review
- approvals in chat
- daily brief and notification loop
- opt-in encrypted backup/sync metadata path
- beta onboarding, cohort gating, and support tooling

## Non-Goals

- WhatsApp or broad channel expansion
- browser automation
- high-risk autonomous execution
- enterprise collaboration features
- new vertical agents
- reopening more core release-control work as Phase 10 scope

## Success Criteria

At the end of Phase 10, a non-developer beta user can:

- create an account
- link Telegram
- import initial data or skip import
- capture things naturally in chat
- ask recall questions
- get resume briefs
- review open loops
- approve simple actions in chat
- receive a useful daily brief

## Product Non-Negotiables

- Alice Core remains the baseline truth; Phase 10 builds on it rather than replacing it.
- Telegram is a product surface on top of the same continuity semantics as local, CLI, and MCP.
- Durable answers remain provenance-backed and correction-aware.
- Consequential actions remain approval-bounded.
- Hosted product docs must clearly distinguish OSS surface from beta product surface.

## Historical Traceability

Superseded planning and control material is retained in local-only internal archives and is not part of the public repo.
