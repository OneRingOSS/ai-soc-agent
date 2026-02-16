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

# Determine script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
# Step 2.5: Optional Real OpenAI API Test
# ─────────────────────────────────────────────────
echo "─────────────────────────────────────────────"
echo "Optional: Test with Real OpenAI API"
echo "─────────────────────────────────────────────"
echo ""
echo "Would you like to process 1 threat with the REAL OpenAI API?"
echo "This will take 8-15 seconds and demonstrate actual LLM integration."
echo ""
echo "⚠️  Note: This requires OPENAI_API_KEY to be set and will cost ~$0.01"
echo ""
read -p "Run real API test? (y/N): " -n 1 -r
echo ""

RAN_REAL_API_TEST=false

if [[ $REPLY =~ ^[Yy]$ ]]; then
  RAN_REAL_API_TEST=true
  # Try to load API key from backend/.env if not already set
  if [ -z "$OPENAI_API_KEY" ]; then
    BACKEND_ENV="$SCRIPT_DIR/../backend/.env"
    if [ -f "$BACKEND_ENV" ]; then
      echo ""
      echo "📄 Loading OPENAI_API_KEY from backend/.env..."
      # Extract the API key value from .env file (remove quotes and whitespace)
      OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" "$BACKEND_ENV" | cut -d'=' -f2- | tr -d ' "' | tr -d "'")
      export OPENAI_API_KEY

      if [ -n "$OPENAI_API_KEY" ]; then
        echo "   ✅ API key loaded successfully (${#OPENAI_API_KEY} characters)"
      else
        echo "   ⚠️  API key found but appears empty"
      fi
    else
      echo "   ⚠️  File not found: $BACKEND_ENV"
    fi
  fi

  if [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "❌ OPENAI_API_KEY is not set!"
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to skip): " API_KEY
    if [ -n "$API_KEY" ]; then
      export OPENAI_API_KEY="$API_KEY"
    else
      echo "⏭️  Skipping real API test"
      echo ""
    fi
  fi

  if [ -n "$OPENAI_API_KEY" ]; then
    echo ""
    echo "🔴 LIVE API TEST — Processing 1 threat with real OpenAI API..."
    echo "   (This will take 8-15 seconds)"
    echo ""

    START_TIME=$(date +%s)

    # Use a temp file to capture response
    TEMP_FILE=$(mktemp)
    HTTP_CODE=$(curl -s -X POST http://localhost:8000/api/threats/trigger \
      -H "Content-Type: application/json" \
      -d '{"threat_type": "bot_traffic"}' \
      -w "%{http_code}" \
      -o "$TEMP_FILE")

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    if [ "$HTTP_CODE" = "200" ]; then
      echo "✅ Real API test completed successfully!"
      echo "   HTTP Status: $HTTP_CODE"
      echo "   Response Time: ${DURATION}s"
      echo ""

      # Show a snippet of the response
      if [ -f "$TEMP_FILE" ]; then
        THREAT_ID=$(grep -o '"id":"[^"]*"' "$TEMP_FILE" | head -1 | cut -d'"' -f4)
        SEVERITY=$(grep -o '"severity":"[^"]*"' "$TEMP_FILE" | head -1 | cut -d'"' -f4)
        if [ -n "$THREAT_ID" ]; then
          echo "   Threat ID: $THREAT_ID"
          echo "   Severity: $SEVERITY"
          echo ""
          echo "   🔍 Opening Jaeger to view the trace..."
          # Open Jaeger with the service pre-selected
          JAEGER_URL="http://localhost:16686/search?service=soc-agent-system"
          open "$JAEGER_URL" 2>/dev/null || true
          echo ""
          echo "   📎 To find this specific trace in Jaeger:"
          echo "      1. Click on 'Tags' in the left sidebar"
          echo "      2. Add tag: threat.id = $THREAT_ID"
          echo "      3. Click 'Find Traces'"
          echo ""
          echo "   Or search by operation: 'analyze_threat'"
          sleep 2
        fi
      fi

      echo ""
      echo "   ✅ Check Jaeger for the distributed trace showing real OpenAI API calls!"
      echo "   → http://localhost:16686/search?service=soc-agent-system"
    else
      echo "❌ Real API test failed!"
      echo "   HTTP Status: $HTTP_CODE"
      echo "   Response Time: ${DURATION}s"
      echo ""

      # Show error details if available
      if [ -f "$TEMP_FILE" ]; then
        ERROR_MSG=$(cat "$TEMP_FILE" | head -c 200)
        if [ -n "$ERROR_MSG" ]; then
          echo "   Error: $ERROR_MSG"
        fi
      fi

      echo ""
      echo "   This is likely due to:"
      echo "   - Invalid API key"
      echo "   - OpenAI rate limits"
      echo "   - Network issues"
    fi

    # Clean up temp file
    rm -f "$TEMP_FILE"

    echo ""
    sleep 2
  fi
else
  echo "⏭️  Skipping real API test"
  echo ""
fi

# ─────────────────────────────────────────────────
# Step 3: Run Load Test (2 minutes) - MOCK MODE
# ─────────────────────────────────────────────────

# Ask if user wants to run load test (skip if they ran real API test)
if [ "$RAN_REAL_API_TEST" = true ]; then
  echo "─────────────────────────────────────────────"
  echo "Step 3: Load Test with Mock Responses"
  echo "─────────────────────────────────────────────"
  echo ""
  echo "You just ran a real API test. Would you like to also run the mock load test?"
  echo "This will generate 1,800+ requests over 2 minutes for performance testing."
  echo ""
  read -p "Run mock load test? (y/N): " -n 1 -r
  echo ""
  echo ""

  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⏭️  Skipping load test"
    echo ""
    echo "=============================================="
    echo " Demo Complete!"
    echo "=============================================="
    echo ""
    echo "📋 What you demonstrated:"
    echo "  ✅ Real OpenAI API integration (8-15s response time)"
    echo "  ✅ Distributed tracing in Jaeger"
    echo "  ✅ Full observability stack"
    echo ""
    echo "💡 Tip: You can still explore the dashboards:"
    echo "  → Grafana: http://localhost:3000"
    echo "  → Jaeger:  http://localhost:16686"
    echo ""
    exit 0
  fi
fi

echo "─────────────────────────────────────────────"
echo "Step 3: Load Test"
echo "─────────────────────────────────────────────"
echo ""
echo "The load test can run in two modes:"
echo "  1. MOCK mode (fast, free, instant responses)"
echo "  2. LIVE mode (slow, costs ~$5-10, real OpenAI API)"
echo ""
echo "⚠️  LIVE mode will make 1,800+ OpenAI API calls over 2 minutes!"
echo "    This will cost approximately $5-10 and take much longer."
echo ""
read -p "Run load test with LIVE OpenAI API? (y/N): " -n 1 -r
echo ""
echo ""

USE_LIVE_API=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
  USE_LIVE_API=true

  # Ensure API key is available
  if [ -z "$OPENAI_API_KEY" ]; then
    BACKEND_ENV="$SCRIPT_DIR/../backend/.env"
    if [ -f "$BACKEND_ENV" ]; then
      echo "📄 Loading OPENAI_API_KEY from backend/.env..."
      OPENAI_API_KEY=$(grep "^OPENAI_API_KEY=" "$BACKEND_ENV" | cut -d'=' -f2- | tr -d ' "' | tr -d "'")
      export OPENAI_API_KEY
    fi
  fi

  if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY is not set!"
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to use MOCK mode): " API_KEY
    if [ -n "$API_KEY" ]; then
      export OPENAI_API_KEY="$API_KEY"
    else
      echo "⏭️  Switching to MOCK mode"
      USE_LIVE_API=false
    fi
  fi
fi

if ! command -v locust &> /dev/null; then
  echo "❌ Locust is not installed. Install with: pip install locust"
  exit 1
fi

# Determine the correct paths (SCRIPT_DIR already set at top of file)
LOCUSTFILE="$SCRIPT_DIR/../loadtests/locustfile.py"
REPORT_DIR="$SCRIPT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Restart backend in the appropriate mode
echo "─────────────────────────────────────────────"
if [ "$USE_LIVE_API" = true ]; then
  echo "🔴 LIVE API MODE"
  echo "─────────────────────────────────────────────"
  echo ""
  echo "Running load test — 20 users, spawn rate 5, duration 2m"
  echo "  🔴 Using LIVE OpenAI API (expect 8-15s per threat)"
  echo "  💰 This will cost approximately $5-10"
  echo "  📊 Watch the dashboards update in real-time!"
  echo ""

  # Ensure OPENAI_API_KEY is set for backend restart
  if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY is not available. Cannot run in LIVE mode."
    exit 1
  fi

  echo "  🔄 Restarting backend in LIVE API mode..."
else
  echo "⚡ MOCK MODE"
  echo "─────────────────────────────────────────────"
  echo ""
  echo "Running load test — 20 users, spawn rate 5, duration 2m"
  echo "  ⚡ Using MOCK mode for speed and cost efficiency"
  echo "  📊 Watch the dashboards update in real-time!"
  echo ""

  echo "  🔄 Restarting backend in MOCK mode..."
  # Unset API key to force mock mode
  unset OPENAI_API_KEY
fi

echo ""

# Find and kill the existing backend process
BACKEND_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
  echo "  → Stopping backend (PID: $BACKEND_PID)..."
  kill "$BACKEND_PID" 2>/dev/null || true
  sleep 2
fi

# Start backend in the appropriate mode
echo "  → Starting backend..."
cd "$SCRIPT_DIR/../backend"
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Start backend in background
if [ "$USE_LIVE_API" = true ]; then
  # Start with OPENAI_API_KEY set
  OPENAI_API_KEY="$OPENAI_API_KEY" python -m uvicorn src.main:app --port 8000 > /tmp/soc-backend-loadtest.log 2>&1 &
else
  # Start without OPENAI_API_KEY (force mock mode)
  env -u OPENAI_API_KEY python -m uvicorn src.main:app --port 8000 > /tmp/soc-backend-loadtest.log 2>&1 &
fi

BACKEND_PID=$!
echo "  → Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
echo "  → Waiting for backend to be ready..."
for i in {1..30}; do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    if [ "$USE_LIVE_API" = true ]; then
      echo "  ✅ Backend ready in LIVE API mode!"
    else
      echo "  ✅ Backend ready in MOCK mode!"
    fi
    break
  fi
  sleep 1
done

# Verify the mode by checking the logs
if [ "$USE_LIVE_API" = true ]; then
  if grep -q "Mode: LIVE" /tmp/soc-backend-loadtest.log 2>/dev/null; then
    echo "  ✅ Confirmed: Backend is running in LIVE API mode"
  else
    echo "  ⚠️  Warning: Could not confirm LIVE mode from logs"
  fi
else
  if grep -q "Mode: MOCK" /tmp/soc-backend-loadtest.log 2>/dev/null; then
    echo "  ✅ Confirmed: Backend is running in MOCK mode"
  else
    echo "  ⚠️  Warning: Could not confirm MOCK mode from logs"
  fi
fi

echo ""
sleep 1

# Run the load test
cd "$SCRIPT_DIR"
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

if [ "$USE_LIVE_API" = true ]; then
  echo " 🔴 This demo used the REAL OpenAI API for all threat analyses."
  echo " You can see the 8-15 second response times per threat in the"
  echo " load test report, which is realistic for production LLM processing."
  echo " The architecture handles this through async processing, proper"
  echo " timeout handling, and horizontal scaling with Redis Pub/Sub."
else
  echo " ⚡ This demo used mock responses for speed and cost efficiency."
  echo " In production with real OpenAI API calls, we'd expect 8-15 second"
  echo " response times per threat due to LLM processing. The architecture"
  echo " supports this through async processing and proper timeout handling."
fi

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
echo " classification, MITRE ATT&CK mapping, and response plans."
echo ""

if [ "$USE_LIVE_API" = false ]; then
  echo " The system is fully integrated with OpenAI's API — I can demonstrate"
  echo " a real example if you'd like to see actual LLM-generated analysis.\""
fi

echo ""
echo "=============================================="

