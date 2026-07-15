# Local + Self-Hosted Provider Adapters

Alice retains local registration, discovery, testing, and invocation for
Ollama, llama.cpp/llama-server, and vLLM. These adapters support embeddings and
model-backed memory workflows; they are not a bundled chat product.

Use `X-AliceBot-User-Id` (or `ALICEBOT_AUTH_USER_ID`) for the local operator.
Hosted session bearer tokens and model packs are not part of this boundary.

```bash
export ALICE_USER_ID=00000000-0000-0000-0000-000000000001
curl -sS -X POST http://127.0.0.1:8000/v1/workspaces/bootstrap \
  -H "X-AliceBot-User-Id: $ALICE_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{}'

curl -sS -X POST http://127.0.0.1:8000/v1/providers/ollama/register \
  -H "X-AliceBot-User-Id: $ALICE_USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Ollama Local","base_url":"http://127.0.0.1:11434","default_model":"llama3.2:latest"}'
```

Equivalent registration routes are available for `llamacpp` and `vllm`.
`POST /v1/providers/test` records normalized capability/health telemetry, and
`POST /v1/runtime/invoke` requires an `Idempotency-Key` for each logical call.
See [Provider Runtime Setup Paths](phase11-setup-paths.md) for the common
request contract.

For an end-to-end local adapter check, the helper bootstraps the deterministic
local workspace before registering, testing, and invoking the provider:

```bash
./.venv/bin/python scripts/run_phase11_local_provider_e2e.py \
  --user-id "$ALICE_USER_ID" \
  --thread-id "$THREAD_ID" \
  --provider ollama \
  --model llama3.2:latest
```
