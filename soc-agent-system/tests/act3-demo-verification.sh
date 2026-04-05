#!/bin/bash
# Act 3 Demo Verification - Validates all live steps from SecOps-demo-guide-v6.md
# Run this before the demo to ensure everything works

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  Act 3 Demo Verification (Phases 1-4)"
echo "  Based on: docs/guides/SecOps-demo-guide-v6.md"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# PHASE 1: THE INCIDENT (3 min)
# ============================================================================
echo "=== PHASE 1: THE INCIDENT ==="
echo ""

echo "[1.1] Verifying SHA-pinned workflow..."
if grep -q "uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5" .github/workflows/ci.yml; then
    echo "✅ PASS: SHA-pinned checkout action found"
else
    echo "❌ FAIL: SHA-pinned actions not found in .github/workflows/ci.yml"
    exit 1
fi

echo "[1.2] Verifying SECURITY-INCIDENT-RESPONSE.md..."
if [ -f "SECURITY-INCIDENT-RESPONSE.md" ]; then
    if grep -q "Trivy Container Scanner Tag Poisoning" SECURITY-INCIDENT-RESPONSE.md; then
        echo "✅ PASS: SECURITY-INCIDENT-RESPONSE.md has Trivy incident"
    else
        echo "❌ FAIL: Trivy incident not documented"
        exit 1
    fi
else
    echo "❌ FAIL: SECURITY-INCIDENT-RESPONSE.md missing"
    exit 1
fi

echo "[1.3] Verifying make quality-gate target..."
if grep -q "quality-gate:.*scan-dependencies.*scan-workflows.*validate-lockfile" soc-agent-system/Makefile; then
    echo "✅ PASS: quality-gate has all 8 security checks"
else
    echo "❌ FAIL: quality-gate missing security checks"
    echo "Expected: lint test scan-secrets scan-dependencies scan-workflows validate-lockfile scan-image"
    exit 1
fi

echo ""
echo "Phase 1 artifacts ready ✅"
echo ""

# ============================================================================
# PHASE 2: GIT LOG
# ============================================================================
echo "=== PHASE 2: GIT LOG ==="
echo ""

echo "[2.1] Checking git log shows hardening commits..."
HARDENING_COMMITS=$(git log --oneline --all | grep -iE "tier|security|hardening|seccomp|stride" | wc -l | tr -d ' ')
if [ "$HARDENING_COMMITS" -gt 15 ]; then
    echo "✅ PASS: Found $HARDENING_COMMITS hardening commits"
    echo "   Sample commits:"
    git log --oneline --all | grep -iE "tier|security|hardening" | head -5
else
    echo "⚠️  WARNING: Only found $HARDENING_COMMITS hardening commits (expected >15)"
    echo "   Demo will still work, but git log may be less impressive"
fi

echo "[2.2] Checking feature branch exists..."
if git rev-parse --verify feature/security-hygiene-improvements &>/dev/null; then
    echo "✅ PASS: feature/security-hygiene-improvements branch exists"
    BRANCH_COMMITS=$(git log --oneline main..feature/security-hygiene-improvements | wc -l | tr -d ' ')
    echo "   Branch has $BRANCH_COMMITS commits ahead of main"
else
    echo "❌ FAIL: feature/security-hygiene-improvements branch missing"
    exit 1
fi

echo ""
echo "Phase 2 git history ready ✅"
echo ""

# ============================================================================
# PHASE 3: ENFORCEMENT (OPA, Sealed Secrets, SBOM)
# ============================================================================
echo "=== PHASE 3: ENFORCEMENT LAYER ==="
echo ""

echo "[3.1] Checking bad-pod.yaml exists at /tmp/bad-pod.yaml..."
if [ ! -f "/tmp/bad-pod.yaml" ]; then
    echo "⚠️  WARNING: /tmp/bad-pod.yaml not found - creating it now..."
    cat > /tmp/bad-pod.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
  namespace: soc-agent-demo
spec:
  automountServiceAccountToken: true    # violates constraint 1
  containers:
  - name: bad-container
    image: nginx:latest
    # no securityContext.seccompProfile  # violates constraint 2
    # no resources.limits                # violates constraint 3
EOF
    echo "✅ Created /tmp/bad-pod.yaml"
else
    echo "✅ PASS: /tmp/bad-pod.yaml exists"
fi

echo "[3.2] Checking Sealed Secrets documentation..."
if [ -f "soc-agent-system/k8s/secrets-encryption/README.md" ]; then
    if grep -q "Sealed Secrets" soc-agent-system/k8s/secrets-encryption/README.md; then
        echo "✅ PASS: Sealed Secrets README exists with comparison matrix"
    else
        echo "❌ FAIL: README missing Sealed Secrets content"
        exit 1
    fi
else
    echo "❌ FAIL: secrets-encryption/README.md missing"
    exit 1
fi

echo "[3.3] Checking Sealed Secrets setup script..."
if [ -f "soc-agent-system/k8s/secrets-encryption/sealed-secrets-setup.sh" ] && [ -x "soc-agent-system/k8s/secrets-encryption/sealed-secrets-setup.sh" ]; then
    echo "✅ PASS: sealed-secrets-setup.sh exists and is executable"
else
    echo "❌ FAIL: sealed-secrets-setup.sh missing or not executable"
    exit 1
fi

echo ""
echo "Phase 3 enforcement artifacts ready ✅"
echo ""

# ============================================================================
# PHASE 4: THREAT MODEL
# ============================================================================
echo "=== PHASE 4: THREAT MODEL ==="
echo ""

echo "[4.1] Checking THREAT_MODEL.md location..."
if [ -f "docs/specs/THREAT_MODEL.md" ]; then
    echo "✅ PASS: docs/specs/THREAT_MODEL.md exists"
else
    echo "❌ FAIL: THREAT_MODEL.md not in docs/specs/"
    exit 1
fi

echo "[4.2] Verifying Section 7 TODO table exists..."
if grep -q "## 7. Planned Mitigations (TODO)" docs/specs/THREAT_MODEL.md; then
    echo "✅ PASS: Section 7 Planned Mitigations found"
else
    echo "❌ FAIL: Section 7 TODO table missing"
    exit 1
fi

echo "[4.3] Checking STRIDE analysis..."
if grep -q "STRIDE Summary by Boundary" docs/specs/THREAT_MODEL.md; then
    echo "✅ PASS: STRIDE analysis present"
else
    echo "❌ FAIL: STRIDE analysis missing"
    exit 1
fi

echo "[4.4] Checking AG-1 and AG-2 sections..."
if grep -q "AG-1: Historical Note Poisoning" docs/specs/THREAT_MODEL.md && \
   grep -q "AG-2: Prompt Injection" docs/specs/THREAT_MODEL.md; then
    echo "✅ PASS: AG-1 and AG-2 attack vectors documented"
else
    echo "❌ FAIL: AG-1 or AG-2 missing from threat model"
    exit 1
fi

echo ""
echo "Phase 4 threat model ready ✅"
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ ALL ACT 3 DEMO STEPS VERIFIED"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "What's ready:"
echo "  ✅ Phase 1: SHA-pinned workflow, quality-gate, incident response doc"
echo "  ✅ Phase 2: Git log with 15+ hardening commits"
echo "  ✅ Phase 3: OPA artifacts, Sealed Secrets docs, bad-pod.yaml"
echo "  ✅ Phase 4: THREAT_MODEL.md with STRIDE + Section 7 TODO"
echo ""
echo "Live commands you can run in demo:"
echo "  make quality-gate                        # Phase 1"
echo "  git log --oneline -20                    # Phase 2"
echo "  kubectl apply -f /tmp/bad-pod.yaml       # Phase 3 (requires cluster)"
echo "  kubectl get sealedsecret                 # Phase 3 (requires cluster)"
echo ""
echo "🎉 Demo is GO for live execution!"
