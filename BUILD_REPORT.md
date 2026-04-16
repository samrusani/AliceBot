# BUILD_REPORT

## sprint objective

Make common model families easy to use with sensible continuity defaults on top of the shipped provider/runtime baseline by shipping the `P14-S3` model-pack workflow.

## completed work

- Added provider-aware model-pack bindings by extending workspace bindings with an optional `provider_id`.
- Kept workspace-default bindings in place so briefing defaults can still resolve without a provider id.
- Updated model-pack resolution so runtime selection now follows request override, provider-specific binding, workspace default binding, then no pack.
- Added runtime compatibility enforcement using declarative pack contract fields (`compatibility.provider_keys` and `compatibility.runtime_providers`).
- Updated the bind API to accept optional `provider_id`, validate provider existence in the workspace, and reject incompatible provider-to-pack bindings with `409`.
- Updated runtime invoke to reject incompatible pack/provider combinations with `409` instead of silently applying the wrong defaults.
- Trimmed the built-in first-party catalog to the four `P14-S3` packs: `llama`, `qwen`, `gemma`, and `gpt-oss`.
- Added a migration and migration unit coverage for provider-aware workspace model-pack bindings.
- Updated targeted unit and integration coverage for provider-aware binding, first-party catalog expectations, and compatibility enforcement.
- Added provider-surface pack smoke coverage across the shipped `ollama`, `llamacpp`, and `vllm` runtime paths.
- Updated the model-pack contract and compatibility docs to match the shipped `P14-S3` behavior.

## incomplete work

- No implementation items remain within the sprint scope.
- Deferred families such as DeepSeek, Mistral, and Kimi remain out of the first-party catalog for this sprint.

## files changed

- `apps/api/alembic/versions/20260416_0064_phase14_provider_model_pack_bindings.py`
- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `ROADMAP.md`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/model_packs.py`
- `apps/api/src/alicebot_api/store.py`
- `docs/integrations/phase11-model-pack-compatibility.md`
- `docs/integrations/phase11-model-packs-tier1.md`
- `docs/phase14-model-pack-contract.md`
- `docs/phase14-s3-control-tower-packet.md`
- `docs/phase14-sprint-14-1-14-5-plan.md`
- `scripts/check_control_doc_truth.py`
- `tests/integration/test_phase11_model_packs_api.py`
- `tests/unit/test_20260416_0064_phase14_provider_model_pack_bindings.py`
- `tests/unit/test_model_packs.py`

## tests run

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_model_packs.py tests/unit/test_task_briefing.py tests/unit/test_20260416_0064_phase14_provider_model_pack_bindings.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_model_packs_api.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_provider_runtime_api.py -q`

## blockers/issues

- No blocking implementation issues remain.
- Pack smoke validation in this build is covered by focused integration smoke over the shipped provider/runtime surfaces (`ollama`, `llamacpp`, `vllm`) rather than by external provider processes.

## recommended next step

Decide whether DeepSeek and Mistral stay deferred or become first-party packs in the next sprint, then extend the compatibility matrix only after that product decision is settled.
