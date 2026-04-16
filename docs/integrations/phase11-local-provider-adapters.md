# Local + Self-Hosted Provider Adapters

This guide covers the sprint-owned local and self-hosted provider paths:

- `POST /v1/providers/ollama/register`
- `POST /v1/providers/llamacpp/register`
- `POST /v1/providers/vllm/register`
- `POST /v1/providers/test`
- `POST /v1/runtime/invoke`
- `GET /v1/providers`
- `GET /v1/providers/{provider_id}`

Scope note: this page documents Ollama, llama.cpp / llama-server, and self-hosted vLLM.

## Prerequisites

1. Start Alice API and data services.
2. Authenticate and obtain a hosted session bearer token.
3. Have a thread ID available for runtime invoke.
4. Run at least one local model backend:
   - Ollama server (default `http://127.0.0.1:11434`)
   - llama.cpp server (default `http://127.0.0.1:8080`)
   - vLLM server (recommended `http://127.0.0.1:8001`)

## Register Ollama

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/ollama/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Ollama Local",
    "base_url": "http://127.0.0.1:11434",
    "default_model": "llama3.2:latest"
  }'
```

## Register llama.cpp / llama-server

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/llamacpp/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "llama.cpp Local",
    "base_url": "http://127.0.0.1:8080",
    "default_model": "Meta-Llama-3.1-8B-Instruct"
  }'
```

## Register vLLM

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/vllm/register" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "vLLM Self-Hosted",
    "base_url": "http://127.0.0.1:8001",
    "default_model": "mistral-small-instruct"
  }'
```

## Test Provider Connectivity

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/providers/test" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "prompt": "Reply with one sentence confirming local connectivity."
  }'
```

Capability snapshots include deterministic local model enumeration and health posture fields:

- `health_status`
- `health_endpoint`
- `models_endpoint`
- `invoke_endpoint`
- `model_count`
- `models`

## Invoke Through Normalized Runtime Seam

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/runtime/invoke" \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "'"$PROVIDER_ID"'",
    "thread_id": "'"$THREAD_ID"'",
    "message": "Summarize current runtime status in one sentence."
  }'
```

## Runnable End-to-End Script

Use the sprint helper script for a full register/test/invoke flow:

```bash
./scripts/run_phase11_local_provider_e2e.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --provider ollama \
  --model llama3.2:latest
```

Or for llama.cpp:

```bash
./scripts/run_phase11_local_provider_e2e.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --provider llamacpp \
  --model Meta-Llama-3.1-8B-Instruct
```

Or for vLLM:

```bash
./scripts/run_phase11_local_provider_e2e.py \
  --session-token "$SESSION_TOKEN" \
  --thread-id "$THREAD_ID" \
  --provider vllm \
  --model mistral-small-instruct
```
