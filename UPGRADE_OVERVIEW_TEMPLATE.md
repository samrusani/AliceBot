# Upgrade Overview Template

Use this template in a pull request whenever the change touches a path listed in [PROTECTED_PATHS.md](PROTECTED_PATHS.md).
The goal is to make compatibility, rollout, and rollback intent explicit before merge.

```md
## Upgrade Overview

### Protected Areas

- [ ] memory schema
- [ ] evidence pipeline
- [ ] trust rules
- [ ] promotion logic
- [ ] continuity APIs

### Compatibility Impact

State whether the change is additive-only, behavior-changing, or breaking.
Call out stored-data impact, contract impact, and any caller-visible changes.

### Migration / Rollout

Describe deploy order, migrations, backfills, feature flags, and any sequencing requirements.

### Operator Action

List required manual steps, or say explicitly that no manual action is required.

### Validation

List exact tests, smoke checks, fixtures, and manual verification performed.

### Rollback

Explain how the change is reverted, contained, or disabled safely if problems appear after deploy.
```

## Notes

- Check every protected area that the PR actually touches.
- Do not leave sections blank or as placeholders such as `TBD`, `N/A`, or `none`.
- If the change is intentionally non-breaking, say why.
- If rollback is constrained by schema or data movement, say that directly.
