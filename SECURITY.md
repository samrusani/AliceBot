# Security Policy

## Supported Scope

Alice `v0.2.0` is a pre-1.0 release. Security posture in this repo is scoped to shipped local/runtime surfaces and deterministic verification paths through Phase 11 and Bridge `B1` through `B4`.

## Reporting a Vulnerability

Please report security issues privately by opening a private security advisory in GitHub for this repository. Include:

- affected component/file
- reproduction steps
- impact assessment
- suggested mitigation (if available)

Do not open public issues for active security vulnerabilities.

## Security Boundaries

- Postgres remains the system of record.
- User-owned data paths are RLS-governed.
- Public CLI/MCP/importer surfaces should not bypass trust/provenance boundaries.
- Consequential side effects remain approval-bounded.

## Hardening Notes

- keep `.env` local and do not commit secrets
- keep local services bound to loopback where possible
- run verification commands before release tagging
