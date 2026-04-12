# Phase 11 Azure + AutoGen Integration (P11-S5)

This guide covers the sprint-owned enterprise provider and framework path:

- `POST /v1/providers/azure/register`
- `POST /v1/providers/test`
- `POST /v1/runtime/invoke`
- `GET /v1/providers`
- `GET /v1/providers/{provider_id}`

Scope note: this page documents Azure provider registration/runtime plus an AutoGen-oriented runtime bridge path.

## Prerequisites

1. Start Alice API and data services.
2. Authenticate and obtain a hosted session bearer token.
3. Have a thread ID available for runtime invoke.
4. Have an Azure OpenAI or Azure Foundry endpoint that supports OpenAI-compatible `/openai/models` and `/openai/responses` paths.

## Register Azure With API Key Auth

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/azure/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Azure Primary",
    "base_url": "https://YOUR_RESOURCE.openai.azure.com",
    "auth_mode": "azure_api_key",
    "api_key": "'"$AZURE_API_KEY"'",
    "api_version": "2024-10-21",
    "default_model": "gpt-4.1-mini"
  }'
```

## Register Azure With Entra Token Auth

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/azure/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Azure Entra",
    "base_url": "https://YOUR_RESOURCE.services.ai.azure.com",
    "auth_mode": "azure_ad_token",
    "ad_token": "'"$AZURE_AD_TOKEN"'",
    "api_version": "2024-10-21",
    "default_model": "gpt-4.1"
  }'
```

Credential posture:

- Azure credentials are persisted as provider secret references.
- Provider responses never return plaintext Azure credentials.

## Test Provider Connectivity

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/test" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "prompt": "Reply in one sentence confirming Azure runtime connectivity."
  }'
```

Azure capability snapshots include additional posture fields:

- `azure_api_version`
- `azure_auth_mode`

## Invoke Through Normalized Runtime Seam

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "thread_id": "'"$THREAD_ID"'",
    "message": "Summarize current enterprise runtime status in one sentence."
  }'
```

Optional model-pack seam (if you want explicit pack selection):

```json
{
  "pack_id": "llama",
  "pack_version": "1.0.0"
}
```

## AutoGen Sample Path

Use the sprint bridge script to call Alice runtime through an AutoGen-style model client shape:

```bash
./scripts/run_phase11_autogen_runtime_bridge.py \
  --session-token "$SESSION_TOKEN" \
  --provider-id "$PROVIDER_ID" \
  --thread-id "$THREAD_ID" \
  --user-message "Provide a concise status update." \
  --show-raw
```

The script exposes `AutoGenAliceRuntimeClient.create(messages=[...])`, which lets AutoGen orchestration remain outside Alice while continuity, provider auth, model-pack shaping, and runtime invocation stay inside shipped Alice seams.

## Guardrails

- This sprint adds Azure + AutoGen path only.
- Tier-2 packs and broader framework integrations remain later Phase 11 scope.
