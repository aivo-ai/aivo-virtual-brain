# Threat Model (High-level)

## Scope

Software supply-chain for aivo-virtual-brains monorepo: source, build, dependencies, CI/CD, and runtime images.

## Assets

- Source code and secrets
- Build artifacts (packages, images) and SBOMs
- CI credentials and signing keys

## Actors

- Developers (internal)
- CI/CD systems (GitHub Actions)
- Adversaries (external threat actors)

## Top Risks

1. Dependency risk (vulnerable, deprecated, or typosquatted packages)
2. Secret leakage (committed secrets, logs, or artifacts)
3. CI/CD compromise (workflow tampering, artifact poisoning)
4. SBOM/signing gaps (missing provenance/signatures)
5. Misconfiguration (excessive permissions, unpinned tools)

## Mitigations

- Dependency hygiene
  - Enforce Node 20.19.4 and pnpm strict peers; Python 3.11.x
  - CI: osv-scanner, trivy fs/image; dependency-review gate
  - Local: `pnpm run sec:deps` fails on deprecated packages
- Secret hygiene
  - Gitleaks pre-merge in CI and local runs
  - .gitignore for local artifacts; no secrets in repo
- CI/CD hardening
  - Branch protections, required checks, signed commits
  - Least-privilege tokens; explicit permissions in workflows
  - No lockfile mutations in CI (dlx for tooling)
- SBOM & signing
  - Syft SBOMs (SPDX & CycloneDX) and keyless Cosign signing
  - Upload artifacts as attestations
- Observability
  - Route/CTA guard for UX footguns
  - Playwright a11y tests (optional when added)

## Residual Risk & Next Steps

- Pin versions for security tools for full reproducibility
- Add image signing/attestations to releases
- Periodic secret rotation and audit
