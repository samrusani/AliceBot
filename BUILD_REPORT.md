# BUILD_REPORT

## sprint objective

Close out Phase 14, promote the public release boundary to `v0.5.1`, and align the canonical docs plus version metadata to the shipped Phase 14 + `HF-001` baseline.

## completed work

- added Phase 14 closeout summary and closeout packet
- added `v0.5.1` release checklist, tag plan, and public release runbook
- updated canonical control docs to treat Phase 14 and `HF-001` as shipped baseline truth
- promoted README and other release-facing docs from the `v0.4.0` boundary to `v0.5.1`
- aligned Python, API, web, CLI, core-package, and Hermes plugin version metadata to `0.5.1`
- switched the active packet into a release-closeout state for the shipped `v0.5.1` boundary

## incomplete work

- full public release gates were not rerun as part of this closeout-doc update
- GitHub release publishing is outside this local repo update unless run separately

## files changed

- `.ai/active/SPRINT_PACKET.md`
- `.ai/handoff/CURRENT_STATE.md`
- `CURRENT_STATE.md`
- `ROADMAP.md`
- `PRODUCT_BRIEF.md`
- `ARCHITECTURE.md`
- `RULES.md`
- `README.md`
- `CHANGELOG.md`
- `pyproject.toml`
- `apps/web/package.json`
- `packages/alice-cli/package.json`
- `packages/alice-core/package.json`
- `apps/api/src/alicebot_api/__init__.py`
- `apps/api/src/alicebot_api/main.py`
- `packages/alice-core/index.js`
- `packages/alice-cli/bin/alice.js`
- `docs/integrations/hermes-memory-provider/plugins/memory/alice/plugin.yaml`
- `docs/quickstart/local-setup-and-first-result.md`
- `docs/integrations/mcp.md`
- `docs/integrations/reference-paths.md`
- `docs/integrations/hermes-bridge-operator-guide.md`
- `docs/npm-publish-quickstart.md`
- `docs/phase14-closeout-summary.md`
- `docs/runbooks/phase14-closeout-packet.md`
- `docs/release/v0.5.1-release-checklist.md`
- `docs/release/v0.5.1-tag-plan.md`
- `docs/runbooks/v0.5.1-public-release-runbook.md`
- `scripts/check_control_doc_truth.py`
- `BUILD_REPORT.md`
- `REVIEW_REPORT.md`

## tests run

- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`

## blockers/issues

- no implementation blocker remains for the closeout/update scope
- full release gates are documented in the `v0.5.1` checklist and runbook but were not rerun in this doc/version-alignment pass

## recommended next step

Use the `v0.5.1` release checklist and tag plan if a full release-gate rerun is desired, otherwise treat this as the accepted release-boundary update for the shipped Phase 14 + `HF-001` baseline.
