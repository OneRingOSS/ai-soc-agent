# SOC Agent System – Architecture v2: Operations
## CI/CD Pipelines, Environment Strategy & Security Scanning

**Version:** 2.0
**Last Updated:** February 16, 2026
**Status:** Enterprise Architecture Blueprint

---

## Table of Contents

1. [CI/CD & Environments](#1-cicd--environments)
   - 1.1 [Branching & Environment Model](#11-branching--environment-model)
   - 1.2 [CI Pipeline (Per Pull Request)](#12-ci-pipeline-per-pull-request)
   - 1.3 [Staging Pipeline](#13-staging-pipeline)
   - 1.4 [Production Pipeline](#14-production-pipeline)
   - 1.5 [Release Management](#15-release-management)
   - 1.6 [Feature Flags](#16-feature-flags)
   - 1.7 [Database Migration Strategy](#17-database-migration-strategy)
2. [Security Scanning & Supply Chain Hardening](#2-security-scanning--supply-chain-hardening)
   - 2.1 [Scanning Matrix](#21-scanning-matrix)
   - 2.2 [Static Analysis & SAST](#22-static-analysis--sast)
   - 2.3 [Dependency & SCA Scanning](#23-dependency--sca-scanning)
   - 2.4 [Secrets Detection](#24-secrets-detection)
   - 2.5 [Container Image Scanning](#25-container-image-scanning)
   - 2.6 [Infrastructure-as-Code Scanning](#26-infrastructure-as-code-scanning)
   - 2.7 [Runtime Security](#27-runtime-security)
   - 2.8 [Policy-as-Code](#28-policy-as-code)
   - 2.9 [SBOM & Supply Chain](#29-sbom--supply-chain)
   - 2.10 [Vendor Comparison](#210-vendor-comparison)

---

## 1. CI/CD & Environments

### 1.1 Branching & Environment Model

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        BRANCHING MODEL                                  │
│                                                                         │
│  feature/SOC-123-add-rbac ──┐                                          │
│  feature/SOC-124-go-gateway ─┤──▶ develop ──▶ release/v2.1 ──▶ main   │
│  feature/SOC-125-mlops ──────┘       │                           │      │
│                                      │                           │      │
│                                      ▼                           ▼      │
│                              ┌──────────────┐          ┌────────────┐  │
│                              │   STAGING     │          │ PRODUCTION │  │
│                              │   (auto-      │          │ (manual    │  │
│                              │    deploy on  │          │  approve + │  │
│                              │    merge to   │          │  canary)   │  │
│                              │    develop)   │          │            │  │
│                              └──────────────┘          └────────────┘  │
│                                                                         │
│  PR → feature branch:  CI pipeline (lint, test, scan, build)           │
│  Merge to develop:     Auto-deploy to staging + E2E tests              │
│  Release branch:       Cut from develop, final QA, version bump        │
│  Merge to main:        Production deployment (canary rollout)          │
│  Hotfix:               Branch from main, fix, merge to main + develop  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Environment Details

| Environment | Purpose | Infra Scale | Data | Deployed From | Lifecycle |
|-------------|---------|-------------|------|--------------|-----------|
| **CI** | Automated testing per PR | Ephemeral K8s namespace (Kind or cluster) | Synthetic test data | Feature branch | Created on PR open, destroyed on PR close |
| **Staging** | Integration testing, QA | 50% of prod (2 backend replicas, small DB) | Anonymized copy of prod data (refreshed weekly) | `develop` branch (auto-deploy) | Persistent, reset weekly |
| **Production** | Live system | Full scale (HPA 2-20 replicas, HA DB) | Real customer data | `main` branch (manual approval + canary) | Persistent, HA |

### 1.2 CI Pipeline (Per Pull Request)

Triggered on every PR to `develop` or `main`. Must pass before merge is allowed.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    CI PIPELINE (GitHub Actions / GitLab CI)              │
│                                                                         │
│  ┌─────────┐   ┌──────────┐   ┌────────────┐   ┌──────────────────┐  │
│  │ STAGE 1 │   │ STAGE 2  │   │  STAGE 3   │   │    STAGE 4       │  │
│  │ Lint &  │──▶│ Unit &   │──▶│  Security  │──▶│  Build & Image   │  │
│  │ Format  │   │ Integ    │   │  Scanning  │   │  Scanning        │  │
│  │         │   │ Tests    │   │            │   │                  │  │
│  │ • ruff  │   │ • pytest │   │ • Semgrep  │   │ • Docker build   │  │
│  │ • mypy  │   │ • 48+    │   │   (SAST)   │   │ • Trivy scan     │  │
│  │ • eslint│   │   tests  │   │ • Trufflhg │   │ • Grype scan     │  │
│  │ • black │   │ • coverg │   │   (secrets)│   │ • Cosign sign    │  │
│  │ • gofmt │   │   ≥80%   │   │ • Snyk/    │   │ • Push to        │  │
│  │ (if Go) │   │ • go test│   │   Trivy    │   │   registry       │  │
│  │         │   │   (if Go)│   │   (deps)   │   │   (staging tag)  │  │
│  └─────────┘   └──────────┘   └────────────┘   └──────────────────┘  │
│                                                                         │
│  GATE: All stages must pass. Any failure blocks merge.                 │
│                                                                         │
│  Artifacts produced:                                                   │
│  • Test coverage report (uploaded to PR comment)                       │
│  • Security scan summary (uploaded to PR comment)                      │
│  • Docker images tagged with PR SHA (pushed to staging registry)       │
│  • SBOM (Software Bill of Materials) for each image                    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Stage Details

**Stage 1 — Lint & Format (parallelized, ~30 seconds):**

```yaml
# GitHub Actions example
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Python lint
      run: |
        ruff check backend/src/ --output-format=github
        mypy backend/src/ --ignore-missing-imports
    - name: Frontend lint
      run: |
        cd frontend && npm ci && npx eslint src/
    - name: Go lint (if applicable)
      run: |
        cd gateway && golangci-lint run ./...
```

**Stage 2 — Tests (~2-3 minutes):**

```yaml
test:
  runs-on: ubuntu-latest
  services:
    redis:
      image: redis:7-alpine
      ports: ["6379:6379"]
  steps:
    - uses: actions/checkout@v4
    - name: Python tests
      run: |
        cd backend
        pip install -r requirements.txt -r requirements-test.txt
        pytest tests/ -v --cov=src --cov-report=xml --cov-fail-under=80
    - name: Upload coverage
      uses: codecov/codecov-action@v4
      with:
        files: backend/coverage.xml
```

**Stage 3 — Security Scanning (~1-2 minutes, parallelized):**

```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: SAST - Semgrep
      uses: returntocorp/semgrep-action@v1
      with:
        config: >-
          p/python
          p/owasp-top-ten
          p/security-audit

    - name: Secrets - TruffleHog
      run: |
        trufflehog filesystem . --only-verified --fail

    - name: Dependencies - Trivy
      run: |
        trivy fs . --scanners vuln --severity CRITICAL,HIGH --exit-code 1
```

**Stage 4 — Build & Image Scan (~3-5 minutes):**

```yaml
build:
  needs: [lint, test, security]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Build images
      run: |
        docker build -t soc-backend:${{ github.sha }} -f Dockerfile.backend .
        docker build -t soc-frontend:${{ github.sha }} -f Dockerfile.frontend .

    - name: Scan images - Trivy
      run: |
        trivy image soc-backend:${{ github.sha }} --severity CRITICAL --exit-code 1
        trivy image soc-frontend:${{ github.sha }} --severity CRITICAL --exit-code 1

    - name: Generate SBOM
      run: |
        syft soc-backend:${{ github.sha }} -o spdx-json > sbom-backend.json
        syft soc-frontend:${{ github.sha }} -o spdx-json > sbom-frontend.json

    - name: Sign images
      run: |
        cosign sign --key cosign.key soc-backend:${{ github.sha }}
        cosign sign --key cosign.key soc-frontend:${{ github.sha }}

    - name: Push to registry
      run: |
        docker tag soc-backend:${{ github.sha }} $REGISTRY/soc-backend:${{ github.sha }}
        docker push $REGISTRY/soc-backend:${{ github.sha }}
```

### 1.3 Staging Pipeline

Triggered automatically when a PR merges to `develop`.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      STAGING PIPELINE                                   │
│                                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────┐   │
│  │   Deploy to  │──▶│  E2E Tests   │──▶│  Performance Baseline    │   │
│  │   Staging    │   │              │   │                          │   │
│  │              │   │ • Smoke tests│   │ • Locust 5-min run       │   │
│  │ • Helm      │   │ • test_docker│   │ • Compare P95 latency    │   │
│  │   upgrade   │   │   _compose.sh│   │   vs previous release    │   │
│  │ • DB        │   │ • All 7      │   │ • Compare error rate     │   │
│  │   migrate   │   │   threat     │   │ • Compare FP rate        │   │
│  │ • Wait for  │   │   types      │   │                          │   │
│  │   healthy   │   │ • WebSocket  │   │ GATE: P95 <1s, err <1%,  │   │
│  │             │   │   test       │   │ no regression >10%        │   │
│  └──────────────┘   └──────────────┘   └──────────────────────────┘   │
│                                                                         │
│  On success: Tag images as staging-ready. Notify in Slack.             │
│  On failure: Revert staging. Block release branch creation.            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key staging tests:**

```bash
#!/bin/bash
# tests/e2e/test_staging.sh
set -e

STAGING_URL="https://staging.soc.internal"

echo "=== Staging E2E Tests ==="

# 1. Health & readiness
curl -sf "$STAGING_URL/health" | jq -e '.status == "healthy"'
curl -sf "$STAGING_URL/ready" | jq -e '.status == "ready"'

# 2. Auth (v2: test RBAC)
TOKEN=$(curl -sf -X POST "$STAGING_URL/auth/token" \
  -d '{"username":"test-analyst","password":"$TEST_PASSWORD"}' | jq -r '.access_token')

# 3. Trigger all 7 threat types
for TYPE in bot_traffic credential_stuffing account_takeover data_scraping geo_anomaly rate_limit_breach brute_force; do
  RESPONSE=$(curl -sf -X POST "$STAGING_URL/api/threats/trigger" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"threat_type\":\"$TYPE\",\"customer_name\":\"StagingTest\",\"customer_id\":\"stg-001\",\"source_ip\":\"10.0.0.1\",\"request_count\":500,\"time_window_minutes\":5}")
  echo "$RESPONSE" | jq -e '.id' > /dev/null
  echo "✅ $TYPE processed"
done

# 4. Verify data in Grafana
sleep 10
PROM_RESULT=$(curl -sf "http://prometheus.staging:9090/api/v1/query?query=soc_threats_processed_total")
echo "$PROM_RESULT" | jq -e '.status == "success"'
echo "✅ Metrics flowing to Prometheus"

# 5. Verify traces in Jaeger
TRACES=$(curl -sf "http://jaeger.staging:16686/api/traces?service=soc-agent-system&limit=5")
TRACE_COUNT=$(echo "$TRACES" | jq '.data | length')
[ "$TRACE_COUNT" -ge 5 ]
echo "✅ Traces in Jaeger ($TRACE_COUNT found)"

echo "=== All staging tests passed ==="
```

### 1.4 Production Pipeline

Triggered manually (or via release branch merge to `main`) with required approvals.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRODUCTION PIPELINE                                   │
│                                                                         │
│  ┌──────────┐   ┌──────────────┐   ┌──────────┐   ┌──────────────┐   │
│  │ Approval │──▶│ Canary 10%   │──▶│ Analysis │──▶│ Canary 50%   │   │
│  │          │   │              │   │ (5 min)  │   │              │   │
│  │ • 2      │   │ • Deploy new │   │          │   │ • Expand if  │   │
│  │   human  │   │   version to │   │ • Error  │   │   analysis   │   │
│  │   approvers  │   10% pods   │   │   rate   │   │   passed     │   │
│  │ • Release│   │ • Route 10%  │   │ • Latency│   │              │   │
│  │   notes  │   │   traffic    │   │ • FP rate│   │              │   │
│  │   reviewed│  │              │   │ • vs     │   │              │   │
│  │          │   │              │   │   baseline│  │              │   │
│  └──────────┘   └──────────────┘   └──────────┘   └──────────────┘   │
│                                                                         │
│                    ┌──────────┐   ┌──────────────┐                     │
│               ──▶  │ Analysis │──▶│ Full 100%    │                     │
│                    │ (10 min) │   │              │                     │
│                    │          │   │ • Promote    │                     │
│                    │ • Same   │   │   to 100%    │                     │
│                    │   checks │   │ • Tag release│                     │
│                    │          │   │ • Notify team│                     │
│                    └──────────┘   └──────────────┘                     │
│                                                                         │
│  AUTO-ROLLBACK: If any analysis gate fails, automatically rollback     │
│  to previous version and page on-call engineer.                        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Canary analysis template (Argo Rollouts):**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
spec:
  metrics:
    - name: error-rate
      interval: 60s
      successCondition: result[0] < 0.01  # <1% error rate
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            sum(rate(http_request_duration_seconds_count{status=~"5..",app="soc-backend",version="{{args.canary-version}}"}[2m]))
            /
            sum(rate(http_request_duration_seconds_count{app="soc-backend",version="{{args.canary-version}}"}[2m]))
    - name: latency-p95
      interval: 60s
      successCondition: result[0] < 1.0  # <1s P95
      provider:
        prometheus:
          address: http://prometheus:9090
          query: |
            histogram_quantile(0.95, sum(rate(soc_threat_processing_duration_seconds_bucket{phase="total",version="{{args.canary-version}}"}[2m])) by (le))
```

### 1.5 Release Management

- **Versioning:** Semantic versioning — `MAJOR.MINOR.PATCH` (e.g., `2.1.0`).
  - Major: breaking API changes, major architecture shifts.
  - Minor: new features, new analyzers, new integrations.
  - Patch: bug fixes, security patches, config changes.
- **Changelogs:** Auto-generated from PR titles using conventional commits:
  - `feat:`, `fix:`, `perf:`, `security:`, `docs:`, `chore:`.
- **Release process:**
  1. Cut `release/v2.1` branch from `develop`.
  2. Version bump in `Chart.yaml`, `pyproject.toml`, `package.json`.
  3. Final QA on staging.
  4. Merge to `main` → triggers production pipeline.
  5. Tag: `git tag v2.1.0` → triggers GitHub release with changelog.

### 1.6 Feature Flags

New analyzers, ML models, and major features are deployed behind flags.

**Implementation:**
- Simple: environment variable per feature (`FEATURE_GO_GATEWAY=true`).
- Advanced: LaunchDarkly, Unleash, or Flagsmith for tenant-level targeting.

**Use cases:**
- New ML model for FP Analyzer: `FEATURE_ML_FP_MODEL=shadow` (runs but doesn't affect scoring).
- Go ingestion gateway: `FEATURE_GO_GATEWAY=canary` (10% of traffic).
- RBAC enforcement: `FEATURE_RBAC_ENFORCE=true` (flip from audit-only to enforcing).

### 1.7 Database Migration Strategy

**Tool:** Alembic (Python) for PostgreSQL migrations.

**Rules:**
- Every migration must be **backward-compatible** (expand-contract pattern).
- **Expand:** Add new columns as nullable, add new tables. Deploy new code that writes to both old and new schemas.
- **Contract:** After all pods are on new code, drop old columns in a subsequent release.
- Never rename or delete columns in the same release as a code change.

**Pipeline integration:**
```yaml
# In staging pipeline
- name: Run migrations
  run: |
    alembic upgrade head --sql > migration_preview.sql  # Preview
    cat migration_preview.sql  # Log for review
    alembic upgrade head  # Apply

- name: Verify migration
  run: |
    alembic current  # Should show latest revision
    python -c "from models import *; print('Models load OK')"  # Import check
```

---

## 2. Security Scanning & Supply Chain Hardening

### 2.1 Scanning Matrix

| Scan Type | When | Tool(s) | Blocks Deploy? | Alert Channel |
|-----------|------|---------|---------------|---------------|
| **SAST** (Static Analysis) | Every PR | Semgrep, Bandit, gosec | Yes (Critical/High) | PR comment |
| **SCA** (Dependencies) | Every PR + nightly | Trivy, Snyk, Dependabot | Yes (Critical) | PR comment + Slack |
| **Secrets** | Every PR + pre-commit | TruffleHog, GitLeaks | Yes (any finding) | PR comment + PagerDuty |
| **Container images** | Every build | Trivy, Grype | Yes (Critical) | PR comment |
| **IaC** | Every PR with infra changes | Checkov, tfsec, Terrascan | Yes (High) | PR comment |
| **SBOM** | Every build | Syft | No (informational) | Stored as artifact |
| **Runtime** | Continuous | Falco, Datadog CWS | No (alert only) | PagerDuty + Slack |
| **Policy-as-Code** | Every PR + admission | OPA Gatekeeper, Kyverno | Yes (policy violation) | PR comment + K8s events |

### 2.2 Static Analysis & SAST

#### Semgrep (Primary SAST)

```yaml
# .semgrep/custom-rules.yml
rules:
  - id: rbac-check-missing
    patterns:
      - pattern: |
          @app.post("/api/...")
          async def $FUNC(...):
              ...
      - pattern-not: |
          @app.post("/api/...")
          @require_permission("...")
          async def $FUNC(...):
              ...
    message: "API endpoint missing RBAC check"
    severity: ERROR
    languages: [python]

  - id: tenant-id-missing-query
    pattern: |
      session.query($MODEL).filter(...)
    pattern-not: |
      session.query($MODEL).filter(..., $MODEL.tenant_id == ...)
    message: "Database query missing tenant_id filter — potential data leak"
    severity: ERROR
    languages: [python]

  - id: raw-sql-injection
    pattern: |
      f"SELECT ... {$VAR} ..."
    message: "Potential SQL injection via f-string"
    severity: ERROR
    languages: [python]
```

#### Additional SAST Tools

| Tool | Language | Focus |
|------|----------|-------|
| **Bandit** | Python | Security-specific linting (eval, exec, hardcoded passwords) |
| **gosec** | Go | Go-specific security issues (crypto, injection, permissions) |
| **ESLint security plugin** | JavaScript/React | XSS, unsafe innerHTML, eval |
| **CodeQL** | Multi-language | Deep semantic analysis (GitHub Advanced Security) |

### 2.3 Dependency & SCA Scanning

**Multi-tool strategy** (belt + suspenders):

| Tool | Strength | Integration |
|------|----------|-------------|
| **Trivy** (open source) | Fast, broad coverage (OS + language packages), free | CI pipeline + container scanning |
| **Snyk** (commercial) | Best vulnerability database, fix PRs, license compliance | GitHub integration + CI |
| **Dependabot** (GitHub native) | Auto-creates PRs for dependency updates | GitHub native |
| **Grype** (open source) | Anchore-powered, good for container SCA | CI pipeline |
| **Endor Labs** (commercial) | **Reachability analysis** — determines if vulnerabilities are actually exploitable in your code paths. Reduces noise by 80%+. | CI pipeline — most relevant given interview context |

**Configuration:**

```yaml
# trivy.yaml
severity:
  - CRITICAL
  - HIGH
ignore:
  - CVE-2023-XXXXX  # Documented exception with justification
  - CVE-2024-YYYYY  # Not reachable per Endor Labs analysis
```

### 2.4 Secrets Detection

**Pre-commit hook (developer machine):**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/trufflesecurity/trufflehog
    rev: main
    hooks:
      - id: trufflehog
        name: TruffleHog secrets scan
        entry: trufflehog filesystem . --only-verified --fail
```

**CI pipeline:**
```yaml
- name: TruffleHog scan
  run: trufflehog filesystem . --only-verified --fail --json > trufflehog-results.json

- name: GitLeaks scan (backup)
  run: gitleaks detect --source . --report-format json --report-path gitleaks-report.json
```

**Policy:** Any verified secret finding blocks the merge. No exceptions.

### 2.5 Container Image Scanning

**Multi-scanner approach:**

```bash
# Trivy — broad vulnerability database
trivy image soc-backend:$SHA \
  --severity CRITICAL,HIGH \
  --exit-code 1 \
  --format json \
  --output trivy-report.json

# Grype — Anchore vulnerability database (different DB = different coverage)
grype soc-backend:$SHA \
  --fail-on critical \
  --output json > grype-report.json
```

**Image hardening:**
- Use distroless or slim base images (e.g., `python:3.11-slim`, `gcr.io/distroless/python3`).
- Run as non-root user in Dockerfile.
- No shell in production images (distroless).
- Pin base image digests, not tags.

```dockerfile
# Hardened Dockerfile example
FROM python:3.11-slim@sha256:<pinned_digest> AS builder
# ... build steps ...

FROM gcr.io/distroless/python3-debian12
COPY --from=builder /app /app
USER nonroot:nonroot
ENTRYPOINT ["python", "/app/main.py"]
```

### 2.6 Infrastructure-as-Code Scanning

| Tool | Scans | Integration |
|------|-------|-------------|
| **Checkov** | Terraform, Helm, K8s manifests, Dockerfiles | CI pipeline, pre-commit |
| **tfsec** (now part of Trivy) | Terraform HCL | CI pipeline |
| **Terrascan** | Terraform, K8s, Helm, CloudFormation | CI pipeline |
| **kube-score** | K8s manifests for best practices | CI pipeline |
| **Pluto** | Deprecated K8s API versions | CI pipeline |

**Example Checkov run:**
```bash
# Scan Helm chart
checkov -d charts/soc-agent/ --framework helm --output json > checkov-helm.json

# Scan Kubernetes manifests
checkov -d k8s/ --framework kubernetes --output json > checkov-k8s.json

# Scan Dockerfiles
checkov -f Dockerfile.backend --framework dockerfile
checkov -f Dockerfile.frontend --framework dockerfile
```

**Common findings to enforce:**
- No containers running as root.
- All pods have resource limits.
- All services use ClusterIP (no LoadBalancer without WAF).
- All secrets mounted as volumes (not environment variables).
- Network policies defined for all namespaces.

### 2.7 Runtime Security

**Falco (open source):**
- Deployed as DaemonSet on every K8s node.
- Monitors syscalls using eBPF.
- Detects:
  - Shell spawned in container.
  - Unexpected network connections.
  - Sensitive file access (/etc/shadow, /proc).
  - Privilege escalation attempts.
- Alerts routed to Slack + PagerDuty.

```yaml
# Custom Falco rule for SOC system
- rule: SOC Backend Shell Access
  desc: Detect shell access in SOC backend containers
  condition: >
    spawned_process and container and
    container.image.repository contains "soc-backend" and
    proc.name in (bash, sh, dash, csh)
  output: >
    Shell spawned in SOC backend (user=%user.name container=%container.name
    command=%proc.cmdline image=%container.image.repository)
  priority: WARNING
  tags: [container, shell, soc]
```

**Datadog Cloud Workload Security (commercial alternative):**
- Agent-based, integrates with Datadog APM.
- Pre-built detection rules for MITRE ATT&CK.
- Threat detection + investigation in same platform as observability.

### 2.8 Policy-as-Code

**OPA Gatekeeper (open source):**

Enforces policies on K8s resources at admission time.

```yaml
# ConstraintTemplate: require non-root containers
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequirenonroot
spec:
  crd:
    spec:
      names:
        kind: K8sRequireNonRoot
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequirenonroot
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          not container.securityContext.runAsNonRoot
          msg := sprintf("Container %s must set runAsNonRoot=true", [container.name])
        }
---
# Apply the constraint
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequireNonRoot
metadata:
  name: require-non-root
spec:
  match:
    kinds:
      - apiGroups: [""]
        kinds: ["Pod"]
    namespaces: ["soc-system"]
```

**Additional policies to enforce:**
- All ingresses must use TLS.
- No `hostPath` volumes.
- Image pull policy must be `Always` in production.
- Resource requests and limits must be set.
- Pod disruption budgets must exist for critical services.

### 2.9 SBOM & Supply Chain

**SBOM generation:**
```bash
# Generate SBOM for each image using Syft
syft soc-backend:$SHA -o spdx-json > sbom-backend.spdx.json
syft soc-frontend:$SHA -o spdx-json > sbom-frontend.spdx.json

# Attest SBOM to image using Cosign
cosign attest --predicate sbom-backend.spdx.json --type spdxjson soc-backend:$SHA
```

**Image signing:**
```bash
# Sign with Cosign + Sigstore (keyless or key-based)
cosign sign soc-backend:$SHA

# Verify before deployment (in admission webhook)
cosign verify soc-backend:$SHA --certificate-identity=ci@soc-system.dev
```

**Supply chain policy:**
- Only deploy images signed by the CI pipeline.
- SBOM stored alongside each release.
- Vulnerability scan results attached to SBOM.
- Regular (monthly) audit of dependency licenses.

### 2.10 Vendor Comparison

| Capability | Open Source (Free) | Commercial (Recommended) | Cloud-Native |
|------------|-------------------|-------------------------|-------------|
| **SAST** | Semgrep Community, Bandit, gosec | Semgrep Pro, Checkmarx, SonarQube | CodeQL (GitHub Advanced Security) |
| **SCA / Dependencies** | Trivy, Grype, OWASP Dependency-Check | Snyk, **Endor Labs** (reachability), Mend | Dependabot (GitHub native) |
| **Secrets** | TruffleHog, GitLeaks | TruffleHog Enterprise, GitGuardian | GitHub Secret Scanning |
| **Container scanning** | Trivy, Grype, Clair | Snyk Container, Prisma Cloud | AWS ECR scanning, GCP Artifact Analysis |
| **IaC scanning** | Checkov, tfsec, Terrascan | Bridgecrew (Prisma Cloud), Snyk IaC | AWS Config Rules, GCP Security Command Center |
| **Runtime** | Falco, Tracee | Datadog CWS, Prisma Cloud Defend, Aqua | AWS GuardDuty, GCP Security Command Center |
| **Policy-as-Code** | OPA Gatekeeper, Kyverno, Conftest | Styra DAS (commercial OPA) | AWS Config, GCP Org Policy |
| **SBOM** | Syft, CycloneDX | Anchore Enterprise, FOSSA | N/A |
| **Image signing** | Cosign + Sigstore | Sigstore + Notary | AWS Signer, GCP Binary Authorization |

**Recommended stack for enterprise:**
- **Endor Labs** for SCA with reachability analysis (most relevant — reduces vulnerability noise by 80%+).
- **Semgrep Pro** for SAST with custom rules (RBAC checks, tenant isolation checks).
- **TruffleHog** for secrets (open source is sufficient).
- **Trivy** for container + IaC scanning (open source is sufficient).
- **Falco** for runtime security (open source is sufficient, or Datadog CWS if already using Datadog).
- **OPA Gatekeeper** for policy-as-code (open source is sufficient).

---

*This document covers Sections 5–6 of the SOC Agent System Architecture v2.*
*See also:*
- *`SOC_System_Architecture_v2_Core.md` — Sections 1–3 (Architecture, Enterprise, Cloud)*
- *`SOC_System_Architecture_v2_Runbooks.md` — Section 4 (Runbooks)*
