# Model Pack Compatibility Matrix

This reference defines the shipped first-party pack compatibility posture.

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

DeepSeek, Mistral, Kimi, and other non-first-party families are not shipped as built-in catalog entries. They require custom packs until first-party definitions are added.

## Scope Notes

- Provider behavior stays in adapters.
- Pack behavior stays declarative in pack contracts and briefing defaults.
- The pack compatibility layer does not reopen provider work or add new runtime providers.
