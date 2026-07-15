# Core Readiness Gates Runbook

## Objective

Run one deterministic command that verifies the retained v0.11 core: retrieval,
provider runtime, and local bootstrap. The historical filename remains as a
compatibility path; this is not a bundled-chat or MVP acceptance runner.

`scripts/run_phase2_readiness_gates.py` is the canonical implementation.
`scripts/run_mvp_readiness_gates.py` and
`scripts/run_phase3_readiness_gates.py` are compatibility aliases.

## Prerequisites

- Install local dependencies with `make setup` or the equivalent project setup.
- No API keys or running Postgres instance are required for this unit-contract
  runner.

## Exact Command

```bash
python3 scripts/run_phase2_readiness_gates.py
```

The runner executes these fail-closed gates in order:

1. `retrieval_contracts`: deterministic retrieval, evaluation, and stability tests.
2. `provider_runtime_contracts`: retained provider-runtime and AutoGen bridge tests.
3. `local_bootstrap_contracts`: deterministic Alice Lite bootstrap asset tests.

Each gate reports `PASS`, `FAIL`, or `BLOCKED`. The command exits `0` only when
all three gates pass; a failed test command or unavailable runner returns nonzero.

## Deterministic Negative Checks

Use one of these commands to prove the no-go signal:

```bash
python3 scripts/run_phase2_readiness_gates.py --induce-gate retrieval_fail
python3 scripts/run_phase2_readiness_gates.py --induce-gate runtime_fail
python3 scripts/run_phase2_readiness_gates.py --induce-gate local_bootstrap_fail
```

The selected gate exits through the induced-failure path while the other gates
still run. The overall result must be `NO_GO` with a nonzero exit code.

## Broader Validation

`python3 scripts/run_phase2_validation_matrix.py` runs this readiness command,
the retained PostgreSQL integration subset, documentation truth checks, and the
current web matrix. Use that matrix for release-candidate evidence; this narrow
runner is only the fast retained-core readiness layer.

## Compatibility Alias

```bash
python3 scripts/run_mvp_readiness_gates.py
```

The alias delegates to the canonical runner and preserves arguments and exit
semantics. New automation should call the canonical script.
