# P14-S3 Control Tower Packet

## Sprint
`P14-S3` Model Packs

## Goal
Make common model families easy to use with sensible continuity defaults on top of the shipped Phase 14 provider/runtime surface.

## Planned Branch
`codex/phase14-s3-model-packs`

## In Scope
- model-pack schema and storage
- model-pack API
- workspace pack binding workflow
- first-party packs for Llama, Qwen, Gemma, and `gpt-oss`
- pack-aware invocation and briefing defaults
- compatibility matrix docs
- pack smoke tests

## Out Of Scope
- provider-contract redesign
- broad provider expansion unrelated to packs
- reopening local/self-hosted compatibility work already closed in `P14-S2`
- design-partner operations

## Acceptance Criteria
- a workspace can bind a provider to a pack
- pack defaults affect briefing and runtime behavior correctly
- first-party packs are versioned and documented
- users get good defaults without manual tuning
- pack behavior composes the shipped provider/runtime baseline instead of creating a second provider path
