# Phase 11 Provider + Model Pack Compatibility (P11-S6)

This reference defines the shipped provider/pack compatibility posture for Phase 11 closeout.

## Built-In Catalog Packs

All built-in catalog packs are seeded per workspace on first model-pack API access and use:

- `contract_version = model_pack_contract_v1`
- `runtime_providers = ["openai_responses"]`
- `tools.mode = "none"`

| Pack ID | Version | Tier | Family | Provider Keys | Runtime Provider |
|---|---|---|---|---|---|
| `llama` | `1.0.0` | `tier1` | `llama` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `qwen` | `1.0.0` | `tier1` | `qwen` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `gemma` | `1.0.0` | `tier1` | `gemma` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `gpt-oss` | `1.0.0` | `tier1` | `gpt-oss` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `deepseek` | `1.0.0` | `tier2` | `deepseek` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `kimi` | `1.0.0` | `tier2` | `kimi` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |
| `mistral` | `1.0.0` | `tier2` | `mistral` | `openai_compatible`, `ollama`, `llamacpp` | `openai_responses` |

## Shipped Provider Paths

| Path | Adapter Key | Primary APIs | Pack Posture |
|---|---|---|---|
| Local (Ollama) | `ollama` | `POST /v1/providers/ollama/register`, `POST /v1/providers/test`, `POST /v1/runtime/invoke` | Built-in catalog packs supported per pack `provider_keys`. |
| Local (llama.cpp) | `llamacpp` | `POST /v1/providers/llamacpp/register`, `POST /v1/providers/test`, `POST /v1/runtime/invoke` | Built-in catalog packs supported per pack `provider_keys`. |
| Self-hosted OpenAI-compatible (including vLLM path) | `openai_compatible` | `POST /v1/providers`, `POST /v1/providers/test`, `POST /v1/runtime/invoke` | Built-in catalog packs supported per pack `provider_keys`. |
| Enterprise Azure | `azure` | `POST /v1/providers/azure/register`, `POST /v1/providers/test`, `POST /v1/runtime/invoke` | Uses the same pack seam; built-in catalog contracts are not Azure-keyed. Use custom packs when Azure-specific compatibility metadata is required. |
| External-agent orchestration (AutoGen bridge) | runtime passthrough to configured provider | `scripts/run_phase11_autogen_runtime_bridge.py` + `POST /v1/runtime/invoke` | Same pack selection rules and metadata as direct runtime invoke. |

## Scope Notes

- Provider behavior stays in adapters; pack behavior stays declarative in pack contracts.
- This document reflects shipped Phase 11 surfaces only; no new providers or frameworks are implied.
