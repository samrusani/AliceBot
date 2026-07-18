# Alice v0.12.0 Phase 3 Engineer Handoff

## Start here

This is an uncommitted structure-only carrier based on
`f342d45dabe127acca6231f29830ff11d98a340e` (tree
`1d84e26597aecfcd9ad894c6d0b86fbe9a66dfd6`) on branch
`codex/v0120-phase3-structural-refactor`.

**Structure only. Zero behavior change.**

Both governed version sources remain `0.11.1` by design. Do not publish the
candidate-version verification packages. After verifying and committing the
carrier through the protected flow, the release engineer must bump both
governed sources once to `0.12.0`, create fresh release artifacts, and rerun
the exact-SHA release gates.

The builder did not stage, commit, push, tag, publish, or mutate repository
settings. Published v0.10.x/v0.11.x records are unchanged.

## Review order

1. Read `SURFACE_INVENTORY.md` for base/final sizes and stable facades.
2. Read `FIX_MATRIX.md` for each mechanical move and its fail-on-old proof.
3. Inspect `main.py` with `routers/`, then response-hygiene and router-coverage
   controls.
4. Compare `vnext_store.py`/`sqlite_store.py` with the corresponding
   `vnext_stores/postgres/` and `vnext_stores/sqlite/` seams; inspect SQL-shape
   guards before judging formatting differences.
5. Inspect `store.py` with `legacy_store/`, then `contracts.py` with
   `_contracts/`.
6. Inspect `mcp_tools.py` with `mcp/`, then `cli/__init__.py` with `cli/` and
   packaging entrypoints.
7. Read `BUILD_REPORT.md`, reconstruct its receipt, and check the protected
   hashes.
8. Require the independent reviewer-authored `REVIEW_REPORT.md`. The builder
   does not create or pre-approve it.

## High-risk invariants

- `alicebot_api.main:app` remains importable; OpenAPI remains 182 default / 231
  gated / delta 49 with exact contracts.
- `ALICE_LEGACY_SURFACES` conditional mounting remains import-time and requires
  restart; legacy MCP and agent-key gates are unchanged.
- Response hygiene totals 296 calls across the per-module manifest; router
  coverage remains above the 45% aggregate floor.
- PostgreSQL and SQLite store extraction is paired; generated SQL text,
  transaction order, public protocols, and migrations do not change.
- `contracts.py` exports the exact base namespace/order/annotations/metadata.
- MCP remains 11 core / 65 legacy / 76 total, with identical gating, aliases,
  error contracts, and facade namespace.
- CLI parser topology, help, handler defaults, namespace, annotations,
  monkeypatch forwarding, and the `alice`, `alicebot`, and `alice-memory`
  entrypoints remain stable.
- Every production Python file remains below 4,000 lines.
- Package and web version sources remain `0.11.1` until the release cut.

## Local reproduction

Do not invoke `uv`; protected user-owned `uv.lock` and `coverage.json` are not
release inputs. Use the existing direct virtual environment.

```bash
./.venv/bin/python scripts/check_control_doc_truth.py
./.venv/bin/pytest -q tests/unit/test_phase3_handoff_truth.py tests/unit/test_control_doc_truth.py tests/unit/test_protected_path_guardrails.py
make release-static
git diff --check
```

Run the complete unit/coverage and router aggregate commands recorded in the
final `BUILD_REPORT.md`. Re-run the role-separated PostgreSQL legacy-on and
explicit flag-off lanes, LongMemEval/evidence/vector lanes, web unit/coverage/
type/lint/build/budget/browser lanes, and two-root package reproduction when
release input bytes change.

Check untracked whitespace without word-splitting paths:

```bash
untracked_whitespace_failed=0
while IFS= read -r -d '' candidate_path; do
  if candidate_check="$(git diff --no-index --check /dev/null "$candidate_path" 2>&1)"; then
    candidate_status=0
  else
    candidate_status=$?
  fi
  if [ "$candidate_status" -gt 1 ] || [ -n "$candidate_check" ]; then
    printf '%s\n' "$candidate_check"
    untracked_whitespace_failed=1
  fi
done < <(git ls-files --others --exclude-standard -z)
test "$untracked_whitespace_failed" -eq 0
```

`git diff --no-index` returns status 1 for an ordinary content difference, so
status 1 with empty `--check` diagnostics is a clean file. A status above 1 or
any diagnostic text is a failure.

## Receipt reconstruction

Reconstruct the `alice-v0.12.0-phase3-structural-carrier-v1` manifest exactly
as specified in `BUILD_REPORT.md`: byte-sort the union of tracked diff paths
from the base plus untracked paths; exclude exactly `coverage.json`, `uv.lock`,
this handoff's `BUILD_REPORT.md`, and its `REVIEW_REPORT.md`; hash raw file bytes
or symlink targets; retain deletions with base mode. Python and Ruby output must
match byte-for-byte.

Any edit outside those four exact exclusions invalidates the receipt and
requires a new matrix bind and independent review. The reviewer report is
excluded so its author can record the verdict without a receipt loop.

## Copy-ready Upgrade Overview

```md
## Upgrade Overview

### Protected Areas

- [x] memory schema
- [x] continuity APIs
- [x] trust rules

### Compatibility Impact

Structure only. Zero behavior change. HTTP, CLI, MCP, store, and contract code
moves behind stable facades. Route, registry, signature, SQL, packaging, and
entrypoint manifests match the published v0.11.1 base.

### Migration / Rollout

No schema migration, data backfill, or phased rollout is required. Deploy the
single reviewed release artifact through the ordinary protected release flow.

### Operator Action

No data or configuration action is required. Operators using import-time
legacy flags must continue to restart after changing them.

### Validation

Run the full Python, role-separated PostgreSQL in both flag postures, SQLite,
LongMemEval, evidence/vector, OpenAPI, MCP, CLI, web/browser, reproducible-
package, installed-artifact, static, and exact-SHA release matrices recorded in
the Phase 3 handoff.

### Rollback

Redeploy the published v0.11.1 artifact. No migration or data rewrite needs
reversal because this carrier changes structure only.
```

## Release-engineer-only completion

1. Verify the carrier receipt and reviewer report with no unresolved blocker.
2. Commit and merge through the protected flow; record the exact release SHA.
3. Bump package and web version sources from `0.11.1` to `0.12.0` once, then
   finalize `CHANGELOG.md` and the pending release notes.
4. Build fresh v0.12.0 wheel/sdist twice, compare them, install and smoke both,
   and create the canonical checksum receipt.
5. Run all required CI, semantic/vector, repository-control, and CodeQL gates
   on the exact release SHA and verify their provenance.
6. Tag only that approved SHA, create the GitHub Release, publish to PyPI, and
   read back tag ancestry, assets, checksums, provenance, and package metadata.
7. Update active truth only after external state exists. Do not start Phase 4
   from this carrier.

## Deferred item

File a later documentation-truth correction for the pre-existing MCP alias
wording in `docs/alpha/mcp-tools.md`. Do not fold that behavior-description
change into this mechanical carrier.
