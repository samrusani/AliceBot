# Security Policy

## Supported Scope

Alice is pre-1.0 software (`v0.5.1` is the latest tagged release). Security posture in this repo is scoped to the shipped local/runtime surfaces and deterministic verification paths on the current baseline.

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
- treat per-agent API keys (`alicebot agent keys create`) as secrets; they are stored hashed, printed exactly once, and can be revoked with `alicebot agent keys revoke`
- run verification commands before release tagging
