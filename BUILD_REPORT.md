# BUILD_REPORT

## sprint objective
Implement `P11-S6` by adding tier-2 model packs (DeepSeek, Kimi, Mistral) on the shipped model-pack abstraction, plus compatibility/setup clarity assets for local, self-hosted, enterprise, and external-agent paths, without reopening `P11-S1` through `P11-S5` architecture.

## completed work
- Added tier-2 built-in pack specs in `model_packs.py`:
  - `deepseek@1.0.0`
  - `kimi@1.0.0`
  - `mistral@1.0.0`
- Preserved shipped pack API behavior and selection semantics:
  - seeded catalog still resolves through existing `/v1/model-packs` flow
  - workspace binding and request override precedence are unchanged
  - no new runtime/provider paths were introduced
- Extended family contract/type support for tier-2 families:
  - `deepseek`, `kimi`, `mistral`
- Added additive migration `20260412_0056_phase11_model_packs_tier2_families.py` to widen `model_packs_family_check` without schema redesign.
- Updated catalog reservation conflict text to cover built-in catalog entries (tier-1 + tier-2).
- Added/updated sprint docs:
  - `docs/integrations/phase11-model-pack-compatibility.md` with provider/pack compatibility matrices
  - `docs/integrations/phase11-setup-paths.md` with operator setup paths for local, self-hosted, enterprise, and external-agent use
  - `docs/integrations/phase11-azure-autogen.md` guardrails/references refreshed for P11-S6
- Updated sprint-owned tests for tier-2 catalog presence, runtime override behavior, and migration coverage.
- Updated control-doc truth checker markers to active `P11-S6` packet/state markers.
- Updated `REVIEW_REPORT.md` for `P11-S6`.

## incomplete work
- None within the sprint packet scope.

## files changed
- `apps/api/src/alicebot_api/model_packs.py`
- `apps/api/src/alicebot_api/contracts.py`
- `apps/api/src/alicebot_api/main.py`
- `apps/api/alembic/versions/20260412_0056_phase11_model_packs_tier2_families.py` (new)
- `tests/unit/test_model_packs.py`
- `tests/integration/test_phase11_model_packs_api.py`
- `tests/unit/test_20260412_0056_phase11_model_packs_tier2_families.py` (new)
- `docs/integrations/phase11-model-pack-compatibility.md`
- `docs/integrations/phase11-setup-paths.md` (new)
- `docs/integrations/phase11-azure-autogen.md`
- `scripts/check_control_doc_truth.py`
- `REVIEW_REPORT.md`
- `BUILD_REPORT.md`

## tests run
1. `python3 scripts/check_control_doc_truth.py`
- Result: PASS

2. `./.venv/bin/python -m pytest tests/unit tests/integration -q`
- Result: PASS (`1145 passed in 185.18s (0:03:05)`)

3. `pnpm --dir apps/web test`
- Result: PASS (`62 files`, `199 tests passed`, duration `5.49s`)

4. Focused sprint tests during implementation:
- `./.venv/bin/python -m pytest tests/unit/test_model_packs.py tests/integration/test_phase11_model_packs_api.py tests/unit/test_20260412_0056_phase11_model_packs_tier2_families.py -q`
- Result: PASS (`14 passed in 1.62s`)

## blockers/issues
- No functional blockers for sprint scope implementation.
- Pre-existing dirty file not modified as sprint work and excluded from sprint merge scope:
  - `README.md`

## recommended next step
Proceed to merge review for `P11-S6`, then run staging smoke checks for one local provider, one self-hosted OpenAI-compatible provider, and one Azure provider with tier-2 and custom pack coverage.
