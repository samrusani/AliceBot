# Alice v0.10.0 Independent Review — Sixth Acceptance Pass

## Verdict

**PASS — no P0, P1, or P2 blocker remains in the frozen pass-6 tree.**

The two fifth-review residuals are independently closed. Publication now
requires a strict release-specific repository-control attestation *and* the
separate exact-SHA semantic attestation, and semantic attestation copies now
preserve JSON types recursively. The affected implementation, adversarial
tests, workflow, release documentation, static gates, and handoff evidence are
consistent.

This is code-review acceptance, not authorization to publish from the current
dirty tree. Release still requires a clean committed candidate SHA, successful
checks on that exact SHA, truthful fresh external-control readback, and the
protected PostgreSQL/pgvector semantic artifact described below. No commit,
push, merge, tag, workflow dispatch, credential handling, release, or
publication occurred during review. Cybersecurity remained explicitly outside
scope.

## Reviewed identity and scope

- Branch: `codex/v0.10-audit-remediation`
- Baseline/current `HEAD`: `68d6bf2f3e76425f5cbd13a73411a3231dffba02`
- Candidate form: remediation remains uncommitted; there is no final candidate
  SHA yet.
- Tracked diff: 186 files, 16,750 insertions, 4,189 deletions.
- Non-ignored untracked scope: 34 files.
- Sixth-pass review scope: the two fifth-review residuals and their affected
  workflow, tests, release tooling, control documentation, and handoff truth.
- `git diff --check`: passed.

The reviewer modified only this report. Production code, tests, workflows,
configuration, and all other documentation remained untouched during review.

## Findings

### P0

None.

### P1

None.

### P2

None.

## Fifth-review residual closure

### Repository release controls — closed

`publish-pypi.yml` now requires the credentialless
`ALICE_RELEASE_CONTROLS_ATTESTATION` before release work and validates its
complete structured value before release verification, semantic artifact
resolution, build, or publication. The contract is bound to the exact
repository, event SHA, and stable tag. It accepts only canonical second-
precision UTC timestamps, rejects future/stale/expired or over-24-hour
validity, closes both object schemas, and requires all 11 documented controls
to be the JSON boolean `true`:

- protected PyPI environment, required reviewers, and restricted deployment;
- protected `main` with strict required checks;
- protected stable tags and immutable releases;
- trusted publishing with no long-lived PyPI credential;
- exposed provider credential revocation; and
- exact-SHA release checks.

Strict parsing rejects duplicate keys, nonstandard numbers, oversized input,
missing/unknown fields, wrong identity, malformed timestamps, false controls,
and boolean-confusable values. Diagnostics report only generic contract
failures; they do not print the raw payload, unknown field names, or values.

The semantic gate remains independently mandatory. The workflow resolves a
successful `semantic-release-gate.yml` dispatch for the exact head SHA,
downloads the exact SHA-named artifact from that run, validates its semantic
attestation, and only then builds. Neither attestation can satisfy the other
gate. The publish job depends on the verified build job, downloads the current
SHA-named distribution artifact, rechecks checksums, isolates only wheel and
sdist files, and uses protected-environment trusted publishing. Permissions
are read-only except for the publish job's required `id-token: write`.

Independent evidence:

- 64 validator tests passed.
- An independent direct sweep rejected 157 adversarial claims and accepted
  only two legitimate claims: the ordinary valid payload and the exact
  24-hour validity boundary.
- The sweep covered all missing top-level fields; unknown top/control keys;
  every missing, false, and seven type-confusable variants for each control;
  identity drift; malformed, duplicate, nonstandard, recursive, and oversized
  JSON; invalid expected workflow identities; and timestamp/freshness drift.
- 18 independent workflow structure, ordering, independence, artifact, and
  permission assertions passed.
- Failure-output tests confirmed that neither payload data nor injected
  key/value text is echoed.

### Semantic attestation JSON type fidelity — closed

Every value copied from the semantic report is now compared through recursive,
type-sensitive canonical equality: report digest, generation time, suite,
status, nested embedding signature, backend, retrieval mode, vector candidate
count, vector-stage participation, and paraphrase recall. Independent shape
checks also require a positive non-boolean integer candidate count, exactly
boolean `true` participation, and a finite float recall in the closed 0..1
range.

Independent production-generator-backed evidence:

- The positive report produced six passing suites and all 78 canonical cases.
  Report validation, attestation writing, and final artifact validation each
  returned zero issues.
- All five fifth-review substitutions rejected:
  `48 -> 48.0`, `true -> 1`, `true -> 1.0`, `1.0 -> 1`, and
  `1.0 -> true`.
- 102/102 recursive copied-node wrong-type mutations rejected.
- 16/16 same-type scalar drifts, 15/15 boolean/non-finite numeric drifts,
  2/2 unknown-key mutations, and 15/15 missing-key mutations rejected.
- Five paired report-and-attestation substitutions still rejected after
  recomputing the report digest and byte-level SHA-256.
- No validator crash occurred.

The fifth-review defect could not forge the underlying report verdict, but it
did violate exact typed-copy fidelity. That bounded integrity gap is now
closed without weakening the strict 78-case report contract.

## Independent verification

| Check | Result |
|---|---|
| Six affected Python test files | **219 passed** |
| Repository-control/workflow/control-doc lane | **88 passed** |
| Release-check and vNext semantic modules | **131 passed** |
| Real generated semantic report → attest → validate | **PASS**, six suites / 78 cases / zero issues |
| Exact five semantic type substitutions | **5/5 rejected** |
| Recursive semantic copied-node drift matrix | **102/102 rejected** |
| Independent repository-control mutation sweep | **157 rejected; two valid boundary claims accepted; zero workflow-relevant crashes** |
| Independent publish-workflow assertions | **18 passed** |
| `make release-static` | **PASS**: control-doc truth, release metadata, Ruff, normal mypy over 134 files |
| Publish and semantic workflow YAML parsing | **PASS** |
| `git diff --check` | **PASS** |

Builder package evidence was also reviewed: the fresh isolated pass-6 wheel
and sdist passed Twine, repository distribution validation, and both installed-
artifact smokes. Their README metadata surfaces each contained 28 Markdown
targets and zero relative targets. The recorded hashes correctly identify
dirty-tree verification artifacts only and are not presented as publishable
release bytes.

## Test-strength and documentation assessment

- The release-control tests execute the validator; they do not merely search
  for workflow strings. They exercise strict parsing, every required control,
  exact identity, time boundaries, failure output, and the executable JSON
  example in `RELEASING.md`.
- Workflow regression tests separately locate and assert both attestation
  gates, their ordering, exact inputs, and non-substitution. The restored gate
  is a strict strengthening of the baseline permanent `v1` flag.
- Semantic regressions use the real six-suite generator-backed fixture and
  include the exact reviewer reproductions plus systematic recursive drift.
- `RELEASING.md` accurately distinguishes operator readback from authenticated
  live settings inspection, documents the closed credentialless contract, and
  requires both independent evidence lanes for the same release identity.
- `BUILD_REPORT.md`, `FIX_MATRIX.md`, and `ENGINEER_HANDOFF.md` accurately
  preserve the builder's pre-review state and do not claim self-approval. This
  report is the authoritative sixth-review verdict and supersedes their
  time-relative “sixth review pending” wording; their external release gates
  remain active.
- Historical pass-3 broad counts are clearly separated from pass-6 affected-
  lane reruns. The handoff does not falsely claim that the full 2,497-unit or
  418-test PostgreSQL suites were rerun after pass 6.
- Desloppify results remain correctly labeled as a mechanical inventory with
  unassessed subjective dimensions and reduced-confidence security scanning,
  not as this review's release verdict or a cybersecurity assessment.

## Main-engineer release conditions

The repaired code and handoff are accepted, but the engineer must not publish
until all of these operational conditions are satisfied:

1. Commit the accepted tree and establish one clean candidate SHA; rerun all
   required checks on that exact SHA.
2. Create the intended annotated stable tag only through the documented
   protected release path and verify it resolves to the exact protected
   `main` head.
3. Read back the external GitHub/PyPI controls and populate the fresh closed
   repository-control attestation for that exact repository/SHA/tag. Remove or
   replace it immediately if control state changes.
4. Run the protected `semantic-release` workflow for the same SHA with the
   real configured provider and PostgreSQL/pgvector; inspect the credential-
   free six-suite/78-case report and attestation.
5. Require both attestations. Do not bypass one because the other is valid.
6. Publish only the workflow-built, tested, checksum-verified wheel and sdist;
   never rebuild between verification and publication.

Subject to those external and exact-candidate gates, the pass-6 remediation is
ready for main-engineer handoff.
