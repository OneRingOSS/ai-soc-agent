#!/bin/bash
# Test script for P1.2: Seccomp profiles validation
# Validates that all deployments have RuntimeDefault seccomp profiles

set -e

CHART_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$CHART_DIR"

echo "=== P1.2: Seccomp Profile Validation Tests ==="
echo ""

# Test 1: Render Helm chart
echo "[TEST 1] Rendering Helm chart..."
RENDERED=$(helm template test . 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ FAIL: Helm template rendering failed"
    echo "$RENDERED"
    exit 1
fi
echo "✅ PASS: Helm chart renders successfully"
echo ""

# Test 2: Check all seccomp profiles (3 pods × 2 levels = 6 total)
echo "[TEST 2] Checking RuntimeDefault seccomp profiles..."
SECCOMP_COUNT=$(echo "$RENDERED" | grep "type: RuntimeDefault" | wc -l | tr -d ' ')
if [ "$SECCOMP_COUNT" -lt 6 ]; then
    echo "❌ FAIL: Expected 6 seccomp profiles (3 pods × 2 levels), found $SECCOMP_COUNT"
    echo "$RENDERED" | grep -B 5 -A 2 "seccompProfile"
    exit 1
fi
echo "✅ PASS: Found $SECCOMP_COUNT RuntimeDefault seccomp profiles (3 pods + 3 containers)"
echo ""

# Test 3: Check allowPrivilegeEscalation: false
echo "[TEST 3] Checking allowPrivilegeEscalation: false on all containers..."
ESCALATION_COUNT=$(echo "$RENDERED" | grep "allowPrivilegeEscalation: false" | wc -l)
if [ "$ESCALATION_COUNT" -lt 3 ]; then
    echo "❌ FAIL: Expected 3 allowPrivilegeEscalation: false (backend, frontend, redis), found $ESCALATION_COUNT"
    exit 1
fi
echo "✅ PASS: All containers have allowPrivilegeEscalation: false"
echo ""

# Test 4: Check capabilities dropped
echo "[TEST 4] Checking capabilities drop ALL on all containers..."
DROP_ALL_COUNT=$(echo "$RENDERED" | grep -A 1 "drop:" | grep "ALL" | wc -l)
if [ "$DROP_ALL_COUNT" -lt 3 ]; then
    echo "❌ FAIL: Expected 3 'drop: ALL' (backend, frontend, redis), found $DROP_ALL_COUNT"
    exit 1
fi
echo "✅ PASS: All containers drop ALL capabilities"
echo ""

# Test 5: Check runAsNonRoot
echo "[TEST 5] Checking runAsNonRoot: true on all pods..."
RUN_AS_NON_ROOT=$(echo "$RENDERED" | grep "runAsNonRoot: true" | wc -l)
if [ "$RUN_AS_NON_ROOT" -lt 6 ]; then
    echo "❌ FAIL: Expected 6 runAsNonRoot: true (3 pods + 3 containers), found $RUN_AS_NON_ROOT"
    exit 1
fi
echo "✅ PASS: All pods and containers run as non-root"
echo ""

# Summary
echo "=== P1.2 Seccomp Profile Test Summary ==="
echo "✅ 5/5 tests passed"
echo ""
echo "Security controls validated:"
echo "  - RuntimeDefault seccomp on all 3 pods (blocks /proc/pid/mem, ptrace, etc.)"
echo "  - allowPrivilegeEscalation: false on all 3 containers"
echo "  - Capabilities dropped to NONE on all 3 containers"
echo "  - runAsNonRoot: true on all 3 pods + containers"
echo ""
echo "✅ P1.2: Seccomp profiles fully implemented and tested!"
