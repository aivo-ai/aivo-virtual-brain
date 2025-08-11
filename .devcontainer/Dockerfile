# syntax=docker/dockerfile:1.7-labs

# Base with Docker-in-Docker and common tools
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu-24.04

ARG NODE_VERSION=20.19.4
ARG PNPM_VERSION=9.11.0
ARG PYTHON_VERSION=3.11
ARG POETRY_VERSION=1.8.3

ENV DEBIAN_FRONTEND=noninteractive \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System deps, Playwright deps, Docker CLI, and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget gnupg lsb-release git bash-completion \
    build-essential pkg-config libssl-dev zlib1g-dev \
    # Playwright deps
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 \
    libxcomposite1 libxrandr2 libxdamage1 libgbm1 libpango-1.0-0 libasound2 \
    libpangocairo-1.0-0 libcairo2 libx11-6 libx11-xcb1 libxext6 libxfixes3 \
    libdrm2 libxcb-dri3-0 libcurl4-openssl-dev xvfb \
    # docker CLI for DinD workflows
    docker.io \
    jq yq && \
    rm -rf /var/lib/apt/lists/*

# Install Node (exact version) and pnpm via corepack
RUN set -eux; \
    arch=$(uname -m); \
    case "$arch" in \
      x86_64) NODE_ARCH=x64 ;; \
      aarch64) NODE_ARCH=arm64 ;; \
      *) echo "Unsupported arch: $arch"; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/node.tgz https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz; \
    mkdir -p /usr/local/lib/nodejs; \
    tar -xJf /tmp/node.tgz -C /usr/local/lib/nodejs; \
    ln -s /usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${NODE_ARCH}/bin/node /usr/local/bin/node; \
    ln -s /usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${NODE_ARCH}/bin/npm /usr/local/bin/npm; \
    ln -s /usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${NODE_ARCH}/bin/npx /usr/local/bin/npx; \
    /usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${NODE_ARCH}/bin/corepack enable; \
    /usr/local/lib/nodejs/node-v${NODE_VERSION}-linux-${NODE_ARCH}/bin/corepack prepare pnpm@${PNPM_VERSION} --activate; \
    node -v && pnpm -v

# Install Python 3.11 and Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-distutils python3-pip && \
    rm -rf /var/lib/apt/lists/* && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    python --version && \
    curl -sSL https://install.python-poetry.org | python - --version ${POETRY_VERSION} && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && poetry --version

# Install security tooling: trivy, osv-scanner, gitleaks, syft, cosign
RUN set -eux; \
    # trivy
    curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb stable main" | tee /etc/apt/sources.list.d/trivy.list; \
    apt-get update && apt-get install -y --no-install-recommends trivy && \
    # gitleaks
    GITLEAKS_VER=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | jq -r .tag_name | sed 's/v//'); \
    curl -fsSL -o /tmp/gitleaks.tar.gz "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VER}/gitleaks_${GITLEAKS_VER}_linux_x64.tar.gz"; \
    tar -xzf /tmp/gitleaks.tar.gz -C /usr/local/bin gitleaks && \
    # osv-scanner
    OSV_VER=$(curl -s https://api.github.com/repos/google/osv-scanner/releases/latest | jq -r .tag_name | sed 's/v//'); \
    curl -fsSL -o /usr/local/bin/osv-scanner "https://github.com/google/osv-scanner/releases/download/v${OSV_VER}/osv-scanner_${OSV_VER}_linux_amd64"; \
    chmod +x /usr/local/bin/osv-scanner && \
    # syft
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin && \
    # cosign
    COSIGN_VER=$(curl -s https://api.github.com/repos/sigstore/cosign/releases/latest | jq -r .tag_name); \
    curl -fsSL -o /usr/local/bin/cosign "https://github.com/sigstore/cosign/releases/download/${COSIGN_VER}/cosign-linux-amd64"; \
    chmod +x /usr/local/bin/cosign && \
    trivy -v && gitleaks version || true && osv-scanner --version

# Create default non-root user (vscode) and prepare workspace
ARG USERNAME=vscode
RUN usermod -aG docker ${USERNAME}

# Set working directory
WORKDIR /workspaces/aivo-virtual-brains

# Default CMD prints versions for acceptance check
CMD ["bash", "-lc", "node -v && python --version && pnpm -v && trivy -v && echo 'Devcontainer ready' "]
