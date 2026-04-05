# THREAT_MODEL.md — Improvement Spec
## Targeted fixes before JP Harvey interview demo

**File to edit:** `THREAT_MODEL.md`
**Total estimated effort:** ~45 minutes
**Priority:** Complete all 🔴 Critical fixes before showing JP. 🟡 Medium fixes are high-value and quick.

---

## Table of Contents

1. [Fix 1 — Add Table of Contents (navigation)](#fix-1--add-table-of-contents)
2. [Fix 2 — Correct overall risk rating](#fix-2--correct-overall-risk-rating)
3. [Fix 3 — Add missing TODO for Agent Input Spoofing gap](#fix-3--add-missing-todo-for-agent-input-spoofing-gap)
4. [Fix 4 — Update E2E test row from "Manual" to "Automated"](#fix-4--update-e2e-test-row-from-manual-to-automated)
5. [Fix 5 — Add detective compensating control for INF-3](#fix-5--add-detective-compensating-control-for-inf-3)
6. [Fix 6 — Bump NET-2 from P3 to P2 with rationale](#fix-6--bump-net-2-from-p3-to-p2-with-rationale)


---

## Fix 1 — Add Table of Contents

**Severity:** 🟡 Medium (navigation / professionalism)
**Effort:** 5 minutes
**Why:** A 43,000-character threat model without a TOC is hard to navigate in a live interview setting. JP will want to jump directly to sections. A TOC also signals document maturity.

### Where to insert

Immediately after the Executive Summary block (before `## 1. Trust Boundaries & STRIDE Analysis`).

### Content to add

```markdown
---

## Table of Contents

1. [Trust Boundaries & STRIDE Analysis](#1-trust-boundaries--stride-analysis)
   - [1.1 Development Boundary](#11-development-boundary)
   - [1.2 CI/CD Boundary](#12-cicd-boundary)
   - [1.3 Container Boundary](#13-container-boundary)
   - [1.4 Kubernetes Runtime Boundary](#14-kubernetes-runtime-boundary)
   - [1.5 Network Boundary](#15-network-boundary)
   - [1.6 Agent Input Boundary](#16-agent-input-boundary)
   - [1.7 Data Store Boundary](#17-data-store-boundary)
   - [STRIDE Summary by Boundary](#stride-summary-by-boundary)
2. [Threat Actors & Motivations](#2-threat-actors--motivations)
3. [Attack Vectors & Mitigations](#3-attack-vectors--mitigations)
   - [3.1 Supply Chain Layer](#31-supply-chain-layer)
   - [3.2 Application Layer (Agent Manipulation)](#32-application-layer-agent-manipulation)
   - [3.3 Infrastructure Layer](#33-infrastructure-layer)
   - [3.4 Network Layer](#34-network-layer)
   - [3.5 Secret Management](#35-secret-management)
4. [Implemented Controls Matrix](#4-implemented-controls-matrix)
5. [CI/CD Pipeline Security Architecture](#5-cicd-pipeline-security-architecture)
6. [Risk Assessment Summary](#6-risk-assessment-summary)
7. [Planned Mitigations (TODO)](#7-planned-mitigations-todo)
8. [Incident Response History](#8-incident-response-history)
9. [Compliance & Standards Alignment](#9-compliance--standards-alignment)

---
```

---

## Fix 2 — Correct Overall Risk Rating

**Severity:** 🔴 Critical — JP will see the contradiction immediately
**Effort:** 5 minutes
**Why:** Executive Summary declares `🟢 LOW` but the STRIDE Summary table directly below it shows 5 of 7 boundaries at `🟡 MEDIUM` and one `❌ Gap`. A VP of Security reading "Overall Risk: LOW" alongside a table showing 5 MEDIUMs will question your risk calibration judgment before you've said a word.

### Location

`## 📊 Executive Summary` — the `**Risk Level:**` line and the risk improvement table in Section 6.1.

### Change 1: Executive Summary block

**Find:**
```markdown
**Risk Level:** 🟢 **LOW** (post-hardening)
```

**Replace with:**
```markdown
**Risk Level:** 🟡 **MEDIUM** (post-hardening, pending P1/P2 TODOs)
**Target Risk Level:** 🟢 **LOW** (after K8s Secrets, seccomp, egress proxy, and LLM output scanning)
```

### Change 2: Section 6.1 Risk Assessment table — Overall System Risk row

**Find:**
```markdown
| **Overall System Risk** | 🔴 HIGH | 🟢 LOW | **-78% overall** |
```

**Replace with:**
```markdown
| **Overall System Risk** | 🔴 HIGH | 🟡 MEDIUM | **-78% risk reduction — 🟢 LOW pending P1/P2 TODOs** |
```

### Change 3: Section 6.1 — add a clarifying note below the table

**Add after the table:**
```markdown
> **Note on residual posture:** "Post-hardening" reflects the 13 implemented tiers. Five boundaries
> carry 🟡 MEDIUM residual risk due to planned-but-not-yet-implemented controls (K8s Secrets
> encryption, seccomp profiles, egress proxy, LLM output scanning, image signing). These are
> tracked in Section 7 with explicit priorities and effort estimates. The system is production-safe
> for a personal project / demo environment at this risk level; customer data deployment requires
> P1 TODO completion first.
```

---

## Fix 3 — Add Missing TODO for Agent Input Spoofing Gap

**Severity:** 🔴 Critical — only ❌ in the entire document has no corresponding TODO
**Effort:** 15 minutes
**Why:** Section 1.6 STRIDE table has this row:

| Spoofing | Malicious analyst impersonates legitimate note author | (Gap - no note signing) | ❌ Gap |

There is no corresponding entry in Section 7 (Planned Mitigations). JP will scroll there and find nothing. This looks like an untracked gap rather than a deliberate decision.

### Change 1: Update Section 1.6 STRIDE table row

**Find:**
```markdown
| **Spoofing** | Malicious analyst impersonates legitimate note author | (Gap - no note signing) | ❌ Gap |
```

**Replace with:**
```markdown
| **Spoofing** | Malicious analyst impersonates legitimate note author | SIEM audit log provides author provenance (external system); cryptographic note signing planned (TODO: AG-1-NOTE-INTEGRITY) | ⚠️ Planned |
```

### Change 2: Update Section 1.6 Residual Risk line

**Find:**
```markdown
**Residual Risk:** 🟡 MEDIUM (historical note signing gap, LLM output scanning planned)
```

**Replace with:**
```markdown
**Residual Risk:** 🟡 MEDIUM
- Note author integrity: covered by SIEM audit logs (external, read-only to this system); cryptographic signing planned (TODO: AG-1-NOTE-INTEGRITY)
- LLM output scanning: planned (TODO: AG-3-OUTPUT)
```

### Change 3: Add new TODO entry in Section 7, after TODO: AG-3-OUTPUT

```markdown
**TODO: AG-1-NOTE-INTEGRITY — Historical Note Author Integrity**
- **Gap:** No cryptographic verification that analyst notes were written by the attributed author;
  SIEM audit logs provide a detective signal but not a preventive one
- **Risk:** Sophisticated insider could fabricate notes with a valid-looking author field without
  triggering the current AdversarialDetector (which catches structural patterns, not identity fraud)
- **Compensating control today:** SIEM audit log provides author + timestamp provenance (external,
  read-only); AdversarialDetector catches the behavioral pattern of mass fabrication (18+ notes,
  identical structure, service account authorship)
- **Full mitigation:**
  - HMAC-sign each note at creation time using a secret key shared with the SIEM
  - Verify HMAC in HistoricalAgent before notes are admitted to LLM context
  - Notes failing HMAC verification are quarantined and flagged for human review
- **Effort:** Medium (2-3 days — requires SIEM-side signing integration)
- **Priority:** P2
- **Trigger:** Multi-analyst production SIEM integration (not required for single-analyst or
  read-only SIEM configurations)
```

### Change 4: Update STRIDE Summary table — Agent Input Spoofing cell

**Find:**
```markdown
| **Agent Input** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 MEDIUM |
```

**Replace with:**
```markdown
| **Agent Input** | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 MEDIUM |
```

---

## Fix 4 — Update E2E Test Row from "Manual" to "Automated"

**Severity:** 🔴 Critical — direct contradiction with what you show JP in the demo
**Effort:** 5 minutes
**Why:** Section 5.2 End-to-End Testing Strategy table says:

| E2E Tests | Manual | Full workflow (threat → analysis → verdict) | Pre-release |

But the v4 spec has a fully automated E2E test for Tier 3A that starts the backend, posts an egress violation, triggers the adversarial catch scenario, and validates the verdict — all in a `#!/bin/bash set -e` script with no human input. JP will have just watched `make quality-gate` run automated E2E. This row will confuse him.

### Location

Section 5.2, End-to-End Testing Strategy table.

### Change: Replace the E2E Tests row

**Find:**
```markdown
| **E2E Tests** | Manual | Full workflow (threat → analysis → verdict) | Pre-release |
```

**Replace with:**
```markdown
| **E2E Tests (Adversarial)** | pytest + bash | Adversarial attack + infrastructure contradiction + egress correlation (Tier 3A automated script) | Every commit (gated on OPENAI_API_KEY present) |
| **E2E Tests (K8s)** | bash (`k8s/tests/integration-test.sh`) | Full cluster: NetworkPolicy block + egress webhook + API + WebSocket | Pre-deployment (requires Kind cluster) |
| **E2E Tests (Full workflow)** | Semi-automated (`make demo-reset`) | Full threat → 5-agent analysis → verdict with MITRE tagging | Pre-release |
```

### Add below the table:

```markdown
> **Note:** Adversarial E2E tests require `OPENAI_API_KEY` in environment; they are skipped
> (not failed) in CI environments where the key is absent. K8s E2E tests are conditional on a
> running Kind cluster and are non-blocking in CI (marked `continue-on-error: true`).
```

---

## Fix 5 — Add Detective Compensating Control for INF-3

**Severity:** 🟡 Medium — shows layered thinking (preventive + detective + corrective)
**Effort:** 10 minutes
**Why:** Section 3.3 INF-3 correctly marks the `/proc/pid/mem` mitigation as PARTIAL and files
seccomp as a P2 TODO. What's missing is any **detective** layer — if a malicious binary did
execute and read runner memory, there is currently no way to know. A VP of Security will ask
"how would you detect this if it happened?" and the current document has no answer.

### Location

Section 3.3, INF-3 block. After the "Gap:" line and before "Residual Risk:".

### Content to add

**Find:**
```markdown
**Gap:** No seccomp profile blocking `/proc/pid/mem` reads (see TODO: INF-3-SECCOMP)

**Residual Risk:** 🟡 MEDIUM (reduced surface, full mitigation requires seccomp)
```

**Replace with:**
```markdown
**Gap:** No seccomp profile blocking `/proc/pid/mem` reads (see TODO: INF-3-SECCOMP)

**Detective Compensating Control (available now, no implementation required):**
- GitHub Actions provides an audit log of all workflow runs, step durations, and runner assignments
- Anomalous process spawn patterns (unexpected binaries executing during `npm ci` or `pip install`
  steps) are visible in GitHub Actions step logs with `ACTIONS_STEP_DEBUG=true`
- GitHub Advanced Security (if enabled) surfaces unexpected network calls from runners
- For production CI: Datadog CI Visibility or similar APM tools provide syscall-level process
  tree visibility on self-hosted runners
- **Current posture:** Relying on GitHub-hosted runners (ephemeral, destroyed after each job) as
  a containment boundary — even if memory is read, the runner is gone within minutes and secrets
  are rotated on next deployment

**Residual Risk:** 🟡 MEDIUM (reduced surface via SHA-pinning + ephemeral runners; detective layer
available via GitHub audit logs; full preventive mitigation requires seccomp — see TODO P2)
```

---

## Fix 6 — Bump NET-2 from P3 to P2

**Severity:** 🟡 Medium — priority inconsistency undermines risk judgment signal
**Effort:** 5 minutes
**Why:** NET-2 (LLM exfiltration via OpenAI API payload) is marked P3 (Compliance) but:
- The trigger says *"Can implement during Tier 2B hardening sprint"* — implying low effort
- For a system handling security telemetry + insider risk signals, covert exfiltration via
  a legitimate API channel is a higher-priority threat than compliance gaps
- The inconsistency between P3 classification and "low-effort/high-relevance" trigger
  will look like careless prioritization to JP

### Change 1: Section 6.2 Residual Risks table — NET-2 row

**Find:**
```markdown
| **NET-2** | LLM exfiltration via OpenAI API | 🟡 MEDIUM | Input sanitizer blocks injection, payload inspection costly | TODO: Response payload inspection (P3) |
```

**Replace with:**
```markdown
| **NET-2** | LLM exfiltration via OpenAI API | 🟡 MEDIUM | Input sanitizer blocks most injection vectors; payload inspection adds ~5ms per call | TODO: Response payload inspection (P2 — elevated from P3; relevant for any multi-tenant or customer-data deployment) |
```

### Change 2: Section 7 TODO: NET-2-PAYLOAD — update priority and rationale

**Find:**
```markdown
**TODO: NET-2-PAYLOAD**
```

In the TODO block, find and update the priority line:

**Find (within that TODO block):**
```markdown
- **Effort:** Medium (2-3 days)
- **Trigger:** Multi-tenant customer data handling
```

**Replace with:**
```markdown
- **Effort:** Medium (2-3 days; regex + entropy classifier on agent output before persistence)
- **Priority:** P2 (elevated from P3 — any deployment handling security telemetry or analyst
  notes from customer environments should treat covert LLM exfiltration as P2, not a compliance
  concern)
- **Trigger:** Any deployment where agent outputs are persisted or returned to users; earlier
  than originally scoped
```

---


```



---

## Validation Checklist

After making all edits, verify the following before showing JP:

```bash
# 1. TOC links resolve — spot check 3 anchors
grep -n "^## " THREAT_MODEL.md | head -20

# 2. No ❌ remains without a corresponding TODO entry
grep -n "❌" THREAT_MODEL.md

# 3. Overall risk is no longer 🟢 LOW in the Executive Summary
grep -n "Risk Level" THREAT_MODEL.md | head -5

# 4. E2E row no longer says "Manual"
grep -n "Manual" THREAT_MODEL.md

# 5. NET-2 is now P2 in both the residual risks table and TODO block
grep -n "NET-2" THREAT_MODEL.md

# 6. AG-1-NOTE-INTEGRITY TODO exists
grep -n "AG-1-NOTE-INTEGRITY" THREAT_MODEL.md



**Expected clean state:**
- `grep "❌" THREAT_MODEL.md` → returns zero lines (all gaps now ⚠️ Planned or ✅)
- `grep "Risk Level.*LOW" THREAT_MODEL.md` → returns only the "Target Risk Level" line
- `grep "Manual" THREAT_MODEL.md` → returns zero lines in the testing table
- `grep "AG-1-NOTE-INTEGRITY" THREAT_MODEL.md` → returns 2+ lines (STRIDE table + TODO block)
- `grep "NET-2.*P2" THREAT_MODEL.md` → returns 2 lines (residual table + TODO block)

---

*Generated April 4, 2026 — based on review of THREAT_MODEL.md v3.0*
*To be applied before JP Harvey interview demo*
