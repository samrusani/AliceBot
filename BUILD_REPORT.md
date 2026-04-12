# BUILD_REPORT

## sprint objective
Implement Phase 11 Sprint 4 (`P11-S4`) Model Packs Tier 1 by adding a declarative model-pack layer with tier-1 packs (`llama`, `qwen`, `gemma`, `gpt-oss`), pack catalog/versioning APIs, workspace binding APIs, and pack-driven runtime shaping on the existing `POST /v1/runtime/invoke` seam.

## completed work
- Added new persistence tables via migration:
  - `model_packs`
  - `workspace_model_pack_bindings`
  - workspace-consistent binding foreign-key integrity (`model_pack_id`, `workspace_id`)
- Added model-pack domain helper module:
  - `apps/api/src/alicebot_api/model_packs.py`
  - contract validation (`model_pack_contract_v1`)
  - tier-1 pack seeding for workspace scope with concurrency-safe upsert behavior
  - pack version and family normalization
  - canonical tier-1 pack key reservation checks
  - workspace binding vs request override precedence resolution
  - declarative runtime shaping helpers (context cap shaping + instruction overlays)
- Extended store layer in `apps/api/src/alicebot_api/store.py`:
  - typed rows for model packs and bindings
  - model-pack CRUD/list/get queries
  - binding create/get-latest queries (workspace-scoped)
- Extended API contracts in `apps/api/src/alicebot_api/contracts.py`:
  - model-pack families/status/binding-source literals
  - model-pack response typed dicts and list order constant
- Added new v1 model-pack endpoints in `apps/api/src/alicebot_api/main.py`:
  - `GET /v1/model-packs`
  - `GET /v1/model-packs/{pack_id}`
  - `POST /v1/model-packs`
  - `POST /v1/model-packs/{pack_id}/bind`
  - `GET /v1/workspaces/{workspace_id}/model-pack-binding`
- Updated `POST /v1/runtime/invoke` in `apps/api/src/alicebot_api/main.py`:
  - pack selection precedence: request override > workspace binding > none
  - pack-driven context cap shaping and instruction overlays
  - model-pack metadata returned for invoke auditing
  - no parallel runtime path created; existing provider invoke seam preserved
- Updated response generation seam in `apps/api/src/alicebot_api/response_generation.py`:
  - added optional system/developer instruction overrides for runtime shaping
  - default `v0/responses` behavior remains unchanged
- Added sprint docs under `docs/`:
  - `docs/integrations/phase11-model-packs-tier1.md`
  - `docs/integrations/phase11-model-pack-compatibility.md`
- Updated control-doc truth markers for active sprint alignment:
  - `scripts/check_control_doc_truth.py`
- Updated active sprint truth markers:
  - `README.md`
- Added sprint tests:
  - unit: `tests/unit/test_model_packs.py`
  - migration unit: `tests/unit/test_20260412_0054_phase11_model_packs_tier1.py`
  - integration: `tests/integration/test_phase11_model_packs_api.py`

## incomplete work
- None identified against `P11-S4` packet acceptance criteria and required API/data scope.

## files changed
- `apps/api/alembic/versions/20260412_0054_phase11_model_packs_tier1.py`
- `apps/api/src/alicebot_api/model_packs.py`
- `apps/api/src/alicebot_api/store.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/response_generation.py`
- `docs/integrations/phase11-model-packs-tier1.md`
- `docs/integrations/phase11-model-pack-compatibility.md`
- `tests/unit/test_model_packs.py`
- `tests/unit/test_20260412_0054_phase11_model_packs_tier1.py`
- `tests/integration/test_phase11_model_packs_api.py`
- `scripts/check_control_doc_truth.py`
- `README.md`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
  - Result: `PASS`
- `./.venv/bin/python -m pytest tests/unit tests/integration -q`
  - Result: `PASS` (`1133 passed in 188.69s (0:03:08)`)
- `pnpm --dir apps/web test`
  - Result: `PASS` (`62` files, `199` tests, duration `4.66s`)
- Sprint-targeted verification subsets:
  - `./.venv/bin/python -m pytest tests/unit/test_model_packs.py tests/unit/test_20260412_0054_phase11_model_packs_tier1.py tests/integration/test_phase11_model_packs_api.py -q`
  - Result: `PASS` (`15 passed in 1.47s`)
  - `python3 -m pytest tests/unit/test_control_doc_truth.py tests/unit/test_response_generation.py tests/integration/test_phase11_provider_runtime_api.py -q`
  - Result: `PASS` (`15 passed in 2.25s`)

## blockers/issues
- No active blockers.
- Pre-existing dirty files were present before sprint implementation and were not modified as part of this sprint scope: `ARCHITECTURE.md`, `PRODUCT_BRIEF.md`.

## recommended next step
1. Open/refresh a sprint PR for `P11-S4` and keep only the sprint-owned files above in merge scope.
2. Run reviewer pass focused on `P11-S4` acceptance criteria and workspace-isolation/runtime-shaping behavior.
