#!/bin/bash
# =============================================================================
# SOC Agent System — Load Test Verification Script
# =============================================================================
# Runs a 6-step verification to ensure the full stack is healthy and load
# testing infrastructure works correctly.
#
# Usage: bash soc-agent-system/loadtests/verify_loadtest.sh
# Exit:  0 = all checks passed, 1 = one or more checks failed
# =============================================================================
set -uo pipefail

# Track results
PASS=0
FAIL=0
RESULTS=()

pass() { PASS=$((PASS + 1)); RESULTS+=("✓ $1"); echo "  ✓ $1"; }
fail() { FAIL=$((FAIL + 1)); RESULTS+=("✗ $1"); echo "  ✗ $1"; }

echo "=============================================="
echo " SOC Agent System — Verification Suite"
echo "=============================================="
echo ""

# ─────────────────────────────────────────────────
# Step 1: Environment Check
# ─────────────────────────────────────────────────
echo "Step 1/6: Environment Check"

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  pass "Backend (localhost:8000) is running"
else
  fail "Backend (localhost:8000) is NOT running"
fi

if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
  pass "Prometheus (localhost:9090) is running"
else
  fail "Prometheus (localhost:9090) is NOT running"
fi

if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
  pass "Grafana (localhost:3000) is running"
else
  fail "Grafana (localhost:3000) is NOT running"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 2: API Integration Test
# ─────────────────────────────────────────────────
echo "Step 2/6: API Integration Test"

RESPONSE=$(curl -sf -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"threat_type": "bot_traffic"}' 2>&1) || RESPONSE=""

if [ -n "$RESPONSE" ]; then
  if echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
assert 'id' in data, 'missing id'
assert 'signal' in data, 'missing signal'
assert 'severity' in data, 'missing severity'
assert data['signal']['threat_type'] == 'bot_traffic', 'wrong threat_type'
" 2>/dev/null; then
    pass "Trigger API returns valid ThreatAnalysis JSON"
  else
    fail "Trigger API response missing expected fields"
  fi
else
  fail "Trigger API returned empty response or error"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 3: Threat Type Validation
# ─────────────────────────────────────────────────
echo "Step 3/6: Threat Type Validation (6 types)"

THREAT_TYPES=("bot_traffic" "proxy_network" "device_compromise" "anomaly_detection" "rate_limit_breach" "geo_anomaly")

for TTYPE in "${THREAT_TYPES[@]}"; do
  RESP=$(curl -sf -o /dev/null -w "%{http_code}" -X POST \
    http://localhost:8000/api/threats/trigger \
    -H "Content-Type: application/json" \
    -d "{\"threat_type\": \"$TTYPE\"}" 2>&1) || RESP="000"

  if [ "$RESP" = "200" ]; then
    pass "Threat type '$TTYPE' → 200 OK"
  else
    fail "Threat type '$TTYPE' → HTTP $RESP"
  fi
done

echo ""

# ─────────────────────────────────────────────────
# Step 4: Locust Dry Run
# ─────────────────────────────────────────────────
echo "Step 4/6: Locust Dry Run (5 users, 30s)"

if ! command -v locust &> /dev/null; then
  fail "Locust is not installed (pip install locust)"
else
  LOCUST_OUTPUT=$(locust -f soc-agent-system/loadtests/locustfile.py \
    --host=http://localhost:8000 \
    --headless -u 5 -r 1 -t 30s \
    --csv=loadtest-results 2>&1) || true

  # Check if CSV results were generated (primary success indicator)
  if [ -f "loadtest-results_stats.csv" ]; then
    pass "Locust dry run completed (CSV results generated)"

    # Check average response time from the Aggregated row
    AVG_MS=$(tail -1 "loadtest-results_stats.csv" | awk -F',' '{print $6}' 2>/dev/null || echo "")
    if [ -n "$AVG_MS" ] && [ "$AVG_MS" != "Average Response Time" ]; then
      if (( $(echo "${AVG_MS:-9999} < 2000" | bc -l 2>/dev/null || echo 0) )); then
        pass "Average response time ${AVG_MS}ms (< 2000ms threshold)"
      else
        fail "Average response time ${AVG_MS}ms (≥ 2000ms threshold)"
      fi
    fi
  else
    fail "Locust dry run — no CSV results generated"
  fi

  # Clean up CSV files
  rm -f loadtest-results_*.csv 2>/dev/null
fi

echo ""

# ─────────────────────────────────────────────────
# Step 5: Observability Verification
# ─────────────────────────────────────────────────
echo "Step 5/6: Observability Verification"

# Check Prometheus has SOC metrics
PROM_RESULT=$(curl -sf 'http://localhost:9090/api/v1/query?query=soc_threats_processed_total' 2>&1) || PROM_RESULT=""

if [ -n "$PROM_RESULT" ]; then
  PROM_STATUS=$(echo "$PROM_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('ok' if data.get('status') == 'success' else 'fail')
" 2>/dev/null || echo "fail")

  if [ "$PROM_STATUS" = "ok" ]; then
    pass "Prometheus query for soc_threats_processed_total succeeded"
  else
    fail "Prometheus query returned non-success status"
  fi
else
  fail "Prometheus is not reachable or returned empty response"
fi

# Check Jaeger has traces
JAEGER_RESULT=$(curl -sf 'http://localhost:16686/api/traces?service=soc-agent-system&limit=1' 2>&1) || JAEGER_RESULT=""

if [ -n "$JAEGER_RESULT" ]; then
  JAEGER_STATUS=$(echo "$JAEGER_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('ok' if 'data' in data else 'fail')
" 2>/dev/null || echo "fail")

  if [ "$JAEGER_STATUS" = "ok" ]; then
    pass "Jaeger traces found for soc-agent-system"
  else
    fail "Jaeger response missing 'data' field"
  fi
else
  fail "Jaeger (localhost:16686) is not reachable"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 6: Final Report
# ─────────────────────────────────────────────────
echo "=============================================="
echo " Verification Report"
echo "=============================================="
echo ""

for RESULT in "${RESULTS[@]}"; do
  echo "  $RESULT"
done

echo ""
echo "----------------------------------------------"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total:  $((PASS + FAIL))"
echo "----------------------------------------------"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "❌ Verification FAILED — $FAIL check(s) did not pass."
  exit 1
else
  echo ""
  echo "✅ All checks passed — system is ready for load testing."
  exit 0
fi
