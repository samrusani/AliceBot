# BUILD_REPORT

## sprint objective
Create the stable provider foundation and unlock an OpenAI-compatible runtime without changing continuity semantics.

## completed work
- finalized the provider adapter code surface around health checks, model listing, normalized response handling, usage normalization, and OpenAI-compatible invoke path support
- upgraded the OpenAI-compatible adapter to perform real capability discovery against `/models` and to honor configured invoke paths
- added workspace-scoped config seeding through `WORKSPACE_PROVIDER_CONFIGS_JSON` during workspace bootstrap
- added `PATCH /v1/providers/{provider_id}` for provider updates with capability refresh
- persisted normalized provider invocation telemetry for both provider test calls and one-call runtime invoke flows
- added the Phase 14 provider invocation telemetry migration and store helpers
- added focused unit and integration coverage for config seeding, provider updates, OpenAI-compatible discovery, telemetry persistence, and hosted RLS on the new telemetry table
- added provider/runtime docs for Phase 14 configuration and a reusable OpenAI-compatible smoke script
- tightened Phase 14 architecture and contract docs back to implemented `P14-S1` truth
- completed the live smoke flow against a real local Alice API session and a temporary compliant stub provider, then confirmed the expected `provider_invocation_telemetry` rows persisted

## incomplete work
- none for the declared `P14-S1` scope

## files changed
- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `ARCHITECTURE.md`
- `CURRENT_STATE.md`
- `PRODUCT_BRIEF.md`
- `README.md`
- `ROADMAP.md`
- `RULES.md`
- `apps/api/src/alicebot_api/config.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/provider_runtime.py`
- `apps/api/src/alicebot_api/response_generation.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/alembic/versions/20260415_0063_phase14_provider_invocation_telemetry.py`
- `scripts/check_control_doc_truth.py`
- `tests/unit/test_config.py`
- `tests/unit/test_provider_runtime.py`
- `tests/unit/test_20260415_0063_phase14_provider_invocation_telemetry.py`
- `tests/integration/test_phase11_provider_runtime_api.py`
- `scripts/run_phase14_openai_compatible_smoke.py`
- `docs/integrations/phase14-provider-configuration.md`
- `docs/phase14-product-spec.md`
- `docs/phase14-provider-adapter-contract.md`
- `docs/phase14-s1-control-tower-packet.md`
- `docs/phase14-s2-control-tower-packet.md`
- `docs/phase14-s3-control-tower-packet.md`
- `docs/phase14-s4-control-tower-packet.md`
- `docs/phase14-s5-control-tower-packet.md`
- `docs/phase14-sprint-14-1-14-5-plan.md`
- `docs/phase14-model-pack-contract.md`
- `docs/phase14-design-partner-launch.md`
- `docs/phase14-launch-checklist.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- `./.venv/bin/python -m pytest tests/unit/test_provider_runtime.py tests/unit/test_config.py tests/unit/test_20260415_0063_phase14_provider_invocation_telemetry.py -q`
- `./.venv/bin/python -m pytest tests/integration/test_phase11_provider_runtime_api.py -q`
- `python3 -m py_compile scripts/run_phase14_openai_compatible_smoke.py`
- `python3 scripts/run_phase14_openai_compatible_smoke.py --help`
- `./.venv/bin/python scripts/run_phase14_openai_compatible_smoke.py --api-base-url http://127.0.0.1:8017 --session-token <redacted-session-token> --thread-id <generated-thread-id> --model gpt-5-mini`
  - `provider_test` succeeded
  - `runtime_invoke` succeeded
  - persisted telemetry rows: `provider_test`, `runtime_invoke`

## blockers/issues
- no blocker remains for the declared `P14-S1` scope

## recommended next step
Proceed to `P14-S2` or package this sprint for merge/review handoff with the provider telemetry RLS posture preserved as the baseline for later workspace-scoped runtime tables.
