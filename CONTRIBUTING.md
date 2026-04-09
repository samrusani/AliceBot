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
./.venv/bin/python -m pytest tests/unit tests/integration
pnpm --dir apps/web test
```

For Phase 9 public-surface changes, also run:

```bash
./scripts/run_phase9_eval.sh --report-path eval/reports/phase9_eval_latest.json
```

## Pull Request Expectations

- Keep PR scope narrow and sprint-aligned.
- Update docs when behavior or command paths change.
- Include exact commands executed and pass/fail evidence.
- Do not introduce claims that outrun shipped functionality.

## Architecture and Rules

Read before making non-trivial changes:

- `ARCHITECTURE.md`
- `RULES.md`
- active sprint packet (internal/local-only; not published in this repo)
