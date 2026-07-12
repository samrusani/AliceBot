# Releasing Alice

`v0.9.2` is the latest published release. `v0.9.3` is a release candidate
until the procedure below has completed on one exact commit. Preparing a
candidate does not authorize a tag, GitHub release, or PyPI upload.

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
2. Remove routine admin/bypass paths from the stable release route. Emergency
   bypasses must be explicit and audited.
3. Protect stable `v*` tags from mutation or deletion.
4. Enable immutable GitHub releases for the repository.
5. Keep the required `main` checks strict, including tests, security scans,
   and protected-path guardrails.
6. If a provider credential has ever been exposed in a local file or terminal
   transcript, revoke and replace it at the provider. Do not paste or print the
   old or replacement value while checking that local `.env` files remain
   ignored by Git.
7. After verifying items 1-6 by readback, set the repository variable
   `ALICE_RELEASE_CONTROLS_ATTESTATION` to `v1`. The publish workflow fails
   closed when this attestation is absent or different. Change or remove it if
   the verified control state later changes.

The workflow cannot create these repository settings itself. An unprotected
PyPI environment is a release blocker even when the YAML is correct.

## Candidate Gate

Run from a clean checkout whose exact SHA is the intended `main` head:

```bash
make setup
make migrate
make release-check DIST_DIR=dist
```

`make migrate` must target a disposable release-candidate database or a live
database that has a current, restore-tested backup. PostgreSQL verification
uses separate admin and application URLs: the admin role installs `pgvector`,
creates/grants the application role, and runs Alembic; runtime and isolation
tests use the non-superuser application role. Never point this gate at an
unbacked production database.

The gate performs correctness-only Python linting, bounded type checks, unit
coverage, PostgreSQL integration tests, every model-free LongMemEval test,
the offline evidence replay, web tests/lint/build, both distribution builds,
Twine checks, and installed wheel/sdist smokes for all four public
entrypoints. It first fetches `origin/main`, and writes `dist/SHA256SUMS` only
after both artifacts pass.

CI must pass on the exact candidate SHA. Do not treat a green parent commit,
branch name, or locally rebuilt artifact as equivalent evidence.

## Tag And Publish

Before the finalization commit, move the `v0.9.2` entries out of `Unreleased`
under a dated `## v0.9.2 — YYYY-MM-DD` heading. Change the release-note title
from `Release Candidate Notes` to `Release Notes`, replace the candidate-status
paragraph, and remove `not published yet`. This finalizes the release text
without claiming that publication has already happened.

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
5. Create a non-draft, non-prerelease GitHub release from that tag.

The `Publish to PyPI` workflow then:

- rejects a prerelease or mismatched tag;
- rejects missing release-control attestation or candidate-state release docs;
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

Verify the GitHub release, PyPI file hashes, and a clean install from PyPI.
Then update remaining active control-document status language to say that the
version is published. That truth change belongs in a separate, evidence-backed
post-publication commit; the tagged changelog and release notes were already
finalized before the tag and must not have claimed publication early.
