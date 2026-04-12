# Phase 11 Model Pack Compatibility (P11-S4)

This table is the sprint-owned compatibility reference for tier-1 model packs.

| Pack ID | Version | Family | Runtime Provider | Provider Keys | Tool Mode |
|---|---|---|---|---|---|
| `llama` | `1.0.0` | `llama` | `openai_responses` | `openai_compatible`, `ollama`, `llamacpp` | `none` |
| `qwen` | `1.0.0` | `qwen` | `openai_responses` | `openai_compatible`, `ollama`, `llamacpp` | `none` |
| `gemma` | `1.0.0` | `gemma` | `openai_responses` | `openai_compatible`, `ollama`, `llamacpp` | `none` |
| `gpt-oss` | `1.0.0` | `gpt-oss` | `openai_responses` | `openai_compatible`, `ollama`, `llamacpp` | `none` |

## Scope Notes

- This reference is limited to tier-1 packs shipped in `P11-S4`.
- Azure and tier-2 packs are explicitly out of scope for this sprint.
- Provider adapter behavior remains in adapters; model-pack behavior remains declarative in pack contracts.
