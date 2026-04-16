# BUILD_REPORT

## sprint objective

Align Ollama, llama.cpp / llama-server, and vLLM runtime paths to the stabilized provider contract, keep telemetry and continuity behavior consistent across those adapters, and document reproducible local/self-hosted quickstarts.

## completed work

- Added a first-class `vllm` provider adapter with healthcheck, model discovery, and chat-completions invocation aligned to the shared provider runtime contract.
- Added dedicated vLLM response/model parsers so runtime errors and normalization stay provider-specific instead of inheriting llama.cpp labels.
- Added `POST /v1/providers/vllm/register` with adapter-specific defaults for self-hosted vLLM deployments.
- Extended workspace provider config parsing so bootstrap config can seed either `openai_compatible` or `vllm` providers with provider-specific defaults.
- Fixed vLLM healthchecks to treat provider-native empty `200` responses as healthy instead of requiring JSON on `/health`.
- Extended provider contract literals to include `vllm`.
- Updated built-in model-pack compatibility hooks so built-in and custom packs can declare `vllm` in `provider_keys`.
- Extended the local/self-hosted smoke helper script to exercise `ollama`, `llamacpp`, or `vllm`.
- Added targeted unit coverage for the vLLM adapter and config/model-pack compatibility changes.
- Added integration coverage for vLLM registration, capability discovery, provider test, runtime invoke, workspace-config seeding, and pack-contract acceptance.
- Updated provider/runtime docs and quickstarts for the new vLLM adapter path, including the Phase 14 config doc note about dedicated `vllm` config entries.

## incomplete work

- No additional implementation items remain within this sprint scope.
- Control Tower decisions from the sprint packet remain product decisions rather than implementation work:
  - supported minimum runtime versions
  - Azure polish timing
  - any pre-Phase-14 local adapter deprecations

## files changed

- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/local_provider_helpers.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/model_packs.py`
- `apps/api/src/alicebot_api/provider_runtime.py`
- `docs/integrations/phase11-local-provider-adapters.md`
- `docs/integrations/phase11-model-pack-compatibility.md`
- `docs/integrations/phase11-model-packs-tier1.md`
- `docs/integrations/phase11-setup-paths.md`
- `docs/integrations/phase14-provider-configuration.md`
- `scripts/run_phase11_local_provider_e2e.py`
- `tests/integration/test_phase11_model_packs_api.py`
- `tests/integration/test_phase11_provider_runtime_api.py`
- `tests/unit/test_config.py`
- `tests/unit/test_model_packs.py`
- `tests/unit/test_provider_runtime.py`

## tests run

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_provider_runtime.py tests/unit/test_model_packs.py tests/unit/test_config.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_provider_runtime_api.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_model_packs_api.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_provider_runtime_api.py tests/integration/test_phase11_model_packs_api.py -q`
- `git diff --check`

## blockers/issues

- No implementation blockers encountered.
- Real-runtime validation against live Ollama, llama.cpp, and vLLM processes was not run in this build; compatibility proof here is based on targeted unit and integration coverage plus the updated smoke helper.

## recommended next step

Run the updated smoke flow against real local/self-hosted runtimes, then lock the supported runtime-version statement in the Phase 14 docs.
