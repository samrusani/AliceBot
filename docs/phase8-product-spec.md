# Phase 8 Product Spec

## Title

Phase 8: Operational Chief-of-Staff

## Executive Summary

Phase 7 proved that AliceBot can function as a trusted chief-of-staff agent for prioritization, follow-through, preparation, and weekly review.

The next product gap is operational closure.

AliceBot can now tell the user what matters, what is slipping, and what to prepare. It is not yet strong enough at turning those recommendations into execution-ready handoffs that can move safely through existing governed workflows.

Phase 8 should close that gap.

The phase objective is to make the chief-of-staff operational by transforming trusted recommendations into:

- structured handoff artifacts
- governed task and approval drafts
- visible handoff queues and outcomes
- closure signals that feed back into later prioritization

This is not an autonomy phase.
It is the execution-bridge phase.

## Product Thesis

Alice should move from:

- telling the user what matters

to:

- packaging the next move so it can actually get done safely

The chief-of-staff becomes truly useful when it not only identifies the right action, but prepares the action in a form that is reviewable, governable, and trackable.

## Why Phase 8 Exists

Phases 4 through 7 established:

- release trust
- continuity
- memory trust calibration
- chief-of-staff guidance

The largest remaining gap is:

- recommendation -> execution handoff

Without this bridge, Alice remains insightful but incomplete. The user still does too much operational reconstruction between deciding and doing.

## Phase Goal

Make chief-of-staff recommendations operationally usable through deterministic, approval-bounded action handoffs and follow-through closure.

## Non-Goals

- autonomous external side effects without approval
- public platform or SDK exposure
- channel expansion such as Telegram or WhatsApp
- broad connector write expansion as the main story
- orchestration redesign
- multi-agent abstraction as the primary deliverable

## Product Principles

1. Handoffs must be more useful than recommendations alone.
2. Every handoff must remain provenance-backed and trust-calibrated.
3. Side effects stay approval-bounded.
4. Outcome tracking matters as much as handoff generation.
5. Closure quality should improve later prioritization.

## Core Pillars

### 1. Action Handoff Artifacts

Chief-of-staff recommendations must be convertible into deterministic action artifacts such as:

- task handoff
- approval handoff
- follow-up handoff
- preparation handoff
- unblock plan

Each artifact should contain:

- title
- rationale
- provenance
- execution posture
- approval posture
- next recommended operator step

### 2. Handoff Queue

Alice needs a visible operational queue showing:

- ready for review
- waiting for approval
- handed off
- executed
- stale handoff
- expired or abandoned

This queue becomes the execution bridge between chief-of-staff reasoning and real workflow.

### 3. Governed Execution Preparation

Phase 8 should connect handoffs into existing governed flows without widening action scope prematurely.

Initial supported output posture:

- task draft
- approval draft
- draft-only follow-up package
- execution posture metadata

The system should prepare execution, not perform it autonomously.

### 4. Outcome Tracking

Alice must track what happened after a handoff:

- reviewed
- approved
- rejected
- rewritten
- executed
- ignored
- expired

Without this, the chief-of-staff cannot improve or accurately supervise follow-through.

### 5. Follow-Through Closure

The phase should close the loop from:

- recommendation
- to handoff
- to governed execution
- to outcome
- to updated future prioritization

## Core User Journeys

### 1. Recommendation To Handoff

Alice identifies a slipping commitment and creates a ready-to-review handoff artifact rather than leaving the user with only a suggestion.

### 2. Follow-Up Package

Alice prepares a follow-up package with:

- suggested draft
- rationale
- target context
- approval posture

The user can review and route it without rebuilding context manually.

### 3. Task Handoff

Alice converts a chief-of-staff recommendation into a structured task draft that can move into the existing task workflow.

### 4. Weekly Review To Closure

During weekly review, Alice not only surfaces problems but proposes closure-ready handoffs for the most important unresolved items.

### 5. Outcome Learning

Alice records whether a handoff was executed, ignored, rewritten, or stalled and uses that to improve future recommendation and handoff quality.

## Required Product Surfaces

### Chief-of-Staff Action Handoff Panel

A new panel in `/chief-of-staff` should show:

- action handoff brief
- handoff items
- execution posture
- approval posture
- provenance-backed rationale

### Handoff Queue

A queue or grouped view should show:

- ready
- pending approval
- executed
- stale
- expired

### Outcome Capture

Users must be able to record what happened to a handoff so later recommendations learn from actual execution outcomes.

## Action Handoff Artifacts

Primary Phase 8 artifacts:

- `action_handoff_brief`
- `handoff_item`
- `task_draft`
- `approval_draft`
- `execution_posture`
- `handoff_outcome_record`

These should be deterministic for fixed input state and should reuse Phase 7 chief-of-staff signals instead of replacing them.

## Trust And Policy Rules

The chief-of-staff handoff layer must inherit Phase 6 trust and Phase 4 governance rules.

### Trust Rules

- low-trust memory lowers handoff confidence
- stale or superseded truth must not be treated as current execution guidance
- provenance must be visible on every handoff

### Policy Rules

Allowed:

- draft
- package
- recommend
- route
- ask for approval

Not allowed by default:

- autonomous external sends
- hidden execution
- bypassing governed task/approval flows

## Success Metrics

Phase 8 should measure:

- handoff acceptance rate
- handoff execution rate
- stale handoff rate
- outcome capture rate
- recommendation-to-execution conversion rate
- follow-through closure rate
- user rewrite rate on handoff artifacts

## Delivery Constraints

- reuse shipped P5/P6/P7 contracts
- preserve Phase 4 qualification and release semantics
- keep action scope narrow and governed
- prefer deterministic operational artifacts over broader agent abstraction work

## Acceptance Criteria

- chief-of-staff recommendations can produce deterministic handoff artifacts
- handoff artifacts are provenance-backed and trust-calibrated
- handoffs map cleanly into existing task and approval workflows
- handoff status and outcomes are visible
- later prioritization can incorporate handoff outcomes

## Phase Exit Definition

Phase 8 is complete when Alice no longer stops at “what should happen.”

It must be able to:

- package the next move
- route it safely
- track what happened
- use that result to improve future guidance

At phase exit, Alice should feel less like a recommendation engine and more like an operational chief-of-staff.

## Recommended Next Phase After Success

If Phase 8 succeeds, then the infrastructure is in a much stronger position for:

- a reusable agent abstraction layer
- or a second first-party vertical agent

Before Phase 8 succeeds, platformization would still be ahead of product proof.
