# Provider Runtime Setup Paths

This guide covers the retained local provider/runtime boundary. It does not use
hosted sessions, multi-workspace administration, or model packs.

## Shared prerequisites

1. Start the Alice API and data services.
2. Set `ALICEBOT_AUTH_USER_ID` for the local operator, or send the same UUID in
   `X-AliceBot-User-Id`.
3. Bootstrap the deterministic local workspace through
   `POST /v1/workspaces/bootstrap`.
4. Have a thread ID available for runtime invocation.

Example header used below:

```bash
export ALICE_USER_ID=00000000-0000-0000-0000-000000000001
```

## Register and test a provider

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/providers/ollama/register \
  -H "X-AliceBot-User-Id: $ALICE_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Local Ollama","base_url":"http://127.0.0.1:11434","default_model":"qwen2.5:7b-instruct"}'
```

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/providers/test \
  -H "X-AliceBot-User-Id: $ALICE_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"provider_id":"'"$PROVIDER_ID"'","prompt":"Confirm connectivity."}'
```

Ollama, llama.cpp/llama-server, vLLM, Azure, and generic OpenAI-compatible
registration all use the same local identity and capability-discovery boundary.

## Invoke with durable idempotency

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/runtime/invoke \
  -H "X-AliceBot-User-Id: $ALICE_USER_ID" \
  -H "Idempotency-Key: runtime-$(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"provider_id":"'"$PROVIDER_ID"'","thread_id":"'"$THREAD_ID"'","message":"Summarize runtime status."}'
```

Reuse the same idempotency key only when retrying the same logical invocation.
The public `/v0/responses` chat endpoint is removed in v0.11; the internal
response-job machinery remains behind `/v1/runtime/invoke` so provider retries
cannot duplicate charges.

## Verification

1. Provider list/get returns only the local operator's records.
2. Provider test records capability and invocation telemetry without secrets.
3. Runtime invoke replays a completed idempotent result and returns `202` while
   the original request is still active.
4. No model-pack field or hosted bearer-session requirement appears in the
   request or response contract.
