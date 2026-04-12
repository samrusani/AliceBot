# Phase 11 Setup Paths (P11-S6)

This guide provides operator-facing setup and verification paths for shipped Phase 11 surfaces across local, self-hosted, enterprise, and external-agent runtime use.

## Shared Prerequisites

1. Start API and data services.
2. Authenticate and obtain `SESSION_TOKEN`.
3. Have a workspace selected and a thread available for runtime invoke.
4. Verify catalog seeding:

```bash
curl -sS -X GET "http://127.0.0.1:8000/v1/model-packs" \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

Expected built-in packs include:

- `llama@1.0.0`
- `qwen@1.0.0`
- `gemma@1.0.0`
- `gpt-oss@1.0.0`
- `deepseek@1.0.0`
- `kimi@1.0.0`
- `mistral@1.0.0`

## Local Path: Ollama / llama.cpp

Register a local provider, test it, optionally bind a pack, then invoke runtime.

### Register Ollama

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/ollama/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Local Ollama",
    "base_url": "http://127.0.0.1:11434",
    "default_model": "qwen2.5:7b-instruct"
  }'
```

### Bind a Pack

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/model-packs/deepseek/bind" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pack_version":"1.0.0","metadata":{"reason":"local-default"}}'
```

### Test and Invoke

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/test" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"provider_id":"'"$PROVIDER_ID"'","prompt":"Confirm local runtime connectivity."}'
```

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id":"'"$PROVIDER_ID"'",
    "thread_id":"'"$THREAD_ID"'",
    "message":"Summarize local runtime status."
  }'
```

## Self-Hosted Path: OpenAI-Compatible (vLLM-Compatible Surface)

Register with `provider_key = openai_compatible`, then use the same test/invoke seams.

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_key":"openai_compatible",
    "display_name":"Self-Hosted vLLM",
    "base_url":"https://selfhosted.example/v1",
    "api_key":"'"$PROVIDER_API_KEY"'",
    "default_model":"mistral-small-instruct"
  }'
```

For explicit invoke override:

```json
{
  "pack_id": "mistral",
  "pack_version": "1.0.0"
}
```

## Enterprise Path: Azure

Register Azure through the shipped Azure endpoint, then use the shared test/invoke seams.

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/azure/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name":"Azure Enterprise",
    "base_url":"https://YOUR_RESOURCE.openai.azure.com",
    "auth_mode":"azure_api_key",
    "api_key":"'"$AZURE_API_KEY"'",
    "api_version":"2024-10-21",
    "default_model":"gpt-4.1-mini"
  }'
```

Azure uses the same pack seam (`pack_id`, `pack_version`) on `POST /v1/runtime/invoke`. If Azure-specific compatibility metadata is needed, create and bind a custom pack.

## External-Agent Path: AutoGen Bridge

Use the shipped bridge script to run AutoGen-style orchestration while keeping Alice runtime/provider/pack semantics intact.

```bash
./scripts/run_phase11_autogen_runtime_bridge.py \
  --session-token "$SESSION_TOKEN" \
  --provider-id "$PROVIDER_ID" \
  --thread-id "$THREAD_ID" \
  --user-message "Provide an execution-ready status update."
```

## Operator Verification Checklist

1. `GET /v1/model-packs` lists tier-1 and tier-2 built-in packs.
2. `POST /v1/model-packs/{pack_id}/bind` succeeds for selected pack/version.
3. `POST /v1/providers/test` succeeds for each configured provider path.
4. `POST /v1/runtime/invoke` metadata reports resolved `model_pack` and `source`.
5. Compatibility posture matches `docs/integrations/phase11-model-pack-compatibility.md`.
