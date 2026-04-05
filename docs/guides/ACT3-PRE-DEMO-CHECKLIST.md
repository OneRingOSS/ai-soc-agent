# Act 3 Pre-Demo Checklist

**Purpose:** Verify all live demo steps work before presenting  
**Based on:** `SecOps-demo-guide-v6.md` Act 3 (Phases 1-4)  
**Runtime:** 5 minutes to verify

---

## Quick Verification Script

```bash
# Run automated verification
bash soc-agent-system/tests/act3-demo-verification.sh

# Expected: All checks pass ✅
```

---

## Manual Pre-Flight Checks

### ✅ Phase 1: The Incident (3 min)

**Tabs to prepare:**
- [ ] **Tab 1:** `.github/workflows/ci.yml` open (line 15-25 showing SHA-pinned actions)
- [ ] **Tab 2:** Terminal in `soc-agent-system/` ready to run `make quality-gate`
- [ ] **Tab 3:** `SECURITY-INCIDENT-RESPONSE.md` open (Incident #1: Trivy)

**Live command test:**
```bash
cd soc-agent-system
make quality-gate
# Should show: "✅ ALL QUALITY GATES PASSED (8 checks)"
```

**Verify outputs:**
- ✅ Linting passes
- ✅ Unit tests: 47 passing
- ✅ Secret scanning: 0 secrets
- ✅ Dependency scanning: 5 known CVEs documented
- ✅ Workflow scanning: informational warnings
- ✅ Lockfile validation: clean
- ✅ Container scanning: no CRITICAL vulns

---

### ✅ Phase 2: Git Log (2 min)

**Tab to prepare:**
- [ ] Terminal in repo root

**Live command test:**
```bash
git log --oneline -20
# Should show commits like:
#   security(P1.1): add K8s secrets encryption
#   security(P1.2): implement seccomp RuntimeDefault
#   docs(tier-3b): STRIDE framework analysis
#   ...15+ security/hardening commits
```

**Talking points:**
- "Here's the progression from reactive to proactive security"
- "Each commit represents a tier of hardening"
- "Notice the test-gated approach - every change has tests"

---

### ✅ Phase 3: Enforcement Layer (3 min)

#### OPA Gatekeeper Demo

**Prerequisites (if demoing live K8s):**
```bash
# Verify OPA is installed
kubectl get pods -n gatekeeper-system
# Should show: gatekeeper-controller-manager running

# Verify constraints exist
kubectl get constraints
# Should show 3 constraints if OPA deployed
```

**Live rejection demo:**
```bash
kubectl apply -f soc-agent-system/k8s/demo-artifacts/bad-pod.yaml
# Should REJECT with 3 violations:
#   [deny-serviceaccount-automount]
#   [require-seccomp-profile]
#   [require-resource-limits]
```

#### Sealed Secrets Demo

**Tab to prepare:**
- [ ] `soc-agent-system/k8s/secrets-encryption/README.md` open

**Talking points:**
- "We use Sealed Secrets for GitOps-friendly encryption"
- "Zero vendor lock-in - 100% open source"
- "Controller auto-rotates keys every 30 days"

**Live command (if cluster available):**
```bash
kubectl get sealedsecret -n soc-agent-demo
# Shows encrypted secrets stored in cluster
```

#### SBOM & Provenance Demo

**Tab to prepare:**
- [ ] GitHub Actions run showing SBOM artifact

**Talking points:**
- "SBOM generated on every release for supply chain transparency"
- "SLSA provenance tracks build integrity"

---

### ✅ Phase 4: Threat Model (2 min)

**Tab to prepare:**
- [ ] `docs/specs/THREAT_MODEL.md` open at Section 7 (TODO table)

**Verify sections exist:**
```bash
grep -n "## 7. Planned Mitigations" docs/specs/THREAT_MODEL.md
# Should show line number ~850

grep -n "STRIDE Summary by Boundary" docs/specs/THREAT_MODEL.md
# Should show line number ~200
```

**Talking points:**
- "STRIDE-compliant threat model - industry standard"
- "42 threats analyzed (7 boundaries × 6 categories)"
- "Section 7 shows our roadmap - what's next"

**Sections to highlight:**
- Table of Contents (shows scope)
- STRIDE Summary Matrix (shows systematic coverage)
- Section 3.2: AG-1 & AG-2 (unique differentiators)
- Section 7: P1/P2 TODOs (shows long-term thinking)

---

## Pre-Demo Environment Setup

### Terminal Setup (4 tabs)

**Tab 1:** `.github/workflows/ci.yml`
```bash
code .github/workflows/ci.yml
# Scroll to line 15 (SHA-pinned actions)
```

**Tab 2:** Ready to run make quality-gate
```bash
cd soc-agent-system
# Don't run yet - save for live demo
```

**Tab 3:** SECURITY-INCIDENT-RESPONSE.md
```bash
code SECURITY-INCIDENT-RESPONSE.md
# Scroll to Incident #1
```

**Tab 4:** Git log terminal
```bash
# Ready to run: git log --oneline -20
```

---

## What Can Go Wrong & Mitigation

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `make quality-gate` fails | Low | Run once before demo, fix any issues |
| K8s cluster not available | Medium | Say "In production we'd see..." and show YAML |
| pip-audit finds new CVE | Low | Expected - show .pip-audit-ignore.yaml |
| Git log doesn't show commits | Low | Verify branch: `git log main..feature/security-hygiene-improvements` |

---

## Backup Plan (No K8s Access)

If OPA/Sealed Secrets can't demo live:

1. **Show YAML files instead:**
   - `bad-pod.yaml` - "This would be rejected..."
   - `sealed-secrets-setup.sh` - "Here's our setup script..."
   
2. **Show screenshots:**
   - Prepare screenshot of OPA rejection
   - Prepare screenshot of sealed secret listing

3. **Emphasize documentation:**
   - "We have executable scripts ready for production"
   - "README.md shows comparison of 3 OSS solutions"

---

## Final Pre-Demo Checklist

- [ ] Run `bash soc-agent-system/tests/act3-demo-verification.sh` - all pass
- [ ] Run `make quality-gate` once - confirm it works
- [ ] Run `git log --oneline -20` - confirm commits show
- [ ] Open all 4 tabs in correct windows
- [ ] Scroll THREAT_MODEL.md to Section 7 beforehand
- [ ] If demoing K8s: verify cluster access with `kubectl get nodes`
- [ ] Have `bad-pod.yaml` ready to `kubectl apply`

---

## Time Allocation

| Phase | Duration | Critical? |
|-------|----------|-----------|
| Phase 1: Incident | 3 min | ✅ Yes |
| Phase 2: Git Log | 2 min | ✅ Yes |
| Phase 3: Enforcement | 3 min | 🟡 K8s optional |
| Phase 4: Threat Model | 2 min | ✅ Yes |
| **Total** | **10 min** | |

**If running over:** Skip Phase 3 K8s live demo, show YAML files instead

---

**You're ready for the demo! 🎉**
