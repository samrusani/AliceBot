# BUILD_REPORT

## sprint objective

Implement Sprint 6C: stabilize the `apps/web` workspace so lint and build are clean, repeatable, non-interactive verification steps while preserving the shipped Sprint 6A and Sprint 6B shell routes and workflow behavior.

## completed work

- committed a stable ESLint setup in `apps/web` and switched the web lint script to `eslint . --max-warnings=0` so `npm run lint` no longer invokes interactive `next lint` setup
- intentionally adopted the Next-generated TypeScript config updates in `apps/web/tsconfig.json`
  - added `esModuleInterop: true`
  - added the `next` TypeScript plugin
  - added `.next/types/**/*.ts` to `include`
- intentionally adopted the framework-managed `apps/web/next-env.d.ts` header text produced by Next.js
- made one behavior-preserving component change in `apps/web/components/approval-actions.tsx` to satisfy the committed hook lint rule without changing approval UI flow
- verified that `npm run build` no longer changes the contents of `apps/web/tsconfig.json` or `apps/web/next-env.d.ts` after those adopted config updates were in place

## incomplete work

- no backend endpoint, schema, or contract changes
- no new routes or workflow features
- no shell redesign or adjacent UI expansion
- no Gmail, Calendar, auth, runner, or connector scope expansion
- no additional frontend tests beyond the existing narrow verification set

## files changed

- `BUILD_REPORT.md`
- `apps/web/package.json`
- `apps/web/eslint.config.mjs`
- `apps/web/tsconfig.json`
- `apps/web/next-env.d.ts`
- `apps/web/components/approval-actions.tsx`

## tests run

- `npm run lint` in `apps/web`
  - PASS
  - non-interactive after the committed ESLint config and script change
- `npm test` in `apps/web`
  - PASS
  - `2` test files, `5` tests passed
- `npm run build` in `apps/web`
  - PASS
  - generated shipped routes remained intact: `/`, `/chat`, `/approvals`, `/tasks`, `/traces`

## exact verification results

- lint command used: `npm run lint`
- test command used: `npm test`
- build command used: `npm run build`
- TypeScript or Next-generated config changes intentionally adopted: yes
  - `apps/web/tsconfig.json`
  - `apps/web/next-env.d.ts`
- build stability check:
  - `shasum apps/web/tsconfig.json apps/web/next-env.d.ts` was unchanged before vs. after `npm run build`
  - pre-build checksum:
    - `23632802ddf6784e5989d71338904efe50848844  apps/web/tsconfig.json`
    - `f75a118439f630e5ca41d376cedef8db9b6d7fc6  apps/web/next-env.d.ts`
  - post-build checksum:
    - `23632802ddf6784e5989d71338904efe50848844  apps/web/tsconfig.json`
    - `f75a118439f630e5ca41d376cedef8db9b6d7fc6  apps/web/next-env.d.ts`

## route and behavior confirmation

- route generation from `next build` still includes `/`, `/chat`, `/approvals`, `/tasks`, and `/traces`
- Sprint 6A and 6B governed request, approval, and task behavior remained intact
- no workflow logic or API contract changes were introduced; the only non-config code change was the `approval-actions` hook dependency cleanup required by lint

## blockers/issues

- no active blockers after the repair
- initial pre-fix issue reproduced exactly as described in the sprint packet:
  - `npm run lint` prompted for ESLint initialization because the workspace had no committed lint config
  - `next build` rewrote `apps/web/tsconfig.json` and `apps/web/next-env.d.ts` until those framework-required changes were intentionally adopted

## recommended next step

Run review against this repair sprint and, if it passes, treat the committed ESLint config plus adopted Next TypeScript settings as the new stable baseline for future `apps/web` UI work.

## intentionally deferred after this sprint

- any new product workflow surface beyond the existing `/`, `/chat`, `/approvals`, `/tasks`, and `/traces` routes
- any backend work
- any visual redesign
- any additional test expansion beyond narrow preservation coverage
