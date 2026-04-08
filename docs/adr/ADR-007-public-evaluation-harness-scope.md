# ADR-007: Public Evaluation Harness Scope

## Status

Accepted (2026-04-08)

## Context

`P9-S37` needs reproducible evidence that importer-expanded continuity data improves useful recall/resumption outcomes and remains correction-aware. Prior retrieval evaluation fixtures exist, but importer and correction posture claims require a sprint-specific harness with fixture-backed import replay.

## Decision

Define the `P9-S37` public evaluation harness scope as local, fixture-backed, and command-driven:

- shipped command: `./scripts/run_phase9_eval.sh`
- shipped fixture inputs: OpenClaw, Markdown, and ChatGPT fixture sources in-repo
- shipped report outputs: JSON reports under `eval/reports/` and committed baseline under `eval/baselines/`
- required measured metrics:
  - importer success rate
  - duplicate-memory posture rate
  - recall precision-at-1 on importer-scoped queries
  - resumption usefulness rate (decision + next-action usefulness in scoped briefs)
  - correction effectiveness rate (supersede correction changing top recall result)

Harness scope is intentionally local-first and deterministic. It does not include hosted telemetry, external benchmark providers, or remote evaluation infrastructure.

## Consequences

Positive:

- quality claims are reproducible from documented commands and repo-local fixtures
- importer and correction outcomes are measured together, not in isolated success-only checks
- launch docs in `P9-S38` can cite committed baseline evidence directly

Negative:

- harness results are scoped to local deterministic fixtures, not production traffic variation
- broader benchmark dimensions remain deferred beyond `P9-S37`

## Alternatives Considered

### Keep only retrieval fixture evaluation without importer replay

Rejected because it would miss importer success/duplicate posture and correction-aware continuity evidence required by sprint acceptance.

### Build hosted benchmark infrastructure in `P9-S37`

Rejected because hosted evaluation is out of scope and would delay shipping deterministic local evidence.
