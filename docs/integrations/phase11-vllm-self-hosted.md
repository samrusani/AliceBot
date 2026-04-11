# Phase 11 vLLM Self-Hosted Path (P11-S3)

This guide covers the sprint-owned vLLM self-hosted provider path:

- `POST /v1/providers/vllm/register`
- `POST /v1/providers/test`
- `POST /v1/runtime/invoke`
- `GET /v1/providers`
- `GET /v1/providers/{provider_id}`
- `GET /v1/providers/{provider_id}/telemetry`

Scope note: this page documents vLLM only.

## Prerequisites

1. Start Alice API and data services.
2. Authenticate and obtain a hosted session bearer token.
3. Have a thread ID available for runtime invoke.
4. Run a self-hosted vLLM server exposing OpenAI-compatible endpoints.
   - Example split: Alice API at `http://127.0.0.1:8000`, vLLM provider at `http://127.0.0.1:8001`.

## Register vLLM Provider

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/vllm/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "vLLM Self-Hosted",
    "base_url": "http://127.0.0.1:8001",
    "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
    "adapter_options": {
      "invoke_passthrough": {
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 256,
        "stop": ["###"]
      }
    }
  }'
```

`adapter_options.invoke_passthrough` is bounded to explicit allowlisted fields:

- `temperature`
- `top_p`
- `max_tokens`
- `frequency_penalty`
- `presence_penalty`
- `n`
- `seed`
- `stop`

## Test Provider Connectivity

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/test" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'$PROVIDER_ID'",
    "prompt": "Reply with one sentence confirming self-hosted connectivity."
  }'
```

## Invoke Through Normalized Runtime Seam

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'$PROVIDER_ID'",
    "thread_id": "'$THREAD_ID'",
    "message": "Summarize current runtime status in one sentence."
  }'
```

## View Provider Telemetry

```bash
curl -sS "http://127.0.0.1:8000/v1/providers/$PROVIDER_ID/telemetry?limit=20" \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

Telemetry includes normalized latency and usage evidence for `provider_test` and `runtime_invoke` flows.

## Runnable End-to-End Script

Use the sprint helper script for a full register/test/invoke/telemetry flow:

```bash
./scripts/run_phase11_vllm_e2e.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --provider-base-url "http://127.0.0.1:8001" \
  --model "meta-llama/Meta-Llama-3.1-8B-Instruct" \
  --temperature 0.2 \
  --top-p 0.9 \
  --max-tokens 256
```
