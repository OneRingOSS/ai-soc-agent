#!/bin/bash
# =============================================================================
# SOC Agent System — Live Observability Demo
# =============================================================================
# Interactive demo that opens dashboards, runs a load test, and generates
# an HTML report. Designed for live presentation.
#
# Usage: bash soc-agent-system/demo/run_demo.sh
# =============================================================================
set -e

echo "=== SOC Agent System — Live Observability Demo ==="
echo ""
echo "This demo will:"
echo "  1. Verify the stack is healthy"
echo "  2. Open Grafana, Jaeger, and SOC Dashboard in your browser"
echo "  3. Run a 2-minute load test (20 users, spawn rate 5)"
echo "  4. Generate an HTML report"
echo ""

# ─────────────────────────────────────────────────
# Step 1: Verify Stack Health
# ─────────────────────────────────────────────────
echo "Step 1: Verifying stack health..."

HEALTHY=true

if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "  ✓ Backend (localhost:8000)"
else
  echo "  ✗ Backend (localhost:8000) — not running!"
  HEALTHY=false
fi

if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
  echo "  ✓ Prometheus (localhost:9090)"
else
  echo "  ✗ Prometheus (localhost:9090) — not running!"
  HEALTHY=false
fi

if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
  echo "  ✓ Grafana (localhost:3000)"
else
  echo "  ✗ Grafana (localhost:3000) — not running!"
  HEALTHY=false
fi

if [ "$HEALTHY" = false ]; then
  echo ""
  echo "❌ Stack is not fully healthy. Start services first:"
  echo "   cd soc-agent-system/observability && docker compose up -d"
  echo "   cd soc-agent-system/backend && python -m uvicorn src.main:app --port 8000"
  exit 1
fi

echo ""
echo "✅ All services healthy!"
echo ""

# ─────────────────────────────────────────────────
# Step 2: Open Browser Tabs
# ─────────────────────────────────────────────────
echo "Step 2: Opening dashboards in browser..."

# Grafana SOC Dashboard
open "http://localhost:3000/d/soc-agent-dashboard/soc-agent-system?orgId=1&refresh=5s" 2>/dev/null || true
echo "  → Grafana:       http://localhost:3000"

# Jaeger UI
open "http://localhost:16686/search?service=soc-agent-system" 2>/dev/null || true
echo "  → Jaeger:        http://localhost:16686"

# SOC Dashboard (frontend)
open "http://localhost:5173" 2>/dev/null || true
echo "  → SOC Dashboard: http://localhost:5173"

echo ""
sleep 2

# ─────────────────────────────────────────────────
# Step 3: Run Load Test (2 minutes)
# ─────────────────────────────────────────────────
echo "Step 3: Running load test — 20 users, spawn rate 5, duration 2m"
echo "  Watch the dashboards update in real-time!"
echo ""

if ! command -v locust &> /dev/null; then
  echo "❌ Locust is not installed. Install with: pip install locust"
  exit 1
fi

# Determine the correct paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCUSTFILE="$SCRIPT_DIR/../loadtests/locustfile.py"
REPORT_DIR="$SCRIPT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

locust -f "$LOCUSTFILE" \
  --host=http://localhost:8000 \
  --headless \
  -u 20 -r 5 -t 2m \
  --csv="${REPORT_DIR}/loadtest-${TIMESTAMP}" \
  --html="${REPORT_DIR}/loadtest-report.html" \
  2>&1 | while IFS= read -r line; do
    echo "  [locust] $line"
  done

echo ""

# ─────────────────────────────────────────────────
# Step 4: Generate Report
# ─────────────────────────────────────────────────
echo "Step 4: Report generated!"
echo ""

if [ -f "${REPORT_DIR}/loadtest-report.html" ]; then
  echo "  📊 HTML Report: ${REPORT_DIR}/loadtest-report.html"
  open "${REPORT_DIR}/loadtest-report.html" 2>/dev/null || true
else
  echo "  ⚠  HTML report was not generated (Locust may not support --html flag)"
fi

if [ -f "${REPORT_DIR}/loadtest-${TIMESTAMP}_stats.csv" ]; then
  echo "  📈 CSV Stats:   ${REPORT_DIR}/loadtest-${TIMESTAMP}_stats.csv"
fi

echo ""
echo "=============================================="
echo " Demo Complete!"
echo "=============================================="
echo ""
echo "📋 Narration Script:"
echo "─────────────────────────────────────────────"
echo ""
echo "\"This is our SOC Agent System with full observability."
echo " We just ran a 2-minute load test with 20 concurrent users"
echo " generating all 6 threat types: bot traffic, proxy networks,"
echo " device compromises, anomaly detections, rate limit breaches,"
echo " and geo anomalies."
echo ""
echo " In Grafana, you can see the threat processing rate, agent"
echo " execution latency, and false positive score distribution —"
echo " all updating in real-time from Prometheus metrics."
echo ""
echo " In Jaeger, each threat analysis creates a distributed trace"
echo " showing the full pipeline: ingestion → 5 parallel agents →"
echo " FP analysis → response planning → timeline generation."
echo ""
echo " The SOC Dashboard shows the live threat feed with severity"
echo " classification, MITRE ATT&CK mapping, and response plans.\""
echo ""
echo "=============================================="

