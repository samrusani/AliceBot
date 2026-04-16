# Phase 14 Provider Configuration (P14-S1)

This guide covers the Phase 14 provider foundation paths:

- `POST /v1/providers`
- `PATCH /v1/providers/{provider_id}`
- `POST /v1/providers/test`
- `POST /v1/runtime/invoke`
- workspace bootstrap seeding through `WORKSPACE_PROVIDER_CONFIGS_JSON`
- `scripts/run_phase14_openai_compatible_smoke.py`

Scope note: this page documents the OpenAI-compatible foundation path owned by `P14-S1`.

## API Registration

Register an OpenAI-compatible provider in the current workspace:

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_key": "openai_compatible",
    "display_name": "Primary OpenAI-Compatible",
    "base_url": "https://provider.example/v1",
    "api_key": "'"$PROVIDER_API_KEY"'",
    "default_model": "gpt-5-mini"
  }'
```

Capability discovery runs during registration and stores:

- `health_status`
- `health_endpoint`
- `models_endpoint`
- `invoke_endpoint`
- `model_count`
- `models`
- `supports_reasoning`

## Config Registration

Workspace bootstrap can seed OpenAI-compatible providers from config with `WORKSPACE_PROVIDER_CONFIGS_JSON`.

Example:

```bash
export WORKSPACE_PROVIDER_CONFIGS_JSON='[
  {
    "provider_key": "openai_compatible",
    "display_name": "Configured OpenAI-Compatible",
    "base_url": "https://provider.example/v1",
    "api_key": "provider-secret-key",
    "default_model": "gpt-5-mini",
    "model_list_path": "/models",
    "healthcheck_path": "/models",
    "invoke_path": "/responses",
    "metadata": {
      "source": "workspace_bootstrap"
    }
  }
]'
```

Then bootstrap the workspace normally:

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/workspaces/bootstrap" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"workspace_id": "'"$WORKSPACE_ID"'"}'
```

Providers from config are seeded once per workspace when bootstrap completes. Existing providers with the same `provider_key` and `display_name` are left in place.

## Provider Updates

Update provider configuration and refresh capability discovery:

```bash
curl -sS -X PATCH "http://127.0.0.1:8000/v1/providers/$PROVIDER_ID" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Updated OpenAI-Compatible",
    "base_url": "https://provider.example/v1",
    "default_model": "gpt-4.1-mini",
    "model_list_path": "/models",
    "healthcheck_path": "/models",
    "invoke_path": "/responses"
  }'
```

For bearer-auth OpenAI-compatible providers, send `api_key` when rotating credentials.

## Provider Test

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/test" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "prompt": "Reply with one sentence confirming connectivity."
  }'
```

The provider-test flow persists normalized invocation telemetry with status, latency, response ID, usage, and error detail.

## Runtime Invoke

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "thread_id": "'"$THREAD_ID"'",
    "message": "Summarize runtime status in one sentence."
  }'
```

One-call continuity still runs through the normal continuity compiler and response trace path. The provider layer adds capability discovery plus invocation telemetry without changing continuity semantics.

## Smoke Script

Run the Phase 14 smoke flow against a real endpoint:

```bash
./scripts/run_phase14_openai_compatible_smoke.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --provider-base-url "https://provider.example/v1" \
  --model "gpt-5-mini"
```

Or let the script start a local compliant stub endpoint for the smoke run:

```bash
./scripts/run_phase14_openai_compatible_smoke.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --model "gpt-5-mini"
```
