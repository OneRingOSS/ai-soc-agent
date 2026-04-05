# Manual Demo Verification Checklist

**Purpose:** Step-by-step manual verification of every demo command before presenting  
**Based on:** SecOps-demo-guide-v6.md - Act 3 (Phases 1-4)  
**Time to Complete:** 15-20 minutes

---

## Pre-Demo Setup (Do This Now)

### Terminal Setup - Open 5 Tabs

- [ ] **Tab 1:** `.github/workflows/ci.yml` (for SHA-pinned actions)
- [ ] **Tab 2:** Terminal in `soc-agent-system/` (for make quality-gate)
- [ ] **Tab 3:** `SECURITY-INCIDENT-RESPONSE.md` (for incident log)
- [ ] **Tab 4:** Terminal in repo root (for git log)
- [ ] **Tab 5:** `docs/specs/THREAT_MODEL.md` (for Section 7 TODO)

### Browser Tab Setup

- [ ] GitHub Actions run showing SBOM artifacts (if available)
- [ ] OPA Gatekeeper docs (backup if K8s unavailable)

---

## Phase 1: The Incident (3 min)

### Tab 1: SHA-Pinned Workflow

**File:** `.github/workflows/ci.yml`

- [ ] Open file in VS Code
- [ ] Scroll to line ~15 (actions/checkout)
- [ ] **VERIFY:** You can see SHA hash like `34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`

**Command to verify:**
```bash
grep "uses: actions/checkout@" .github/workflows/ci.yml
```

**Expected output:**
```
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
```

- [ ] ✅ Output matches

---

### Tab 2: Run make quality-gate LIVE

**Directory:** `soc-agent-system/`

**Command:**
```bash
cd soc-agent-system
make quality-gate
```

**Expected output (should show all 8 checks):**
```
✅ Code linting (ruff) - PASS
✅ Unit tests (pytest) - 47 passing
✅ Secret scanning (TruffleHog) - 0 secrets
✅ Dependency scanning (pip-audit) - 5 known CVEs documented
✅ Workflow scanning (zizmor) - informational warnings
✅ npm lockfile validation - PASS
✅ Container scanning (Trivy) - no CRITICAL vulns
✅ ALL QUALITY GATES PASSED (8 checks)
```

**Checkpoints:**
- [ ] Command completes in <2 minutes
- [ ] Shows "✅ ALL QUALITY GATES PASSED (8 checks)"
- [ ] No errors (warnings are OK)
- [ ] pip-audit shows "5 known CVEs documented" (not failures)

**If it fails:**
- Check if you're in `soc-agent-system/` directory
- Run `make lint` alone first to isolate issue
- Check if tools installed: `which ruff trufflehog pip-audit zizmor`

---

### Tab 3: SECURITY-INCIDENT-RESPONSE.md

**File:** `SECURITY-INCIDENT-RESPONSE.md`

- [ ] Open file in VS Code
- [ ] Scroll to Incident #1
- [ ] **VERIFY:** You can see "Trivy Container Scanner Tag Poisoning"

**Command to verify:**
```bash
grep -A 10 "Incident #1" SECURITY-INCIDENT-RESPONSE.md | head -15
```

**Expected output:**
```
## Incident #1: Trivy Container Scanner Tag Poisoning
**Date:** March 27, 2026
**Severity:** 🔴 HIGH
...
```

- [ ] ✅ Output shows Trivy incident
- [ ] Date is March 27, 2026
- [ ] Severity is HIGH

---

## Phase 2: Git Log (2 min)

### Tab 4: Show Git Progression

**Directory:** Repo root

**Command:**
```bash
git log --oneline -20
```

**Expected output (first ~10 commits):**
```
f681e6e fix(docker): install pip packages globally
f2b667f test: add cluster validation tests
17c17b4 demo: verify Act 3 demo steps
<commit> security(P1.1): add K8s secrets encryption
<commit> security(P1.2): implement seccomp RuntimeDefault
<commit> docs(tier-3b): STRIDE framework analysis
...
```

**Checkpoints:**
- [ ] Shows 20+ commits with security/hardening keywords
- [ ] Recent commits include "P1.2 seccomp", "STRIDE", "tier-3b"
- [ ] Progression shows Friday (Trivy response) → Weekend (hardening)

**Count security commits:**
```bash
git log --oneline --all | grep -iE "tier|security|hardening|seccomp|stride" | wc -l
```

**Expected:** Should show 20+ commits

- [ ] ✅ Count is >20

---

## Phase 3: Enforcement Layer (5 min)

### OPA Gatekeeper Demo (If K8s Cluster Available)

**Prerequisites Check:**
```bash
kubectl cluster-info
```

- [ ] ✅ Cluster is reachable

**Step 1: Show Gatekeeper Running**
```bash
kubectl get pods -n gatekeeper-system
```

**Expected:**
```
NAME                                            READY   STATUS    RESTARTS   AGE
gatekeeper-audit-...                            1/1     Running   0          ...
gatekeeper-controller-manager-...               1/1     Running   0          ...
```

- [ ] ✅ Gatekeeper pods are Running (if installed)
- [ ] ⚠️  If NOT installed: Skip to "Alternative: Show YAML" below

**Step 2: Show Constraints**
```bash
kubectl get constraints
```

**Expected (if OPA deployed):**
```
No resources found  (or list of constraint templates)
```

- [ ] ✅ Command runs without error

**Step 3: Test Rejection (Live Demo)**
```bash
kubectl apply -f soc-agent-system/k8s/demo-artifacts/bad-pod.yaml
```

**Expected output (if OPA constraints exist):**
```
Error from server: admission webhook "validation.gatekeeper.sh" denied the request:
[deny-serviceaccount-automount] Pod bad-pod automounts service account token
[require-seccomp-profile] Pod bad-pod must set securityContext.seccompProfile
[require-resource-limits] Pod bad-pod must set resources.limits
```

- [ ] ✅ Pod is REJECTED with violation messages

**Alternative: Show YAML (If No K8s Access)**

- [ ] Open `soc-agent-system/k8s/demo-artifacts/bad-pod.yaml` in VS Code
- [ ] Point to comments: `# ❌ VIOLATES: ...`
- [ ] Say: "In production, this would be rejected by OPA Gatekeeper"

---

### Sealed Secrets Demo

**Option A: Live K8s (if controller deployed)**
```bash
kubectl get sealedsecret -n soc-agent-demo
```

**Expected:**
```
NAME                  AGE
redis-auth-secret     ...
```

- [ ] ✅ SealedSecret exists (if deployed)

**Option B: Show Documentation (if no controller)**

- [ ] Open `soc-agent-system/k8s/secrets-encryption/README.md`
- [ ] Show comparison matrix (3 open-source solutions)
- [ ] Point to `sealed-secrets-setup.sh` script

**Command to verify script exists:**
```bash
ls -lh soc-agent-system/k8s/secrets-encryption/sealed-secrets-setup.sh
```

**Expected:**
```
-rwxr-xr-x  ... sealed-secrets-setup.sh
```

- [ ] ✅ Script exists and is executable

---

### SBOM Demo

**Option A: Show GitHub Actions Artifacts**

- [ ] Open GitHub Actions tab in browser
- [ ] Navigate to latest workflow run
- [ ] Show "Artifacts" section with SBOM (if generated)

**Option B: Show Workflow YAML**

- [ ] Open `.github/workflows/ci.yml`
- [ ] Scroll to SBOM generation step (if exists)
- [ ] Say: "On release, we generate SBOM in SPDX format"

**Command to verify SBOM tools:**
```bash
which syft || echo "Syft not installed (would generate SBOM in CI)"
```

- [ ] ✅ Command runs

---

## Phase 4: Threat Model (1 min)

### Tab 5: THREAT_MODEL.md - Section 7

**File:** `docs/specs/THREAT_MODEL.md`

**Navigate to Section 7:**
```bash
grep -n "## 7. Planned Mitigations" docs/specs/THREAT_MODEL.md
```

**Expected output:**
```
850:## 7. Planned Mitigations (TODO)
```

- [ ] ✅ Section 7 exists around line 850

**In VS Code:**
- [ ] Jump to line 850 (Cmd+G or Ctrl+G)
- [ ] Scroll to see TODO table with P1/P2 items
- [ ] **VERIFY:** Shows P1.1 (K8s Secrets), P2 items (seccomp, egress proxy, etc.)

**Show STRIDE Summary:**
```bash
grep -n "STRIDE Summary by Boundary" docs/specs/THREAT_MODEL.md
```

**Expected:**
```
220:### STRIDE Summary by Boundary
```

- [ ] ✅ STRIDE section exists around line 220
- [ ] Jump to line 220 in VS Code
- [ ] **VERIFY:** Shows table with S/T/R/I/D/E columns

**Show Overall Risk Rating:**
```bash
grep -A 2 "Overall System Risk" docs/specs/THREAT_MODEL.md
```

**Expected:**
```
| **Overall System Risk** | 🔴 HIGH | 🟡 MEDIUM | **-60% current** (🟢 LOW after P1/P2 TODOs) |
```

- [ ] ✅ Shows MEDIUM risk (honest assessment)
- [ ] Shows target: LOW after P1/P2

---

## Final Verification Summary

### Critical Checkpoints (Must All Pass)

- [ ] `make quality-gate` completes successfully
- [ ] `git log` shows 20+ security commits
- [ ] SHA-pinned workflow visible in `.github/workflows/ci.yml`
- [ ] SECURITY-INCIDENT-RESPONSE.md shows Trivy incident
- [ ] THREAT_MODEL.md Section 7 exists with TODO table
- [ ] THREAT_MODEL.md shows STRIDE summary
- [ ] bad-pod.yaml exists in demo-artifacts/

### Optional Checkpoints (Nice to Have)

- [ ] OPA Gatekeeper running in cluster
- [ ] Sealed Secrets deployed
- [ ] SBOM artifacts in GitHub Actions

---

## Time Estimate Per Phase

| Phase | Verification Time | Demo Time |
|-------|------------------|-----------|
| Phase 1: Incident | 5 min | 3 min |
| Phase 2: Git Log | 2 min | 2 min |
| Phase 3: Enforcement | 5 min | 5 min |
| Phase 4: Threat Model | 3 min | 1 min |
| **Total** | **15 min** | **11 min** |

---

## If Something Fails

### make quality-gate fails
- Run individual targets: `make lint`, `make test`, etc.
- Check tool installation: `which ruff pip-audit`
- Re-run with verbose: `make quality-gate -B`

### git log doesn't show commits
- Check branch: `git log feature/security-hygiene-improvements --oneline -20`
- Commits may be in feature branch, not main

### OPA/Sealed Secrets not available
- **Fallback:** Show YAML files + setup scripts
- Say: "In production, this would be deployed..."

### THREAT_MODEL.md sections missing
- Verify file location: `ls -lh docs/specs/THREAT_MODEL.md`
- Check line numbers updated: `wc -l docs/specs/THREAT_MODEL.md`

---

**After completing this checklist, you'll know EXACTLY what works and what doesn't for the live demo!**

**Next Step:** Run through this checklist NOW before pushing to verify everything.
