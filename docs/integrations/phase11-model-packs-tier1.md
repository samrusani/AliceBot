# Phase 11 Model Packs Tier 1 (P11-S4)

This guide documents the declarative tier-1 model-pack layer introduced in `P11-S4`.

## In-Scope APIs

- `GET /v1/model-packs`
- `GET /v1/model-packs/{pack_id}`
- `POST /v1/model-packs`
- `POST /v1/model-packs/{pack_id}/bind`
- `GET /v1/workspaces/{workspace_id}/model-pack-binding`
- `POST /v1/runtime/invoke` (pack-aware shaping)

## Tier-1 Packs

The tier-1 pack catalog is seeded per workspace and includes:

- `llama@1.0.0`
- `qwen@1.0.0`
- `gemma@1.0.0`
- `gpt-oss@1.0.0`

Each tier-1 pack uses `contract_version = model_pack_contract_v1` and keeps behavior declarative in:

- `context` (limit caps)
- `tools` (mode)
- `response` (instruction overlays)
- `compatibility` (provider/runtime compatibility references)

## Runtime Selection Precedence

For `POST /v1/runtime/invoke`, model-pack selection precedence is:

1. request override (`pack_id` + optional `pack_version`)
2. provider-specific workspace binding
3. workspace default binding
4. no pack

This precedence affects runtime shaping only. It does not change provider adapter semantics.

## Pack-Driven Runtime Shaping

Pack contracts can declaratively shape:

- context compiler caps (`max_sessions`, `max_events`, `max_memories`, `max_entities`, `max_entity_edges`)
- instruction overlays appended to system/developer instructions
- tool mode contract (`none` in this sprint)

Shaping is applied on the existing invoke seam (`/v1/runtime/invoke`) and does not create a parallel runtime path.

## Bind A Tier-1 Pack

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/model-packs/gpt-oss/bind" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'$PROVIDER_ID'",
    "pack_version": "1.0.0",
    "metadata": {"reason": "provider-default"}
  }'
```

Omit `provider_id` to set the workspace default pack used for briefing defaults.

## Invoke With Bound Pack

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'$PROVIDER_ID'",
    "thread_id": "'$THREAD_ID'",
    "message": "Summarize current open loops.",
    "max_sessions": 10,
    "max_events": 40,
    "max_memories": 40,
    "max_entities": 40,
    "max_entity_edges": 80
  }'
```

The response metadata reports the resolved pack and source when a pack is applied.

## Read The Current Binding

```bash
curl -sS -X GET "http://127.0.0.1:8000/v1/workspaces/$WORKSPACE_ID/model-pack-binding?provider_id=$PROVIDER_ID" \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

## Create A Custom Pack

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/model-packs" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pack_id": "custom-brief",
    "pack_version": "1.0.0",
    "display_name": "Custom Brief",
    "family": "custom",
    "description": "Workspace custom pack for concise operational briefs.",
    "contract": {
      "contract_version": "model_pack_contract_v1",
      "context": {
        "max_sessions_cap": 3,
        "max_events_cap": 8,
        "max_memories_cap": 5,
        "max_entities_cap": 5,
        "max_entity_edges_cap": 10
      },
      "tools": {"mode": "none"},
      "response": {
        "system_instruction_append": "Keep responses concise and grounded.",
        "developer_instruction_append": "Prioritize explicit next actions."
      },
      "compatibility": {
        "provider_keys": ["openai_compatible", "ollama", "llamacpp", "vllm"],
        "runtime_providers": ["openai_responses"],
        "notes": "Custom workspace brief style."
      }
    },
    "metadata": {
      "owner": "workspace-ops"
    }
  }'
```

## Compatibility References

See `docs/integrations/phase11-model-pack-compatibility.md`.
