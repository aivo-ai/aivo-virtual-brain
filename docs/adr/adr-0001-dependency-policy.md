# ADR-0001: Dependency Management Policy

## Status

Accepted

## Context

The aivo-virtual-brains monorepo requires automated dependency management to:

- Maintain security posture with timely vulnerability patches
- Reduce manual overhead of dependency updates
- Ensure stability through controlled update cadence
- Support both Node.js (pnpm) and Python (Poetry) ecosystems

## Decision

We will use Renovate Bot with the following policy:

### Update Strategy

- **Patch updates**: Automated PRs, manual merge required
- **Minor updates**: Automated PRs, manual merge required
- **Major updates**: Dependency Dashboard approval required, manual merge
- **Security updates**: High priority, any-time scheduling
- **Lockfile maintenance**: Weekly on Mondays

### Rate Limiting

- Maximum 2 concurrent PRs
- Maximum 2 PRs per hour
- Scheduled updates before 6am UTC on weekdays
- Security updates exempt from scheduling

### Critical Package Protection

Major version updates are **disabled** for:

- `turbo` (build orchestration)
- `prettier` (code formatting)
- `husky` (git hooks)
- `@commitlint/*` (commit validation)

### Node.js Version Pinning

- Node.js version updates are **disabled** (manual review required)
- Custom manager tracks .nvmrc but requires manual approval
- Ensures compatibility with DevContainer and CI pinning

### Quality Gates

- All PRs must pass CI (contracts, ci-node, ci-python, sbom-sign)
- `dependency-review-action` blocks vulnerable dependencies
- OSV vulnerability alerts enabled
- SBOM generation for supply-chain transparency

## Consequences

### Positive

- Automated security patching reduces exposure window
- Dependency Dashboard provides visibility into available updates
- Rate limiting prevents CI resource exhaustion
- Major version protection prevents breaking changes
- Quality gates ensure updates don't introduce regressions

### Negative

- Manual merge requirement increases maintenance overhead
- Conservative approach may delay beneficial updates
- Dependency Dashboard approval adds friction for majors
- Node.js pinning requires manual coordination across DevContainer/CI

### Mitigations

- Weekly lockfile maintenance keeps indirect dependencies fresh
- Security updates bypass scheduling for urgent fixes
- Semantic prefixes improve commit message clarity
- Assignees from CODEOWNERS ensure proper review

## Alternatives Considered

- **Dependabot**: Less configurable, GitHub-only, no Poetry support
- **Manual updates**: High overhead, inconsistent security posture
- **Fully automated**: Higher risk of breaking changes, production issues

## References

- [Renovate Documentation](https://docs.renovatebot.com/)
- [dependency-review-action](https://github.com/actions/dependency-review-action)
- [OSV Database](https://osv.dev/)
