# aivo-virtual-brains

Monorepo scaffold using pnpm + Turborepo pinned to Node 20.19.4 with strict dependency rules, Husky + lint-staged, Commitlint + Commitizen, and basic security checks.

## Requirements

- Node 20.19.4 (enforced via `.nvmrc` and `engines`)
- Python 3.11.x (enforced via `.python-version`)
- pnpm (recommended via Corepack)

## Structure

- apps/web
- apps/gateway
- services/
- libs/
- infra/
- docs/
- scripts/

## Quick start

1. Ensure Node 20.19.4 is active.
2. Enable Corepack and prepare pnpm.
3. Install dependencies (this also installs Husky hooks).
4. Run verification.

### Commands

```powershell
# 1) Verify Node version
node -v

# 2) Enable Corepack (recommended)
corepack enable; corepack prepare pnpm@latest --activate

# 3) Install dev deps and setup husky
pnpm install

# 4) Run verification (turbo, security checks, deprecation scan)
pnpm run verify-all

# Optional: dependency hygiene
pnpm run deps:dedupe
pnpm run deps:outdated
```

## Conventional Commits

Use Commitizen: run `git cz` (wired as a git alias to `pnpm commit`). Commitlint enforces conventional commit messages.

## Security

`pnpm run sec:all` attempts to run `osv-scanner` and `trivy fs` if found. Install those tools locally to enforce HIGH/CRITICAL blocking; otherwise, they're skipped with a notice.

## License

Apache-2.0
