# Post-v0.10.2 Audit Remediation Matrix

Cybersecurity was explicitly excluded. “Builder closed” means the change and a
focused regression exist; independent review remains a separate release gate.

| Area | Audit failure | Builder status | Correction and evidence |
|---|---|---|---|
| Response generation | Retries and crashes could duplicate user turns and provider charges | Builder closed | Durable `response_generation_jobs`, mandatory caller idempotency keys, request fingerprints, leases, replay, terminal fencing, and fail-closed unknown outcomes; focused API/store/migration suites pass |
| Provider transactions | Provider discovery, testing, invocation, Telegram polling, local-folder traversal, embeddings, and scheduled generation held database transactions | Builder closed | External work is performed between short transactions; provider and scheduler results use revision/token CAS; HTTP connector regression observes connection depth zero during I/O |
| Deferred embeddings | Provider work remained inside review, consolidation, project-review, CLI/MCP, backfill, and SQLite reindex transactions | Builder closed | Every adapter snapshots in a short read transaction, calls the provider with no database context open, then uses a separate best-effort persistence transaction; explicit depth regressions cover HTTP, MCP, CLI, project service, backfill, and SQLite batches |
| Review concurrency | Project accept/edit/reject could race and leave contradictory state | Builder closed | Locked artifact/memory/project reads plus status CAS; project value, summary, confirmation, and candidate metadata transition together |
| Artifact lifecycle | Promoted artifacts could later be rejected or archived | Builder closed | Explicit locked transition table rejects invalid terminal transitions |
| Project scope | Canonical multi-project scope was discarded or widened through stale legacy values | Builder closed | Canonical scope is preserved and overlap-aware throughout retrieval, automation, artifacts, memories, and loops; key presence is authoritative, so explicit `project_scope: []` suppresses singular and nested legacy fallbacks |
| Scheduler | Advisory-lock execution held connections, lacked durable claims, reported failures as success, and used unstable macOS ownership identity | Builder closed | Durable claim/lease/heartbeat/version fence, external execution, fenced finalize/reaper, nonzero failure exits, stable ownership token, and fail-closed SQLite boundary |
| OpenAPI | Success responses used an arbitrary JSON catch-all or incorrect property types | Builder closed | All 294 operations now have named success contracts with source-verified property types; status codes include conditional 200/201, 201/207, 200/202, and 200/503 cases |
| Release recovery | PyPI success followed by GitHub failure was unrecoverable; release prose could remain pre-publication | Builder closed | Verified draft is staged before PyPI; exact-byte asset validation and `finalize-existing-draft` / `resume-pypi-and-finalize` modes recover safely; neutral body is rendered structurally |
| Workflow idempotency | Daily/weekly, connection, and contradiction artifacts or edges could duplicate | Builder closed | Deterministic logical digests exclude volatile run/trace identifiers; backend uniqueness and atomic upsert/get-or-create cover PostgreSQL and SQLite, with migration 0089 fencing graph-edge publication |
| CLI/MCP startup | Environment-only local startup invoked unrelated hosted validation | Builder closed | Local environment validation is scoped to the selected runtime |
| Exit semantics | Failed queue tasks and scheduler runs could exit zero | Builder closed | CLI and daemon one-shot paths propagate failed status as nonzero with an error summary |
| Provider parsing | Non-UTF payloads, malformed embedding indices, and invalid reranker scores escaped or corrupted ordering | Builder closed | Typed decode failures, exact index permutations, finite integer score range, and fail-open reranking regressions |
| Retrieval completeness | Inferred domains became destructive filters; scoped supplemental stages and chunk parents truncated before scope/deduplication | Builder closed | Inference is ranking-only, scoped predicates precede limits, related rows bulk-load, and distinct parent-source ranking prevents long-document crowding |
| Embedding persistence | Store write failures violated the best-effort contract | Builder closed | Operational persistence failures return a contained false result without swallowing cancellation/base exceptions |
| ChatGPT import | Conversation time semantics and stable conversation identity were not persisted | Builder closed | One source per conversation with stable identity, source timestamps, role/order/repetition preservation, aggregate batch results, and no raw JSON duplication |
| Trace/telemetry scale | Source traces scanned full corpora; artifact traces sampled the newest sources; policy telemetry was unbounded | Builder closed | Targeted source-reference/event queries, exact source-ID loading, artifact-targeted events, and bounded agent policy readers |
| Migration operations | Persistence indexes and repair/validation were not online-safe | Builder closed | Concurrent indexes, bounded/deferred repair boundary, and deferred validation in migration 0087 |
| Provider fence compatibility | Raw legacy provider inserts failed the new fingerprint constraint; raw changes could bypass stale-discovery fencing | Builder closed | Migration 0088 supplies valid default fingerprints and advances revision/fingerprint on raw configuration changes; app-provided CAS tokens remain authoritative |
| Packaging/CI | Compatibility installs drifted; one wheel smoke reintroduced checkout source | Builder closed | Pinned build/test tooling, isolated installed-wheel process, byte-reproducible wheel/sdist checks, and packaged migration verification |
| Documentation | Active docs contained stale release and implementation claims | Builder closed | Control-doc checker resolves the published baseline and active docs distinguish immutable v0.10.2 from unreleased remediation |

## Independent-review correction pass

The first independent review requested the following additional corrections.
All are builder-closed on the current dirty tree and were included in the
final independent **APPROVE** verdict.

| Priority | Review finding | Correction and focused evidence |
|---|---|---|
| P1 | Scheduler provider work could publish domain rows before a live claim was atomically finalized; manual runs also crossed the provider-I/O boundary | Every workflow now executes against a read-through staged store, then publishes artifacts, memories, open loops, edges, revisions, and events only inside the short transaction that locks/revalidates the exact claim fence and finalizes it. Manual PostgreSQL execution uses the same prepare/publish split. Provider failure and forced fence loss leave zero workflow domain rows/events; 5 PostgreSQL adversarial tests pass. |
| P1 | Runtime replay and provider credential/network work occurred in the wrong order or transaction boundary | Terminal response jobs replay immediately after auth/workspace resolution and before provider/model-pack reads, DNS, secrets, or adapter resolution. Provider secret files are staged outside database transactions, write context and provider revision/fingerprint are revalidated, and failed database writes compensate the staged secret. Focused replay and transaction-depth regressions pass. |
| P1 | GitHub release bodies were extracted through a lossy text path | The workflow stores the GitHub JSON response, decodes the body string with the repository helper, and byte-compares it before PyPI, normal finalization, and both recovery modes. Trailing line feeds and multiline bodies are preserved exactly. |
| P1 | Migration 0087 could not reliably resume after partially committed DDL or an invalid concurrent index | Columns and constraints are retry-safe; a named invalid index is detected in the catalog, dropped concurrently, and rebuilt. The PostgreSQL regression interrupts after committed DDL/index failure, repairs the collision, retries to a valid/ready unique index, and downgrades cleanly. |
| P1 | Migration 0088 broke previous-binary provider writes during rolling deployment | Capability fence columns receive defaults before backfill/`NOT NULL`; previous-binary inserts/upserts work; legacy config updates auto-advance both tokens; current writes must advance revision by exactly one with a changed fingerprint. PostgreSQL migration/provider regressions pass. |
| P1 | Nested legacy project scope could override or union with a canonical scope | Canonical key presence is authoritative, including an explicitly empty scope. Precedence is top-level, then `metadata_json`, then `scope_json`; legacy/nested fields are read only when no canonical key exists. Helper and all audited consumer tests pass. |
| P1 | OpenAPI still routed most successes through seven domain-wide fallback buckets | The seven buckets and their dead factory are removed. The live inventory fails closed unless all 294 operations are covered by 49 typed exact contracts plus 245 literal, uniquely named per-operation contracts. The 49 exact contracts and 67 source-verified literal envelopes are closed; 178 helper-backed envelopes stay explicitly extensible; only two async replay operations are marked polymorphic with individual reasons. All 301 documented 2xx responses and the health 503 have zero broad-bucket references; 67 literal success envelopes were audited with zero missing visible keys. |
| P2 | Raw provider fence tokens could be rewound or changed independently | The migration trigger rejects rollback, revision jumps, fingerprint-only rewrites, and active changes without paired token advancement using SQLSTATE `23514`; persisted state remains unchanged after rejected writes. |
| P2 | Ambiguous or mismatched project automation scope surfaced as a server error | Project automation validation failures now return HTTP 400, with focused endpoint regressions. |
| P2 | Control-document truth checks accepted weak or stale publication evidence | Historical publication evidence must use the supported schema, published/recorded state, and canonical checksum receipt; phrase-first and version-first multiline stale claims are rejected. |
| P2 | Source trace and policy telemetry reads were caller-unbounded or could claim false completeness | Every source-trace collection fetches at most 501, returns at most 500, and reports per-collection truncation plus aggregate completeness. Policy readers clamp direct calls and HTTP input to 200. The 501-row adversarial regression covers all five collections. |
| P2 | Telegram live test/polling and local-folder traversal held CLI or HTTP database transactions | Secret resolution, Telegram polling, and filesystem traversal occur between short read and persist transactions. CLI and HTTP depth-observation regressions pass. |
| P2 | Scheduler idempotency changed when only `agent_run_id` changed | Logical workflow digests recursively exclude volatile `agent_run_id`; daily/weekly replay returns the same artifact across attempts. |
| P2 | A successful daemon scan could retain a stale `last_error_type` | Successful status writes now explicitly clear `last_error_type`; failure paths still persist the current exception type. |

## Final independent-review correction pass

The final review rechecked the prior corrections under concurrency and direct
runtime reproduction. Its bounded findings are closed as follows; the
reviewer's authoritative verdict is in `REVIEW_REPORT.md`.

| Priority | Review finding | Final correction and evidence |
|---|---|---|
| P1 | Canonical scope could widen when an explicitly empty key fell through to stale legacy fields | Top-level and metadata `project_scope` key presence is authoritative, including `[]`; direct helper, retrieval-consumer, SQL-precedence, and PostgreSQL regressions pass. |
| P1 | Generated OpenAPI contracts could preserve property names while assigning incorrect scalar/array types | Per-operation contracts now retain actual integer, boolean, string, array, and object types; the live 294-operation inventory and source-envelope checks pass. |
| P1 | CLI/MCP scheduler run-now paths could hold model/provider work inside a transaction | Both adapters perform policy reads first and call durable run-now only after closing the store context; focused CLI/MCP/scheduler tests pass. |
| P1 | Manual scheduler result bookkeeping could revoke an unrelated live due-run claim | Result-only updates preserve the live claim when bound to the completed run; configuration mutations still revoke it. Real PostgreSQL manual/due isolation passes. |
| P1 | Connection and contradiction retries could duplicate artifacts and edges | Recursive logical digests exclude volatile run/trace identifiers; migration 0089 and atomic edge/artifact upserts provide sequential and concurrent replay. Real PostgreSQL barrier tests publish one artifact and one logical edge set. |
| P1 | Review/consolidation/project/backfill embedding paths still performed provider I/O under locks or transactions | HTTP, MCP, CLI, project service, backfill, and SQLite reindex use read snapshot, provider-at-depth-zero, and separate best-effort persistence phases. The affected 512-test suite and explicit adapter boundary regressions pass. |
| P1 | Provider configuration PATCH used a check-then-update race | Revision plus canonical fingerprint are compared and advanced atomically; concurrent stale writers receive 409. Migration 0088 uses the same canonical fingerprint. |
| P1 | First-party web retries created a fresh idempotency key and did not model HTTP 202 | One logical invocation retains its key across uncertain retries and polls active response jobs until terminal; 55 API-client and 7 composer tests pass. |
| P1 | Control-document checks accepted incomplete or contradictory publication evidence | Historical evidence requires the supported exact schema and canonical checksum receipt; extra states and multiline published/unpublished contradictions fail closed. |
| P2 | Scheduler reaping could mutate a run while reporting zero and omitting its event | Every mutated run is returned and emits the failure event even when a newer workflow fence is preserved. |
| P2 | CLI policy telemetry was unbounded and ignored agent scope | CLI uses bounded, agent-scoped artifact and memory readers with the same cap as HTTP. |
| P2 | Provider validation, Azure auth changes, secret retirement, capability reads, and terminal replay had stale/ambiguous windows | Endpoint addresses validate before commit; Azure mode requires a compatible new credential; secret retirement is reference-aware and ambiguous-commit safe; capabilities join the exact fence; terminal jobs are created/replayed atomically before mutable provider dependencies. |
| P2 | Expected CLI runtime failures escaped as tracebacks | Expected runtime errors are normalized to concise nonzero CLI exits. |
| P2 | Publication and recovery used different frontend build versions | Both paths use the same pinned build toolchain. |
| P2 | Branched ChatGPT imports could select traversal order rather than the true modified timestamp | Conversation timestamps use the minimum valid creation time and maximum valid modification time across the selected branch. |
| P2 | SQLite embedding reindex opened a long-lived write context before provider batches | Each batch closes its read context before embedding and opens a separate persistence context; the two-row `batch_size=1` reproduction observed `[False, False]`. |

## External-only items

These were not mutated by builders and remain release-engineer work:

- read back and update live `MainProtect` required contexts using the exact
  payload-preserving procedure in `RELEASING.md`;
- do not rewrite immutable v0.10.2 assets or body; publish the remediation only
  under a new version and exact candidate SHA;
- correct the historical PyPI v0.9.4 yank explanation only through the
  authorized PyPI operator path, if the project owner still wants that
  metadata repair; and
- run the protected configured semantic gate and repository-control
  attestation for the final clean candidate SHA.
