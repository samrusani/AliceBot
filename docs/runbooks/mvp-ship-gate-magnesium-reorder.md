# MVP Ship-Gate Runbook: Magnesium Reorder

## Objective
Verify the canonical MVP ship-gate flow remains explicit and bounded:
`request -> approval -> execution -> memory write-back`.

This scenario is first-class in Phase 4 gates via:

- `python3 scripts/run_phase4_acceptance.py`
- `python3 scripts/run_phase4_readiness_gates.py`
- `python3 scripts/run_phase4_validation_matrix.py` (`phase4_magnesium_ship_gate` step)

## Automated Evidence Node

- `tests/integration/test_mvp_acceptance_suite.py::test_acceptance_canonical_magnesium_reorder_flow_with_memory_write_back_evidence`

## Preconditions

- API is running and reachable by `apps/web`.
- `NEXT_PUBLIC_ALICEBOT_API_BASE_URL` is set for `apps/web`.
- API is configured with `ALICEBOT_AUTH_USER_ID` so `/v0/*` requests are server-bound to one authenticated user identity.
- One tool/policy path exists that routes magnesium reorder requests through approval and `proxy.echo` execution.

## Manual Verification: `/approvals`

1. Submit a governed magnesium reorder request so one approval enters `pending`.
2. Open `/approvals` and select the new approval.
3. Confirm `Approval action bar` shows `Approve` and `Reject`.
4. Click `Approve` and confirm status transitions to `approved`.
5. Click `Execute approved request` and confirm execution review renders:
   - execution status
   - request event ID
   - result event ID
6. In `Post-execution memory write-back`:
   - enter memory key `user.preference.supplement.magnesium_reorder`
   - enter JSON value
   - submit
7. Confirm success message reports persisted decision (`ADD`/`UPDATE`) and revision sequence.

## Manual Verification: Embedded `/chat` Workflow Panel

1. Open `/chat` on the same thread.
2. In `Thread-linked workflow`, confirm embedded approval detail shows:
   - existing execution review
   - same `Post-execution memory write-back` control
3. Confirm fixture mode keeps write-back read-only and does not permit submission.

## API Seams Used

- `POST /v0/approvals/{approval_id}/execute`
- `POST /v0/memories/admit`

## Expected Evidence

- Approval created and resolved.
- Execution response includes event evidence (`events.request_event_id`, `events.result_event_id`).
- Memory admission uses execution-linked `source_event_ids`.
- Memory and revision records reflect explicit write-back decisions.

## Out of Scope (Remain Deferred)

- Any automatic memory admission after execution.
- New runtime/task-run schema changes.
- Connector/auth/platform expansion.
- Workflow engine/orchestration redesign.
