# Phase 14 Model Pack Compatibility Matrix (P14-S3)

This reference defines the shipped first-party pack compatibility posture for `P14-S3`.

## Built-In Catalog Packs

All built-in catalog packs are seeded per workspace on first model-pack API access and use:

- `contract_version = model_pack_contract_v1`
- `runtime_providers = ["openai_responses"]`
- `tools.mode = "none"`

| Pack ID | Version | Family | Provider Keys | Runtime Provider | Default Briefing |
|---|---|---|---|---|---|
| `llama` | `1.0.0` | `llama` | `openai_compatible`, `ollama`, `llamacpp`, `vllm` | `openai_responses` | `compact`, `160` |
| `qwen` | `1.0.0` | `qwen` | `openai_compatible`, `ollama`, `llamacpp`, `vllm` | `openai_responses` | `compact`, `144` |
| `gemma` | `1.0.0` | `gemma` | `openai_compatible`, `ollama`, `llamacpp`, `vllm` | `openai_responses` | `compact`, `128` |
| `gpt-oss` | `1.0.0` | `gpt-oss` | `openai_compatible`, `ollama`, `llamacpp`, `vllm` | `openai_responses` | `balanced`, `192` |

## Binding Resolution

- request override
- provider-specific workspace binding
- workspace default binding
- no pack

Provider-specific bindings must satisfy both:
- `compatibility.provider_keys`
- `compatibility.runtime_providers`

Workspace default bindings intentionally stay provider-agnostic so briefing defaults can resolve without a provider id.

## Deferred Families

DeepSeek, Mistral, Kimi, and other non-first-party families are not shipped as built-in catalog entries in `P14-S3`. They require custom packs until a later sprint adds first-party definitions.

## Scope Notes

- Provider behavior stays in adapters.
- Pack behavior stays declarative in pack contracts and briefing defaults.
- `P14-S3` does not reopen provider work or add new runtime providers.
