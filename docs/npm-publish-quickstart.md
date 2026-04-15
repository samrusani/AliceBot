# NPM Publish Quickstart (`@aliceos`)

This repo now includes two publish-ready package scaffolds:

- `packages/alice-core` -> `@aliceos/alice-core`
- `packages/alice-cli` -> `@aliceos/alice-cli`

## 1) Login

```bash
npm login
npm whoami
```

## 2) Publish core first

```bash
cd packages/alice-core
npm publish --access public
```

## 3) Publish CLI second

```bash
cd ../alice-cli
npm publish --access public
```

Publish order matters because `@aliceos/alice-cli` depends on `@aliceos/alice-core`.

## 4) Verify

```bash
npm view @aliceos/alice-core
npm view @aliceos/alice-cli
```

## 5) Enable tag-based auto publish (GitHub Actions)

Set repository secret:

- `NPM_TOKEN` = npm automation token with publish access to `@aliceos`

Workflow file:

- `.github/workflows/publish-npm.yml`

After that, push the current semver tag:

```bash
git tag v0.3.2
git push origin v0.3.2
```
