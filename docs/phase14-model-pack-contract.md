# Phase 14 Model Pack Contract

## Purpose
Define the declarative pack profile Alice uses to make provider-backed models usable without manual tuning.

## Rule
Model packs are profiles, not forks.

They may shape defaults for prompting, briefing, tools, token budgets, and quirks, but they must not create new continuity semantics.

## Required Fields
- `pack_id`
- `family`
- `display_name`
- `provider_type`
- `default_model_name`
- `supports_tools`
- `supports_reasoning`
- `supports_vision`
- `briefing_strategy`
- `resume_brief_style`
- `max_context_pack_tokens`
- `max_brief_tokens`
- `default_temperature`
- `default_top_p`
- `evidence_strategy`
- `known_quirks`

## Initial First-Party Families
- Llama
- Qwen
- Gemma
- `gpt-oss`

Optional later Phase 14 families if capacity remains:
- DeepSeek
- Mistral

## Binding Rules
- a workspace binds a provider to a model pack
- packs must be versioned
- pack bindings may allow model-name override without semantic drift
- pack defaults must flow into runtime invocation and briefing behavior

## Success Condition
Users should be able to bind a supported provider to a first-party pack and get sensible continuity defaults without hand tuning or hidden behavior changes.
