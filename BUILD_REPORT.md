# BUILD_REPORT.md

## Sprint Objective
Deliver Sprint 7F quantitative MVP readiness evidence: one deterministic command that emits explicit pass/fail/blocked results for acceptance prerequisite, latency p95, cache reuse, and memory quality posture.

## Completed Work
- Added additive usage telemetry support for optional cached token evidence:
  - `cached_input_tokens` is now carried in the model usage contract when provider telemetry is present.
  - Response usage parsing now extracts cached-token telemetry from provider details (`input_tokens_details.cached_tokens` or `prompt_tokens_details.cached_tokens`) without breaking existing payloads.
- Added deterministic test coverage for usage parsing and payload shapes:
  - unit coverage for telemetry absent/present parsing behavior.
  - integration coverage that response event payload and response trace payload retain optional cached telemetry when present.
- Added `scripts/run_mvp_readiness_gates.py`:
  - acceptance suite prerequisite gate (reuses `scripts/run_mvp_acceptance.py`)
  - latency gate (`p95_seconds < 5.0`) from repeated retrieval-plus-response probes
  - cache-reuse gate (`cache_reuse_ratio >= 0.70`) with explicit `BLOCKED` when cached telemetry is unavailable
  - memory-quality gate from shipped summary semantics (`precision >= 0.80` and `adjudicated_sample >= 10`)
  - explicit per-gate output (`PASS` / `FAIL` / `BLOCKED`) and non-zero exit code on any non-pass gate
- Added `tests/integration/test_mvp_readiness_gates.py` validating deterministic gate math and exit-code behavior.
- Added runbook `docs/runbooks/mvp-readiness-gates.md` and aligned `docs/runbooks/memory-quality-gate.md` to runner semantics.
- Updated sprint reports for Sprint 7F.

## Incomplete Work
- None within Sprint 7F scope.

## Files Changed
- `/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/contracts.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/apps/api/src/alicebot_api/response_generation.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/tests/unit/test_response_generation.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_responses_api.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/tests/integration/test_mvp_readiness_gates.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/scripts/run_mvp_readiness_gates.py`
- `/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/mvp-readiness-gates.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/docs/runbooks/memory-quality-gate.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/BUILD_REPORT.md`
- `/Users/samirusani/Desktop/Codex/AliceBot/REVIEW_REPORT.md`

## Exact Readiness Gates Executed
- `acceptance_suite`
- `latency_p95`
- `cache_reuse`
- `memory_quality`

## Exact Commands And Environment Assumptions
- `python3 -m pytest -q tests/unit/test_response_generation.py`
- `python3 -m pytest -q tests/integration/test_mvp_readiness_gates.py`
- `python3 -m pytest -q tests/integration/test_responses_api.py`
- `python3 scripts/run_mvp_acceptance.py`
- `python3 scripts/run_mvp_readiness_gates.py`
- `python3 scripts/run_mvp_readiness_gates.py --induce-gate cache_blocked`

Environment assumptions:
- Local Postgres reachable on configured admin/app URLs.
- Python dependencies installed in project environment.
- Runner uses deterministic in-process model stubs for probe calls; no external model API dependency for readiness probe gate math.

## Per-Gate Outcome Table (Latest Normal Run)

| Gate | Status | Measured | Threshold |
|---|---|---|---|
| `acceptance_suite` | `PASS` | `exit_code=0` | `exit_code == 0` |
| `latency_p95` | `PASS` | `p95_seconds=0.039442` (8 probe samples) | `p95_seconds < 5.0` |
| `cache_reuse` | `PASS` | `cache_reuse_ratio=0.800000` | `cache_reuse_ratio >= 0.70` |
| `memory_quality` | `PASS` | `precision=0.800000; adjudicated_sample=10; unlabeled_memory_count=0; posture=on_track` | `precision >= 0.80 and adjudicated_sample >= 10` |

Command result: `python3 scripts/run_mvp_readiness_gates.py` exited `0` with `MVP readiness gate result: PASS`.

## Blocked/Insufficient-Evidence Handling Summary
- Cache gate handling is explicit and non-pass by design when cached telemetry is unavailable.
- Verified with induced run:
  - `python3 scripts/run_mvp_readiness_gates.py --induce-gate cache_blocked`
  - `cache_reuse` reported `BLOCKED` with `cache_reuse_ratio=unavailable`
  - overall runner result was `NO_GO` with non-zero exit code.
- Memory gate handling maps insufficient adjudicated sample to explicit `BLOCKED` posture (`insufficient_evidence`).

## Tests Run
- `python3 -m pytest -q tests/unit/test_response_generation.py` -> `4 passed`
- `python3 -m pytest -q tests/integration/test_mvp_readiness_gates.py` -> `6 passed`
- `python3 -m pytest -q tests/integration/test_responses_api.py` -> `4 passed`
- `python3 scripts/run_mvp_acceptance.py` -> `PASS` (`3 passed`, exit `0`)
- `python3 scripts/run_mvp_readiness_gates.py` -> `PASS` (all gates `PASS`, exit `0`)
- `python3 scripts/run_mvp_readiness_gates.py --induce-gate cache_blocked` -> `NO_GO` (`cache_reuse` `BLOCKED`, exit non-zero)

## Blockers/Issues
- Localhost Postgres access is sandbox-restricted in this environment, so DB-backed integration tests and runner commands required unsandboxed execution.
- Runner output includes Alembic migration logs during temporary DB setup; this is expected but verbose.

## Explicit Deferred Criteria Not Covered By This Sprint
- No new endpoint, schema, or connector-scope expansion.
- No UI redesign or web-route changes.
- No external load-testing framework or broad performance benchmark suite beyond bounded readiness probes.

## Recommended Next Step
Run `python3 scripts/run_mvp_readiness_gates.py` in reviewer/CI environment and use `docs/runbooks/mvp-readiness-gates.md` as the canonical go/no-go interpretation guide.
