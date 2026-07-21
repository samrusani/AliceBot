# Security Review Evidence

This directory is the durable Stage A preparation package for Alice's first
independent security review. It describes the shipped local-first product,
records what the repository currently proves, and names proof gaps without
turning team-authored evidence into an independent sign-off.

## Status

- Stage A threat model and evidence package: **prepared; focused final-carrier
  receipts are green**.
- Stage B independent review (Phase 5.1.c): **open and owner-owned**.
- Security certification or assurance claim: **none**.
- Version change or release approval: **not granted by these documents**.

The Stage A baseline is `main` at
`c9d24243920a694eaf00ad595da392a1478710dd`. The browser-clipper remediation
adds one HTTP operation to that baseline. The frozen carrier has
183 default HTTP operations, including 71 `/v0/vnext` operations, 232 HTTP
operations with legacy surfaces enabled, and 11 core MCP tools. Route, OpenAPI,
legacy-gating, and flag-off MCP closure tests reproduced those counts. The base
counts were 182, 70, 231, and 11.

## Evidence Language

- **Implemented control** means the named code path exists.
- **Test evidence** means a named repository test exercises the claim; it still
  has to pass on the exact review commit.
- **Carrier acceptance** means a final-carrier CI or local result is required.
- **Proof gap** means the team does not claim closure.
- **Owner action** is outside the builder team's authority.

## Package Index

- [Threat model](threat-model.md) — assets, actors, trust boundaries, data flows,
  abuse cases, controls, and residual risks.
- [Stage A evidence ledger](stage-a-evidence.md) — scope, source provenance,
  acceptance rules, and known gaps.
- [Authentication and authorization](auth-authorization.md) — HTTP, MCP, agent
  key, project-scope, RLS, SQLite, and legacy-gating boundaries.
- [Input validation](input-validation.md) — request models, SQL/JSON/FTS
  construction, import paths, and the deferred directory-import gap.
- [Secrets and redaction](secrets-redaction.md) — key storage, provider secrets,
  public errors, logging evidence, and RAM-hygiene limits.
- [Dependency posture](dependency-posture.md) — pinning, advisory tooling,
  automated scans, and the Python audit gap.
- [External-review brief](external-review-brief.md) — owner-owned Stage B scope,
  environment, expected deliverables, and current status.

## Historical Scan: Input, Not Sign-off

A repository-wide deep scan targeted
`2c372417e1d07d072265d2efdfbdace04f8bfcbb`, not the Phase 5 base or final
carrier. Its report contains 41 canonical findings represented by 156 report
instances: 24 Medium and 132 Low, no High or Critical, all with Medium
confidence. Coverage was partial and the report explicitly retained runtime and
deployment proof gaps.

The scan artifacts remain with the release engineer. They are historical review
input only: the counts must not be presented as a current-head finding count,
clean bill of health, external assessment, or proof that untested paths are
safe. Three confirmed issues from that cycle were merged in PRs #310, #311, and
#312; the browser-clipper credential-context remediation belongs to the Phase 5
carrier and must pass its final acceptance tests. Stage B must assess the exact
release candidate independently.
