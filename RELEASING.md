# Releasing Alice

`v0.9.4` is the latest published release. `v0.10.0` is an unshipped
development candidate until the procedure below completes on one exact clean
commit and an independent reviewer reports no blocker. Preparing a candidate
does not authorize a tag, GitHub release, or PyPI upload.

## One Release Identity

`pyproject.toml` is the canonical package-version source. The API and Python
entrypoints read the installed distribution metadata. The release check also
requires the private web package and active control documents to agree with
the candidate version.

A stable publication uses all of the following on the same commit:

- package version `X.Y.Z`;
- annotated Git tag `vX.Y.Z`;
- non-draft, non-prerelease GitHub release `vX.Y.Z`;
- wheel and sdist metadata version `X.Y.Z`.

## Manual Repository Prerequisites

Before publishing, configure these controls in GitHub and verify them by
readback:

1. Protect the `pypi` environment with required reviewers and a deployment
   branch policy limited to `main` or protected branches.
2. Keep the required `main` status checks strict — tests, security scans, and
   the protected-path guardrail — so no release commit reaches `main` without
   passing them. This is a single-maintainer repository: the maintainer merges
   release pull requests by administrative merge after those checks pass, which
   is the audited release route. The controls below gate *what publishes*, not
   *who approves the merge*. Keep `main` branch protection enabled as well.
3. Protect stable `v*` tags from mutation or deletion.
4. Enable immutable GitHub releases for the repository.
5. Configure PyPI trusted publishing for this repository, the pinned publish
   workflow, and the protected `pypi` environment. Do not store or use a
   long-lived PyPI upload credential.
6. If a provider credential has ever been exposed in a local file or terminal
   transcript, revoke and replace it at the provider. Do not paste or print the
   old or replacement value while checking that local `.env` files remain
   ignored by Git.
7. Immediately before publishing, after the exact stable tag exists, verify
   items 1-6 by readback for that tag and commit. Then set the repository
   variable `ALICE_RELEASE_CONTROLS_ATTESTATION` to the credentialless JSON
   contract below. Publication fails closed when the variable is missing,
   malformed, expired, stale, names another repository, tag, or SHA, omits a
   control, adds an unknown claim, or contains any control value other than
   JSON `true`. Remove it immediately if the verified state changes.
8. Protect a separate `semantic-release` environment. Configure
   `ALICE_RELEASE_EMBEDDINGS_BASE_URL` as an environment secret,
   `ALICE_RELEASE_EMBEDDINGS_MODEL` as an environment variable, and (when the
   provider requires it) `ALICE_RELEASE_EMBEDDINGS_API_KEY` as an environment
   secret. Dispatch `semantic-release-gate.yml` on the exact candidate SHA.
   The workflow uploads a credential-free report and attestation named with
   that SHA. Publication fails closed unless it can resolve a successful gate
   run, download that exact artifact, and validate its source SHA, report
   digest, passing suite set, Postgres backend, and positive signed-vector
   candidate count.

Use this exact closed shape for the repository variable, replacing every
placeholder with the release-specific value. `verified_at` must not be in the
future or more than 24 hours old. `expires_at` must be later than `verified_at`
and the current time, with a validity window no longer than 24 hours.

```json
{
  "schema_version": "alice_release_controls_attestation_v1",
  "repository": "OWNER/REPOSITORY",
  "release_sha": "40_lowercase_hex_characters",
  "release_tag": "vX.Y.Z",
  "verified_at": "YYYY-MM-DDTHH:MM:SSZ",
  "expires_at": "YYYY-MM-DDTHH:MM:SSZ",
  "controls": {
    "pypi_environment_protected": true,
    "pypi_required_reviewers": true,
    "pypi_deployment_policy_restricted": true,
    "main_branch_protected": true,
    "main_required_checks_strict": true,
    "stable_tags_protected": true,
    "immutable_releases_enabled": true,
    "trusted_publishing_enabled": true,
    "no_long_lived_pypi_credentials": true,
    "exposed_provider_credentials_revoked": true,
    "exact_sha_release_checks_required": true
  }
}
```

This variable contains claims only; credentials, endpoints, and tokens never
belong in it. The repository-control attestation and exact-SHA semantic
attestation are independent mandatory gates. Neither is evidence for, or a
substitute for, the other.

The workflow cannot create these repository settings itself. An unprotected
PyPI environment is a release blocker even when the YAML is correct.

## Candidate Gate

Run from a clean checkout whose exact SHA is the intended `main` head:

```bash
make setup
make setup-browser
make migrate
make release-check DIST_DIR=dist
```

`make setup-browser` is an idempotent local prerequisite that installs the
Playwright-managed Chromium binary. It intentionally does not pass
`--with-deps`: that option invokes Linux system-package installation and is not
appropriate on macOS. `make test-web` also declares this prerequisite so a
direct local web-gate run cannot skip it. On a clean Debian or Ubuntu release
host, substitute the guarded `make setup-browser-linux` target; it installs
Chromium plus the required Linux runner packages and refuses to run on macOS.
The Linux CI job uses the same `setup:browser:linux` package script.

`make migrate` must target a disposable release-candidate database or a live
database that has a current, restore-tested backup. PostgreSQL verification
uses separate admin and application URLs: the admin role installs `pgvector`,
creates/grants the application role, and runs Alembic; runtime and isolation
tests use the non-superuser application role. Never point this gate at an
unbacked production database.

The gate performs correctness-only Python linting, normal cross-module mypy
over the complete first-party production/release-tool surface, unit coverage,
PostgreSQL integration tests, every model-free LongMemEval test, and the
offline evidence replay. Web gates include units, core plus vNext per-file coverage,
TypeScript, lint, the production build, navigation/axe/outage browser
tests, and bundle budgets. It also builds both distributions, runs Twine, and
tests the installed wheel/sdist across all four public entrypoints. It first
fetches `origin/main`, and writes `dist/SHA256SUMS` only after both artifacts
pass.

The release regression surface also treats every advertised MCP JSON Schema
keyword as an executable pre-handler contract. RFC 3339 full dates must be
both syntactically and calendrically valid, unsupported advertised formats
fail closed, and numeric confidence fields reject booleans and non-finite
values as well as values outside their declared 0..1 interval. Durable SQLite
and PostgreSQL rollback tests prove representative invalid corrections do not
partially mutate review state.

The gate also runs the canonical retrieval-quality eval with `--release-gate`.
That flag fails closed: a run that never exercises the vector stage reports
`pass_fts_only` and exits non-zero, so the gate cannot go green without
measuring semantic/paraphrase retrieval quality. Point
`ALICEBOT_EVAL_DATABASE_URL` at a `pgvector` database and set the
`ALICE_EMBEDDINGS_*` provider variables before running `make release-check`;
the default in-memory SQLite URL exists only as a fail-closed smoke. The report
must prove that production-compatible signed vectors produced a nonzero vector
candidate count; merely attempting a vector stage is not evidence. CI runs the
no-provider path on purpose and asserts it fails closed — ordinary CI green is
not the semantic release gate.

The configured semantic run writes an attested report containing the exact Git
SHA, suite configuration, and a structured `embedding_signature` copied from
the signed vector writes. That identity contains its schema/signature versions,
the non-secret provider and model labels plus their SHA-256 fingerprints, and
the existing 16-hex endpoint fingerprint; it never contains a raw endpoint URL
or API key. The report digest binds this identity, and the attestation must copy
it exactly. Validation also derives and reconciles the canonical suite order
and titles, nonempty case lists with all 78 canonical identities, exact
generator-owned query/target linkage, acceptance targets and target-check
keys, known corpus digests, and Postgres backend evidence for every suite.
Suite and case metrics, evidence, retrieval subsets/latencies/seeding, graph
ranks, and control objects are recursively closed and type checked; numeric
values must be finite, non-boolean, and in their declared ranges. Rank-derived
case metrics and suite/subset aggregates must reconcile with the reported
evidence. Executed/skipped counts, pass/fail counts, pass rate, and report/
summary status are derived and reconciled as well. Unknown fields and
recursively detected credential-bearing keys or values are rejected in both
report and attestation. A provider-free release-gate run fails for missing
configured semantic evidence, not because a validator/provider mismatch
fabricates a digest failure.
The canonical `report_digest` is a `sha256:<hex>` digest over every semantic
report field except its wall-clock timestamp and the digest itself. The
attestation's separate bare `report_sha256` is the byte-level transport hash of
the report file. The publish workflow accepts only a verified report artifact
whose SHA equals the release tag commit. Credentials remain operator-supplied
and are never stored in repository files or ordinary CI variables. A
deterministic test provider is valid for regression tests, not for a public
release attestation.

CI must pass on the exact candidate SHA. Do not treat a green parent commit,
branch name, or locally rebuilt artifact as equivalent evidence.

## Tag And Publish

Before the finalization commit, move the candidate entries out of `Unreleased`
under a dated `## vX.Y.Z — YYYY-MM-DD` heading. Change the release-note title
from `Release Candidate Notes` to `Release Notes`, replace the candidate-status
paragraph, and remove `not published yet`. This finalizes the release text
without claiming that publication has already happened.

The release notes must carry exactly one machine-readable state comment on
physical line 2, immediately under the exact title. It must not appear inside
a code fence or anywhere else in the release-notes file:

```html
<!-- alice-release-state: {"schema_version":"alice_release_document_state_v1","version":"X.Y.Z","publication_status":"pending","checksums_status":"pending"} -->
```

The finalization check reads this structured state, not prose keywords. Keep it
`pending` on the tag. The evidence-backed post-publication commit changes the
two statuses to `published` and `recorded` after the checksums file exists.

Only after that finalization commit is merged and the prerequisites above are
verified:

1. Confirm the checkout is the exact remote `main` head and the worktree is
   clean.
2. Run `make release-finalization-check`. It rejects stale changelog or
   release-note candidate state.
3. Create an annotated `vX.Y.Z` tag on that SHA. Lightweight tags are rejected.
4. Run `python scripts/release_check.py --tag vX.Y.Z --expected-sha SHA
   --require-main-head --require-clean`; the publish workflow repeats the same
   identity check on the release event.
5. Read back the external controls again and set the release-specific
   `ALICE_RELEASE_CONTROLS_ATTESTATION` for that repository, tag, and SHA with
   fresh `verified_at` and `expires_at` values.
6. Confirm the protected semantic gate succeeded on that exact SHA and inspect
   its credential-free report and attestation artifact.
7. Create a non-draft, non-prerelease GitHub release from that tag.

The `Publish to PyPI` workflow then:

- rejects a prerelease or mismatched tag;
- rejects a missing, invalid, stale, wrong-repository, wrong-tag, wrong-SHA, or
  incomplete repository-control attestation;
- independently rejects missing exact-SHA semantic report/attestation evidence
  or release documents whose structured publication/checksum state is
  inconsistent;
- rejects a lightweight tag;
- requires the tag commit to equal the exact `origin/main` head;
- rejects a version already present on PyPI;
- builds the wheel and sdist once;
- tests those exact bytes and records their SHA-256 digests;
- publishes the downloaded, checksum-verified artifacts through the protected
  `pypi` environment.

Never rebuild between verification and publication. PyPI files are immutable;
if a publication partially succeeds, diagnose the published state and issue a
new patch version rather than reusing the version.

## After Publication

Verify the GitHub release, a clean install from PyPI, and the published file
hashes against PyPI's integrity attestations (which bind each file to this
repository, the tag, the workflow, the exact commit, the release event, and
the `pypi` environment). Because immutable releases cannot take assets after
publication, the durable checksum record lives in the repository: record the
published wheel and sdist SHA-256 digests in
`docs/release/vX.Y.Z-checksums.txt` as part of the post-publication commit,
which also updates remaining active control-document status language to say
the version is published. That truth change is a separate, evidence-backed
commit; the tagged changelog and release notes were already finalized before
the tag and must not have claimed publication early.
