# GitHub Issues Created for Threat Model Mitigations

**Date:** April 6, 2026
**Created By:** AI SOC Agent Development Team
**Total Issues:** 9 (1 P1 + 5 P2 + 1 P3 + 2 Chore)

---

## Priority 1 (Production Blockers) — 1 Issue

### Issue #20: [P1] Implement etcd encryption at rest for K8s Secrets
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/20  
**Risk ID:** K8S-SECRETS (partially implemented)  
**Severity:** 🟡 MEDIUM  
**Effort:** 3 days  
**Timeline:** Required before production deployment with real customer data

**Description:**
Sealed Secrets addresses Git leak vector but etcd at-rest encryption is still pending. Two options:
1. Enable etcd encryption with KMS provider (AWS/GCP/Azure)
2. Migrate to External Secrets Operator with HashiCorp Vault

**Risk Reduction:** 🔴 HIGH → 🟢 LOW (completes Secret Management hardening)

---

## Priority 2 (High-Value Hardening) — 5 Issues

### Issue #21: [P2] Upgrade to Python 3.10+ to resolve 5 CVEs (SC-3.1)
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/21  
**Risk ID:** SC-3.1  
**Severity:** 🟡 MEDIUM  
**Effort:** 2-3 days  
**Timeline:** Q3 2026 (post-MVP hardening sprint)

**Description:**
5 Python CVEs require Python 3.10+ upgrade. All are Low-Medium severity, currently documented in `.pip-audit-ignore.yaml`.

**Acceptance Criteria:**
- Upgrade from Python 3.9.6 to 3.10+ (recommend 3.11 or 3.12 LTS)
- Update Docker base images
- Verify all 40+ tests pass
- Remove resolved CVEs from `.pip-audit-ignore.yaml`

**Risk Reduction:** Supply Chain: 🟡 MEDIUM → 🟢 LOW

---

### Issue #22: [P2] Deploy seccomp profiles to all K8s pods (INF-3)
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/22  
**Risk ID:** INF-3  
**Severity:** 🟡 MEDIUM  
**Effort:** 1-2 days  
**Timeline:** Before production K8s deployment

**Description:**
Complete seccomp deployment for K8s pods and CI runners. OPA Gatekeeper enforcement is already active; pod specs need annotation.

**Current Status:**
- ✅ OPA enforces `seccompProfile.type: RuntimeDefault` at admission
- ⚠️ Pod spec templates need seccomp annotation (deployment step)
- ❌ CI runners lack seccomp for `/proc/pid/mem` protection

**Acceptance Criteria:**
- Add seccomp annotations to all pod specs (backend, frontend, redis)
- Add `allowPrivilegeEscalation: false` to all containers
- Research and apply seccomp to CI runners

**Risk Reduction:** Infrastructure: 🟡 MEDIUM → 🟢 LOW

---

### Issue #23: [P2] Deploy egress proxy with certificate pinning (NET-3)
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/23  
**Risk ID:** NET-3  
**Severity:** 🟡 MEDIUM  
**Effort:** 3-5 days  
**Timeline:** Production deployment with sensitive customer data

**Description:**
Implement egress proxy with FQDN-based allowlist and certificate pinning to prevent DNS rebinding attacks.

**Current Gap:**
IP-CIDR NetworkPolicy doesn't prevent malicious domains from resolving to legitimate IPs and then rebinding.

**Solution Options:**
1. Envoy sidecar (recommended)
2. Squid proxy

**Acceptance Criteria:**
- Deploy proxy as sidecar in backend pod
- FQDN allowlist: `api.openai.com`, `www.virustotal.com`
- TLS certificate pinning per vendor
- Block direct egress from application

**Performance:** <50ms added latency per request

**Risk Reduction:** Network Security: 🟡 MEDIUM → 🟢 LOW

---

### Issue #24: [P2] Implement LLM output scanning for exfiltration detection (AG-3, NET-2)
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/24  
**Risk IDs:** AG-3, NET-2  
**Severity:** 🟡 MEDIUM  
**Effort:** 2-3 days  
**Timeline:** Multi-tenant customer data handling

**Description:**
Implement regex and entropy-based classifier to detect covert data exfiltration in LLM responses.

**Detection Patterns:**
- Environment variables (`OPENAI_API_KEY=`, `AWS_SECRET=`)
- IP addresses (IPv4, IPv6)
- Base64-encoded blobs (>50 chars)
- High entropy text (>7.5 bits/char)

**Implementation:**
- Shannon entropy calculation
- Regex pattern matching
- Response quarantine for suspicious outputs
- Prometheus metrics for monitoring

**Performance:** ~5ms per response (acceptable)

**Risk Reduction:**
- Application Security (AG-3): 🟡 MEDIUM → 🟢 LOW
- Network Security (NET-2): 🟡 MEDIUM → 🟢 LOW

---

### Issue #25: [P2] Deploy Falco runtime threat detection for K8s
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/25  
**Risk ID:** RUNTIME-FALCO  
**Severity:** 🟡 MEDIUM  
**Effort:** 2-3 days  
**Timeline:** Production K8s deployment

**Description:**
Deploy Falco for syscall-level runtime threat detection in Kubernetes.

**Custom Rules:**
1. Unexpected outbound connection from backend
2. `/proc/pid/mem` read attempt (CRITICAL)
3. New systemd service from unexpected parent
4. Shell spawned in container
5. Sensitive file access (`/etc/shadow`, service account tokens)

**Integration:**
- Route alerts to `/api/egress-violations`
- Correlate with AdversarialDetector
- Prometheus metrics
- Grafana dashboard

**Performance Overhead:**
- CPU: ~2-5% per node
- Memory: ~200MB per Falco pod

**Risk Reduction:**
- Infrastructure Security: Adds runtime detection layer
- Compliance: NIST 800-190 coverage 75% → 90%
- Incident Response: Detection latency hours → seconds

---

## Summary Statistics

| Priority | Issues | Total Effort | Risk Categories Addressed |
|----------|--------|--------------|---------------------------|
| P1 | 1 | 3 days | Secret Management |
| P2 | 5 | 11-18 days | Supply Chain, Infrastructure, Network, Application |
| **Total** | **6** | **14-21 days** | **All 5 risk categories** |

---

## Risk Reduction Impact

**Current State (with all 6 issues open):**
- Overall System Risk: 🟡 MEDIUM
- 5 accepted residual risks (all 🟡 MEDIUM)

**Target State (with all 6 issues completed):**
- Overall System Risk: 🟢 LOW
- 0 accepted residual risks
- All risk categories: 🟢 LOW

---

## Timeline Overview

**Immediate (Before First Production Customer):**
- Issue #20: etcd encryption (P1) — 3 days

**Q3 2026 (Post-MVP Hardening Sprint):**
- Issue #21: Python 3.10+ upgrade — 2-3 days
- Issue #22: Seccomp profiles — 1-2 days
- Issue #23: Egress proxy — 3-5 days
- Issue #24: LLM output scanning — 2-3 days
- Issue #25: Falco runtime detection — 2-3 days

**Total Sprint Duration:** ~3 weeks (assuming sequential execution, can parallelize some tasks)

---

## GitHub Labels Applied

All issues tagged with:
- `security` (all issues)
- `P1` or `P2` (priority)
- Category-specific: `infrastructure`, `supply-chain`, `network`, `application`, `kubernetes`, `monitoring`, `llm-security`

---

---

## Priority 3 (Compliance & Supply Chain) — 1 Issue

### Issue #27: [P3] Implement SLSA Build Provenance for Docker images
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/27
**Risk ID:** PROVENANCE
**Severity:** 🟡 MEDIUM
**Effort:** 1-2 days
**Timeline:** Post-MVP production hardening sprint (Q3 2026)

**Description:**
Implement SLSA Build Provenance to provide cryptographic proof that Docker images were built from expected source code. Currently, SBOM generation is ✅ implemented but provenance attestation is missing.

**Solution:**
1. Add `slsa-github-generator` to CI workflow
2. Sign Docker images with Sigstore/cosign (keyless OIDC signing)
3. Publish provenance to Rekor transparency log
4. Optional: Add OPA policy to require signed images

**Compliance Impact:**
- SLSA Build Security: L2 (partial) → L3 ✅ (fully compliant)
- OpenSSF Best Practices: 95% → 100% ✅

**Performance:** Negligible (~10-25 seconds added to CI, no runtime overhead)

**Risk Reduction:** Supply Chain: 🟡 MEDIUM → 🟢 LOW, OpenSSF 95% → 100%

---

## Chore Issues (Dependency Management) — 2 Issues

### Issue #26: [Chore] Review and merge Dependabot dependency updates
**URL:** https://github.com/OneRingOSS/ai-soc-agent/issues/26
**Category:** Dependency Management
**Effort:** 1-2 days
**Priority:** Medium

**Description:**
Tracking issue for 6 outstanding Dependabot PRs across frontend, backend, and GitHub Actions.

**PRs to Review:**
1. **PR #17:** globals 16.5.0 → 17.4.0 (frontend dev)
2. **PR #16:** axios 1.13.4 → 1.14.0 (frontend prod)
3. **PR #15:** python-dotenv 1.0.0 → 1.2.2 (backend prod) - ⚠️ May require Python 3.10+ first
4. **PR #9:** pytest 7.4.4 → 9.0.2 (backend test)
5. **PR #7:** docker/setup-buildx-action 3.12.0 → 4.0.0 (CI/CD)
6. **PR #6:** actions/checkout 4.3.1 → 6.0.2 (CI/CD)
7. **PR #5:** actions/upload-artifact 4.4.2 → 7.0.0 (CI/CD)

**Recommended Merge Order:**
1. GitHub Actions updates (#5, #6, #7) - 🟢 LOW risk
2. Backend dev dependencies (#9) - 🟢 LOW risk
3. Frontend dev dependencies (#17) - 🟢 LOW risk
4. Frontend prod dependencies (#16) - 🟡 MEDIUM risk
5. Backend prod dependencies (#15) - 🟠 MEDIUM-HIGH risk (may need Python 3.10+ upgrade)

**Blocker:** PR #15 (python-dotenv) may be blocked by Python 3.9.6 compatibility - consider deferring until Issue #21 is complete

---

## Summary Statistics (Updated)

| Priority | Issues | Total Effort | Risk Categories Addressed |
|----------|--------|--------------|---------------------------|
| P1 | 1 | 3 days | Secret Management |
| P2 | 5 | 11-18 days | Supply Chain, Infrastructure, Network, Application |
| P3 | 1 | 1-2 days | Supply Chain, Compliance |
| Chore | 2 | 2-4 days | Dependency Management |
| **Total** | **9** | **17-27 days** | **All risk categories + dependencies** |

---

## Updated Timeline Overview

**Immediate (Before First Production Customer):**
- Issue #20: etcd encryption (P1) — 3 days

**Q2 2026 (Dependency Hygiene):**
- Issue #26: Dependabot updates — 1-2 days (staged merges)

**Q3 2026 (Post-MVP Hardening Sprint):**
- Issue #21: Python 3.10+ upgrade — 2-3 days
- Issue #22: Seccomp profiles — 1-2 days
- Issue #23: Egress proxy — 3-5 days
- Issue #24: LLM output scanning — 2-3 days
- Issue #25: Falco runtime detection — 2-3 days
- Issue #27: SLSA provenance — 1-2 days

**Total Sprint Duration:** ~4 weeks (assuming some parallelization)

---

## GitHub Labels Applied (Updated)

All issues tagged with appropriate labels:
- `security` (issues #20-25, #27)
- `P1`, `P2`, or `P3` (priority level)
- `chore` (issue #26)
- `dependencies`, `dependabot` (issue #26)
- Category-specific: `infrastructure`, `supply-chain`, `network`, `application`, `kubernetes`, `monitoring`, `llm-security`, `compliance`

---

**Next Steps:**
1. Review and prioritize issues based on production timeline
2. Assign issues to team members
3. Create milestones for P1 (pre-production), P2 (post-MVP), and P3 (compliance)
4. Track progress in GitHub Projects
5. Update threat model as issues are completed
