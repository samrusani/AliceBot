# BUILD_REPORT

## sprint objective
Turn the shipped Phase 14 platform surface into tracked design-partner usage proof through partner objects, workspace linkage, onboarding/support artifacts, structured feedback, usage summaries, and a partner success dashboard.

## completed work
- added hosted-admin design-partner API support for create, list, detail, patch, workspace linkage, feedback intake, and dashboard views
- added Phase 14 database tables for `design_partners`, `design_partner_workspaces`, and `design_partner_feedback`
- connected partner usage summaries to existing `provider_invocation_telemetry` linked through partner workspaces
- added sprint-scoped launch artifacts under `docs/design-partners/`
- replaced placeholder launch-set docs with an anonymized tracked pilot packet and a case-study candidate artifact for the canonical launch set
- tightened dashboard readiness to require actual usage evidence and captured feedback instead of proxy linkage signals
- added targeted unit and integration coverage for migration shape, route registration, admin access, linkage, feedback validation, usage summaries, and dashboard acceptance signals

## incomplete work
- none

## files changed
- `apps/api/src/alicebot_api/main.py`
- `apps/api/src/alicebot_api/design_partners.py`
- `apps/api/alembic/versions/20260416_0065_phase14_design_partner_launch.py`
- `tests/integration/test_phase14_design_partner_launch_api.py`
- `tests/unit/test_20260416_0065_phase14_design_partner_launch.py`
- `tests/unit/test_main.py`
- `RULES.md`
- `docs/design-partners/README.md`
- `docs/design-partners/onboarding-runbook.md`
- `docs/design-partners/support-checklist.md`
- `docs/design-partners/canonical-launch-set.md`
- `docs/design-partners/case-study-template.md`
- `docs/design-partners/pilot-evidence.md`
- `docs/design-partners/case-study-candidate-finops-console.md`

## tests run
- `python3 scripts/check_control_doc_truth.py`
- `./.venv/bin/python -m pytest tests/unit/test_control_doc_truth.py -q`
- `./.venv/bin/python -m py_compile apps/api/src/alicebot_api/design_partners.py apps/api/src/alicebot_api/main.py tests/integration/test_phase14_design_partner_launch_api.py tests/unit/test_20260416_0065_phase14_design_partner_launch.py tests/unit/test_main.py`
- `./.venv/bin/pytest tests/unit/test_20260416_0065_phase14_design_partner_launch.py tests/unit/test_main.py -q`
- `./.venv/bin/pytest tests/integration/test_phase14_design_partner_launch_api.py -q`
- `./.venv/bin/pytest tests/unit/test_20260416_0065_phase14_design_partner_launch.py tests/unit/test_main.py tests/integration/test_phase14_design_partner_launch_api.py -q`

## blockers/issues
- none

## recommended next step
- keep the weekly pilot review moving, advance `dp-finops-console` from case-study candidate toward drafting, and only count reserve partners once linkage, usage evidence, and structured feedback are present
