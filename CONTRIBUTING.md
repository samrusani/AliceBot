# Contributing

Thanks for contributing to Alice.

## Scope Discipline

This repo enforces sprint-scoped delivery. Keep changes aligned to active sprint packet and avoid unrelated refactors.

## Local Setup

```bash
cp .env.example .env
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[dev]'
docker compose up -d
./scripts/migrate.sh
./scripts/load_sample_data.sh
```

## Required Validation

Before opening a PR, run:

```bash
python3 scripts/check_control_doc_truth.py
./.venv/bin/python -m pytest tests/unit tests/integration -q
pnpm --dir apps/web test
./.venv/bin/python scripts/run_hermes_memory_provider_smoke.py
./.venv/bin/python scripts/run_hermes_mcp_smoke.py
./.venv/bin/python scripts/run_hermes_bridge_demo.py
```

For `v0.2.0` release-doc or release-process changes:

```bash
python3 scripts/check_control_doc_truth.py
```

## Pull Request Expectations

- Keep PR scope narrow and sprint-aligned.
- Update docs when behavior or command paths change.
- Include exact commands executed and pass/fail evidence.
- Complete the protected-path `Upgrade Overview` when the PR touches paths listed in `PROTECTED_PATHS.md`.
- Do not introduce claims that outrun shipped functionality.

## Architecture and Rules

Read before making non-trivial changes:

- `ARCHITECTURE.md`
- `RULES.md`
- `PROTECTED_PATHS.md`
- active sprint packet (internal/local-only; not published in this repo)
