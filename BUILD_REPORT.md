# BUILD_REPORT

## sprint objective
Implement `P11-S3` by adding a vLLM adapter and self-hosted runtime path through the existing provider abstraction, with bounded provider-specific passthrough options, normalized latency/usage telemetry persistence and API exposure, plus self-hosted docs and runnable examples.

## completed work
- Added vLLM adapter support in provider runtime:
  - new adapter key `vllm`
  - capability discovery via `/health` + `/v1/models`
  - invoke via `/v1/chat/completions`
  - capability snapshot telemetry posture fields (`supports_normalized_latency_telemetry`, `supports_normalized_usage_telemetry`, `telemetry_flow_scope`)
- Added bounded provider-specific passthrough:
  - explicit `adapter_options.invoke_passthrough` schema for vLLM registration
  - bounded allowlist extraction helper for vLLM passthrough options
  - passthrough applied only in vLLM adapter invoke payload
- Added vLLM provider registration endpoint:
  - `POST /v1/providers/vllm/register`
- Added provider telemetry persistence + API:
  - new telemetry storage table and store methods
  - telemetry recording for `/v1/providers/test` and `/v1/runtime/invoke`
  - new endpoint `GET /v1/providers/{provider_id}/telemetry`
- Added additive provider config field support:
  - `model_providers.adapter_options` persisted and serialized
- Added migration:
  - `20260411_0054_phase11_vllm_telemetry`
- Added/updated tests for runtime, integration, and migration coverage
- Added self-hosted docs and runnable script for vLLM end-to-end flow
- Updated control-doc truth check markers to `P11-S3`

## incomplete work
- None identified within sprint scope.

## files changed
Sprint-owned files changed:
- `apps/api/src/alicebot_api/provider_runtime.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/vllm_provider_helpers.py` (new)
- `apps/api/alembic/versions/20260411_0054_phase11_vllm_telemetry.py` (new)
- `tests/unit/test_provider_runtime.py`
- `tests/integration/test_phase11_provider_runtime_api.py`
- `tests/unit/test_20260411_0054_phase11_vllm_telemetry.py` (new)
- `docs/integrations/phase11-vllm-self-hosted.md` (new)
- `scripts/run_phase11_vllm_e2e.py` (new)
- `scripts/check_control_doc_truth.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

Pre-existing dirty files excluded from sprint merge scope:
- `README.md`
- `ARCHITECTURE.md`
- `PRODUCT_BRIEF.md`

## tests run
Required verification commands and exact results:
- `python3 scripts/check_control_doc_truth.py`
  - Result: `PASS`
  - Verified: `README.md`, `ROADMAP.md`, `.ai/active/SPRINT_PACKET.md`, `RULES.md`, `.ai/handoff/CURRENT_STATE.md`, `docs/archive/planning/2026-04-08-context-compaction/README.md`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: `1122 passed in 170.62s (0:02:50)`
- `pnpm --dir apps/web test`
  - Result: `62 passed` test files, `199 passed` tests, duration `4.86s`

## blockers/issues
- No blockers during implementation.

## recommended next step
1. Open the sprint PR from branch `codex/phase11-sprint-3-vllm-adapter-selfhosted` and request review focused on vLLM telemetry schema and endpoint response shape stability.
