# Threat Model Corrections Summary

**Date:** April 6, 2026  
**Document:** `docs/specs/THREAT_MODEL.md`  
**Reason:** Align risk ratings with residual risk reality; correct inconsistencies between sections

---

## Issues Identified and Fixed

### ✅ Issue 1: Section 10.1 Incorrectly Claimed LOW Risk (CRITICAL)

**Problem:**  
Section 10.1 stated **"Overall Risk Level: 🟢 LOW (post-hardening)"** — but this contradicted:
- Executive Summary: 🟡 MEDIUM (post-hardening, pending P1/P2 TODOs)
- Section 6.1 table: Overall System Risk = 🟡 MEDIUM
- Section 6.2: 5 accepted residual risks, all 🟡 MEDIUM

**Root Cause:**  
Section 10.1 was aspirational (target state) instead of descriptive (current state).

**Fix Applied:**
```diff
- **Overall Risk Level:** 🟢 **LOW** (post-hardening)
+ **Overall Risk Level:** 🟡 **MEDIUM** (post-hardening, pending P1/P2 TODOs)
+ **Note:** Current 🟡 MEDIUM risk reflects 5 accepted residual risks (Section 6.2). 
+ Target risk level is 🟢 LOW after completing P1 production blockers (etcd encryption) 
+ and P2 high-value hardening (seccomp, egress proxy, LLM output scanning).
```

**Impact:** Document now correctly reflects that MEDIUM risk is the honest current state.

---

### ✅ Issue 2: Section 10.2 Used Checkmarks for Incomplete TODOs (CRITICAL)

**Problem:**  
Production deployment checklist showed ✅ for items that are TODOs:
- etcd encryption at rest (not implemented)
- seccomp profiles (partially implemented)
- Python 3.10+ upgrade (not started)
- Falco, egress proxy, LLM output scanning (all pending)

**Root Cause:**  
Checklist format implied completion when items are still requirements.

**Fix Applied:**
```diff
- 1. ✅ Implement K8s Secrets encryption at rest (P1)
+ 1. ⬜ **Required:** Implement K8s Secrets encryption at rest (P1) — etcd encryption pending

- 2. ✅ Apply seccomp profiles to all pods (P2)
+ 2. ⬜ **Required:** Apply seccomp profiles to all pods (P2) — OPA enforcement active, pod specs need annotation

  [Similar for all TODO items]
+ 2. ✅ **Implemented:** Generate SBOMs for all releases (P3) — CycloneDX + SPDX active as of v3.1
```

**Impact:** Clear distinction between implemented (✅) and required (⬜) items.

---

### ✅ Issue 3: K8s Runtime Boundary Incorrectly Rated LOW with P1 Blocker Open (HIGH)

**Problem:**  
Section 1.4 showed **Residual Risk: 🟢 LOW** despite etcd encryption being a P1 production blocker.

**Root Cause:**  
Sealed Secrets partially mitigates (Git leaks), but etcd at-rest encryption is still pending.

**Fix Applied:**
```diff
- **Residual Risk:** 🟢 LOW (resource limits planned for DoS)
+ **Residual Risk:** 🟡 MEDIUM (Sealed Secrets addresses Git leaks, etcd at-rest encryption pending — P1 blocker)
```

**Cascading Fix:** STRIDE Summary table updated:
```diff
- | **K8s Runtime** | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 🟢 LOW |
+ | **K8s Runtime** | ✅ | ✅ | ✅ | ✅ | 🟡 | ✅ | 🟡 MEDIUM |
```

**Impact:** Boundary risk now reflects P1 blocker status.

---

### ✅ Issue 4: Section 6.1 Post-Hardening Column Showed ALL GREEN (CRITICAL)

**Problem:**  
Table showed 🟢 LOW for all categories post-hardening, ignoring 5 MEDIUM residual risks:
- SC-3.1: 5 Python CVEs
- INF-3: /proc/pid/mem exfiltration
- NET-2: LLM payload exfiltration
- NET-3: DNS rebinding
- AG-3: Novel LLM manipulation

**Root Cause:**  
Post-hardening column showed ideal state, not residual-adjusted state.

**Fix Applied:**
Completely rewrote table to reflect **residual-adjusted posture**:

| Risk Category | Pre-Hardening | Post-Hardening (Current) | Residual Risk Adjustments |
|---------------|---------------|---------------------------|---------------------------|
| **Supply Chain** | 🔴 HIGH | 🟡 MEDIUM | SC-3.1: 5 accepted CVEs (Py 3.10+ pending) |
| **Application Security** | 🟡 MEDIUM | 🟡 MEDIUM | AG-3: novel LLM output manipulation open |
| **Infrastructure** | 🟡 MEDIUM | 🟡 MEDIUM | INF-3: /proc/pid/mem CI exfiltration open (requires seccomp) |
| **Network Security** | 🟠 MEDIUM-HIGH | 🟡 MEDIUM | NET-2: LLM payload exfiltration; NET-3: DNS rebinding open |
| **Secret Management** | 🔴 HIGH | 🟡 MEDIUM | etcd at-rest encryption open (P1) — Sealed Secrets addresses Git leaks |
| **Overall System Risk** | 🔴 HIGH | 🟡 **MEDIUM** | 🟢 LOW after P1 + P2 TODOs complete |

**Impact:** Risk posture now honestly reflects accepted residual risks.

---

### ✅ Issue 5: Container Boundary EoP Row Showed Partial Despite OPA Enforcement (MEDIUM)

**Problem:**
Section 1.3 Elevation of Privilege row stated:
- **Status:** 🟡 Partial
- **Mitigation:** "Trivy scanning + seccomp (planned)"

But OPA Gatekeeper (ADM-1) now **enforces** seccomp at admission time (v3.1).

**Root Cause:**
Document didn't reflect that OPA closes the enforcement gap.

**Fix Applied:**
```diff
- | **Elevation of Privilege** | Container escape via kernel exploit | Trivy scanning + seccomp (planned) | 🟡 Partial |
+ | **Elevation of Privilege** | Container escape via kernel exploit | Trivy scanning + OPA seccomp enforcement (ADM-1) | ✅ Mitigated* |

+ **Residual Risk:** 🟡 MEDIUM (image signing and provenance planned)
+
+ **\*Note on Seccomp:** OPA Gatekeeper (ADM-1) enforces `seccompProfile.type: RuntimeDefault`
+ at admission time via K8sRequiredProbes constraint. Pod spec templates need seccomp annotation
+ to pass the gate — not a gap, but a deployment step.
```

**Impact:** Correctly reflects that OPA enforcement is active; pod specs just need annotation.

---

### ✅ Issue 6: Section 9 Compliance Table Showed SBOM as TODO (MEDIUM)

**Problem:**
OpenSSF row stated: **"SBOM generation (TODO)"**
But SBOM generation (CycloneDX + SPDX) was implemented in v3.1.

**Root Cause:**
Table not updated after v3.1 release.

**Fix Applied:**
```diff
- | **OpenSSF Best Practices** | Dependency scanning, secret scanning, SBOM | 90% | SBOM generation (TODO) |
+ | **OpenSSF Best Practices** | Dependency scanning, secret scanning, SBOM | 95% | SLSA provenance (TODO) — SBOM ✅ implemented v3.1 |
```

**Impact:** Coverage increased from 90% → 95%; remaining gap is SLSA provenance only.

---

### ✅ Issue 7: INF-3-SECCOMP TODO Showed as Complete Gap (HIGH)

**Problem:**
TODO section stated: **"Gap: No seccomp profile"**
But OPA Gatekeeper (ADM-1) **enforces** seccomp at Kubernetes API level.

**Root Cause:**
Seccomp enforcement and seccomp deployment are two different things:
- **OPA enforcement:** ✅ Active (blocks pods without seccomp)
- **Pod specs:** Deployment step (need annotation to pass OPA gate)

**Fix Applied:**
Rewrote entire INF-3-SECCOMP section:
```diff
- **TODO: INF-3-SECCOMP — Seccomp Profile for CI and K8s Pods**
+ **⚠️ PARTIALLY IMPLEMENTED: INF-3-SECCOMP — Seccomp Profile for CI and K8s Pods**
+ - **Implementation Date:** April 6, 2026 (OPA enforcement active)
+ - **✅ Implemented:** OPA Gatekeeper enforces seccomp at admission time
+ - **⚠️ Deployment Step Required:** Pod specs need seccomp annotation
+ - **Gap:** CI runners (GitHub Actions) still lack seccomp for /proc/pid/mem protection
+ - **Note:** OPA enforcement closes the Kubernetes attack surface; this is a deployment
+   workflow step, not a security gap
```

**Impact:** Clear separation between enforcement (implemented) and deployment (workflow step).

---

## Validation: Consistency Check Passed ✅

After applying all fixes, the document is now **internally consistent**:

### Executive Summary (Section 📊)
- Risk Level: 🟡 MEDIUM ✅

### Section 1.4 (K8s Runtime Boundary)
- Residual Risk: 🟡 MEDIUM ✅

### STRIDE Summary Table
- K8s Runtime Overall Risk: 🟡 MEDIUM ✅

### Section 6.1 (Risk Posture)
- All categories: 🟡 MEDIUM (with residual adjustments) ✅
- Overall System Risk: 🟡 MEDIUM ✅

### Section 6.2 (Residual Risks)
- 5 accepted risks, all 🟡 MEDIUM ✅

### Section 10.1 (Conclusion)
- Overall Risk Level: 🟡 MEDIUM ✅

### Section 10.2 (Recommendations)
- TODOs marked with ⬜ Required ✅
- Implemented items marked with ✅ Implemented ✅

---

## Key Insight: Why MEDIUM Is Correct

**The document now correctly shows 🟡 MEDIUM overall because it honestly accounts for 5 accepted residual risks.**

This is a **sign of a mature threat model**, not an incomplete one:
- ✅ Transparent about what's implemented
- ✅ Honest about what's pending
- ✅ Clear path to LOW risk (complete P1 + P2 TODOs)

A document that claims 🟢 LOW while carrying **open P1 blockers** would be the red flag.

---

## Recommendations

✅ **No Further Changes Required** — document is now accurate and internally consistent.

**Optional Improvements:**
1. Consider adding a "Risk Trend" section showing risk reduction timeline
2. Add visual dashboard showing progress toward 🟢 LOW target
3. Create quarterly review checklist based on Section 10.2

---

**Document Status:** ✅ CORRECTED AND VALIDATED
