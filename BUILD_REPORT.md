# BUILD_REPORT

## sprint objective
Implement Phase 11 Sprint 2 (`P11-S2`) local-provider support by shipping Ollama and llama.cpp adapters behind the existing provider abstraction, including registration, model enumeration + health posture snapshots, and normalized runtime invoke through existing `v1` seams.

## completed work
- Added local provider transport helpers in `apps/api/src/alicebot_api/local_provider_helpers.py`:
  - auth header handling (`bearer`/`none`)
  - deterministic JSON request helper
  - Ollama/llama.cpp model enumeration parsers
  - Ollama/llama.cpp invoke response normalization
- Extended provider runtime adapters in `apps/api/src/alicebot_api/provider_runtime.py`:
  - added `ollama` and `llamacpp` adapter keys and implementations
  - registered both adapters in the existing provider registry
  - added deterministic capability snapshot fields for local health/model posture
  - preserved normalized runtime provider seam (`openai_responses`)
- Added additive model provider config fields in persistence:
  - migration `apps/api/alembic/versions/20260411_0053_phase11_local_provider_config_fields.py`
  - store/runtime wiring for `auth_mode`, `model_list_path`, `healthcheck_path`, `invoke_path`
- Updated API contract and serialization surfaces:
  - `apps/api/src/alicebot_api/contracts.py`
  - `apps/api/src/alicebot_api/store.py`
  - `apps/api/src/alicebot_api/main.py`
- Added new registration APIs in `apps/api/src/alicebot_api/main.py`:
  - `POST /v1/providers/ollama/register`
  - `POST /v1/providers/llamacpp/register`
- Kept existing in-scope APIs working with local adapters:
  - `POST /v1/providers/test`
  - `POST /v1/runtime/invoke`
  - `GET /v1/providers`
  - `GET /v1/providers/{provider_id}`
- Added failure-safe capability behavior:
  - registration stores failed discovery posture when local provider is unreachable
  - provider test stores failed discovery posture when capability discovery fails
- Added sprint verification tests:
  - `tests/unit/test_provider_runtime.py`
  - `tests/unit/test_20260411_0053_phase11_local_provider_config_fields.py`
  - `tests/integration/test_phase11_provider_runtime_api.py`
- Added local setup docs and runnable example paths:
  - `docs/integrations/phase11-local-provider-adapters.md`
  - `scripts/run_phase11_local_provider_e2e.py`
- Updated control-doc truth checker markers for current sprint state:
  - `scripts/check_control_doc_truth.py`
  - linked new integration doc from `README.md`

## incomplete work
- None for `P11-S2` acceptance criteria and required verification commands.

## files changed
- `apps/api/src/alicebot_api/local_provider_helpers.py`
- `apps/api/src/alicebot_api/provider_runtime.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/alembic/versions/20260411_0053_phase11_local_provider_config_fields.py`
- `tests/unit/test_provider_runtime.py`
- `tests/unit/test_20260411_0053_phase11_local_provider_config_fields.py`
- `tests/integration/test_phase11_provider_runtime_api.py`
- `docs/integrations/phase11-local-provider-adapters.md`
- `scripts/run_phase11_local_provider_e2e.py`
- `scripts/check_control_doc_truth.py`
- `README.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
  - Result: `PASS`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: `PASS` (`1118 passed in 183.14s (0:03:03)`)
- `pnpm --dir apps/web test`
  - Result: `PASS` (`62 files`, `199 tests`, duration `4.82s`)
- Sprint-targeted subset:
  - `./.venv/bin/python -m pytest tests/unit/test_provider_runtime.py tests/unit/test_20260411_0053_phase11_local_provider_config_fields.py tests/integration/test_phase11_provider_runtime_api.py -q`
  - Result: `PASS` (`12 passed in 2.50s`)

## blockers/issues
- No active implementation blockers.

## recommended next step
1. Open a sprint PR from `codex/phase11-sprint-2-ollama-llamacpp-adapters` with this report and required test evidence.
2. Keep pre-existing dirty local docs (`ARCHITECTURE.md`, `PRODUCT_BRIEF.md`) excluded from sprint merge scope.
