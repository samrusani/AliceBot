# Phase 14 Model Pack Contract

## Purpose
Model packs provide declarative continuity defaults on top of the shipped provider/runtime baseline.

They shape briefing and runtime behavior without creating a second provider path or changing Alice continuity semantics.

## Shipped First-Party Packs
- `llama@1.0.0`
- `qwen@1.0.0`
- `gemma@1.0.0`
- `gpt-oss@1.0.0`

DeepSeek, Mistral, and other families remain deferred from the first-party catalog in `P14-S3`.

## Persisted Model-Pack Fields
- `pack_id`
- `pack_version`
- `display_name`
- `family`
- `description`
- `status`
- `briefing_strategy`
- `briefing_max_tokens`
- `contract`
- `metadata`

## Contract Shape
`contract.contract_version` must equal `model_pack_contract_v1`.

### `context`
- `max_sessions_cap`
- `max_events_cap`
- `max_memories_cap`
- `max_entities_cap`
- `max_entity_edges_cap`

### `tools`
- `mode`

`P14-S3` ships only `tools.mode = "none"`.

### `response`
- `system_instruction_append`
- `developer_instruction_append`

### `compatibility`
- `provider_keys`
- `runtime_providers`
- `notes`

## Binding Rules
- a workspace may bind a default pack with no provider id
- a workspace may bind a specific provider to a pack by `provider_id`
- runtime selection precedence is:
  1. explicit request override
  2. provider-specific binding
  3. workspace default binding
  4. no pack
- task-briefing defaults resolve from the workspace default binding when no explicit pack is requested
- pack compatibility must remain declarative through `compatibility.provider_keys` and `compatibility.runtime_providers`

## Success Condition
Users can bind a supported provider or workspace default to a documented first-party pack and get sensible continuity defaults without manual tuning or hidden runtime behavior changes.
