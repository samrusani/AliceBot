# Alice v0.11.0 Phase 1 Engineer Handoff

## Start here

This is an uncommitted Phase 1 candidate based on
`8520f29d3812aa95a75d192fdaf897e5d099a29a`. Both governed version sources are
already `0.11.0`; do not bump them again. The builder did not stage, commit,
push, tag, or publish anything.

Review in this order:

1. `SURFACE_INVENTORY.md` for the governing pre-edit disposition and count
   reconciliation.
2. `FIX_MATRIX.md` for the implementation boundary and proof by surface.
3. `surface_flags.py` and the mount filtering in `main.py`; verify exact flag
   semantics before reviewing individual compatibility handlers.
4. The permanent-operation inventory and physical cleanup in
   `openapi_operation_contracts.py`, then the OpenAPI tests.
5. `local_workspace.py`, local bootstrap handlers, provider handlers, and the
   rewritten provider integration carrier.
6. `vnext_connectors.py` and the web Telegram carrier, especially the required
   raw-update payload, explicit allowlist, pre-fetch rejection, and exact
   historical-config normalization.
7. MCP/CLI/worker registries and their exact inventory tests.
8. Web route deletion, the server-only legacy resolver, shell navigation, and
   four browser postures.
9. The exact 14-module/12-TypedDict/model-pack public-name guards, the dead
   limiter carrier guard, and lazy `proxy_execution` import posture.
10. Test/readiness/validation carrier retirements, the bounded active sprint
    packet, and the non-operational Phase 2/3 closeout archive replacement.
11. Ubuntu packaging and the neutral reference fixture/demo parity.
12. `BUILD_REPORT.md` and its frozen-tree receipt, then the reviewer-owned
    `REVIEW_REPORT.md` when available.
13. The D3 production-startup correction in `config.py`, `validate_env.sh`, and
    the health payload, then its focused fail-on-old tests and superseding
    receipt. The existing review report refers to the prior carrier until the
    independent reviewer reseals it.

## High-risk review points

- `ALICE_LEGACY_SURFACES` is exact and case-sensitive: only the literal `1`
  mounts HTTP compatibility and enables worker task ticks. Leading/trailing
  whitespace and values such as `true`, `yes`, or `on` fail closed. It is read
  at process import/start; changing it requires restarting affected API,
  worker, and web processes.
- `ALICE_MCP_LEGACY_TOOLS` retains its documented case-insensitive
  `1/true/yes/on` parser. Agent-key-bound MCP ignores both expansion paths and
  remains exactly eleven tools.
- The legacy HTTP set is frozen at module import. Tests use isolated processes;
  runtime mutation of the environment must not alter an already-mounted app.
  A default process must also leave `alicebot_api.proxy_execution` unloaded;
  flag-on mounts approval execution but imports the module only on invocation.
- The 63 permanent HTTP deletions must remain disjoint from both the 182
  default and 231 compatibility-enabled OpenAPI inventories.
- Telegram is not a channel transport. Its only retained path accepts supplied
  update objects plus an explicit chat allowlist. Generic sync, polling, token,
  secret, webhook, and delivery paths must stay absent or rejected before side
  effects. Historical config must not expose unknown top-level token/poll keys.
  The web must not synthesize an empty sync call, and the Ubuntu template must
  not advertise bot-token or webhook-secret configuration.
- `POST /v1/workspaces/bootstrap` is the only workspace creator. Provider
  routes must fail before bootstrap and must not recreate hosted workspace,
  session, device, membership-administration, or bearer-auth seams.
- Hosted-era provider rows are not reassigned to the deterministic local
  workspace. Re-register providers after upgrading; migration or adoption of
  those orphaned rows is outside this carrier.
- A core-only production process must boot without `S3_ACCESS_KEY` and
  `S3_SECRET_KEY`. Local identity, role-separated database URLs, and CORS
  deployment validation remain mandatory, and `/healthz` must not echo
  `s3_endpoint_url`.
- The provider/runtime carrier must preserve durable idempotent replay and
  telemetry without reviving model-pack selection or `/v0/responses`.
- The neutral public task-brief contract is `briefing_strategy`. The immutable
  SQL column/store parameter named `model_pack_strategy` is a compatibility
  carrier only and must not reappear in public payloads, CLI arguments, docs,
  reference annotations, or the handoff fixture.
- `_request_client_identifier` is intentionally retained, but the obsolete
  response/entrypoint rate-limiter classes, settings, env, and script carriers
  must remain absent.
- Screenshot and transcript inputs are externally extracted text payloads;
  neither active docs nor rendered UI may claim Alice performs OCR or
  transcription. The retired Phase 2/3 closeout runbooks must not reappear as
  live instructions.
- No historical migration may be changed to make removed tables disappear.
  They remain inert schema history.
- The default web shell has seven views. Approvals, tasks, Gmail, and Calendar
  are the only four server-gated web routes. There is no `NEXT_PUBLIC_*` bypass.

## Reproduce the primary gates

```bash
./.venv/bin/pytest -q tests/unit
./.venv/bin/python -m pytest tests/unit -q \
  --cov=alicebot_api --cov-report=term \
  --cov-report=json:/tmp/alicebot-python-coverage.json --cov-fail-under=50
./.venv/bin/python scripts/check_python_coverage.py \
  --coverage-json /tmp/alicebot-python-coverage.json \
  --path apps/api/src/alicebot_api/main.py --min-percent 45
ALICE_LEGACY_SURFACES=1 ./.venv/bin/pytest -q tests/integration
make release-static
make test-longmemeval
./.venv/bin/python scripts/run_reference_agent_examples_demo.py
```

The integration suite requires role-separated PostgreSQL 16 with pgvector at
least 0.8; set `DATABASE_ADMIN_URL` and `DATABASE_URL` if the local container
is not mapped to port 5432. Web reproduction uses `make test-web` and requires
the Playwright browser setup described in the Makefile.

## Working-tree and receipt rules

- Preserve user-owned untracked `coverage.json` and `uv.lock`; they are not
  candidate evidence and are excluded from the receipt.
- Do not create `REVIEW_REPORT.md` until the independent reviewer has reviewed
  the exact receipt in `BUILD_REPORT.md`.
- Any edit after the recorded receipt invalidates the receipt. Rerun the
  affected gates, reconstruct the manifest twice, update `BUILD_REPORT.md`,
  and request review of the new digest.
- D2's flag-off default-surface integration smoke belongs to Phase 2. Do not
  add that workflow job while finalizing or reviewing this Phase 1 carrier.
- Keep `docs/handoff/2026-07-14-v0.10.4-remediation/` and immutable v0.10.x
  release records untouched.

## After approval

The release engineer may commit this uncommitted tree, merge through the normal
protected-main flow, and run required CI and semantic evidence on the resulting
final SHA. Only that exact green SHA may be tagged. Phase 2 starts in a later,
separately reviewed increment; do not fold it into release finalization.
