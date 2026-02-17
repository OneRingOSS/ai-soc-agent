#!/bin/bash
# Test script to demonstrate trace correlation between Grafana logs and Jaeger

set -e

echo "========================================="
echo "Trace Correlation Demo Helper"
echo "========================================="
echo ""

# Trigger a single threat analysis to generate a trace
echo "1. Triggering a threat analysis..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "threat_type": "malware_detection",
    "severity": "HIGH",
    "source_ip": "192.168.1.100",
    "customer_name": "Demo Corp"
  }')

echo "✓ Threat triggered"
echo ""

# Extract trace_id from the response (if available in logs)
echo "2. Waiting for trace to be exported to Jaeger (3 seconds)..."
sleep 3
echo "✓ Trace should now be in Jaeger"
echo ""

# Get recent traces from Jaeger
echo "3. Fetching recent traces from Jaeger..."
TRACES=$(curl -s "http://localhost:16686/api/traces?service=soc-agent-system&limit=5&lookback=5m")
TRACE_COUNT=$(echo "$TRACES" | jq -r '.data | length')

if [ "$TRACE_COUNT" -gt 0 ]; then
    echo "✓ Found $TRACE_COUNT recent traces"
    echo ""
    
    # Get the most recent trace ID
    LATEST_TRACE_ID=$(echo "$TRACES" | jq -r '.data[0].traceID')
    echo "4. Most recent trace ID: $LATEST_TRACE_ID"
    echo ""
    
    # Construct Jaeger URL
    JAEGER_URL="http://localhost:16686/trace/$LATEST_TRACE_ID"
    echo "5. Jaeger trace URL:"
    echo "   $JAEGER_URL"
    echo ""
    
    echo "========================================="
    echo "Demo Instructions:"
    echo "========================================="
    echo ""
    echo "1. Open Grafana dashboard:"
    echo "   http://localhost:3000/d/soc-agent-k8s/soc-agent-system-k8s"
    echo ""
    echo "2. Scroll to the 'Recent Logs' panel at the bottom"
    echo ""
    echo "3. Click the PAUSE button (⏸) in the top-right of the logs panel"
    echo "   This stops the live stream so you can click on trace IDs"
    echo ""
    echo "4. Look for a log entry with trace_id: $LATEST_TRACE_ID"
    echo ""
    echo "5. Click on the trace_id value - it will open Jaeger in a new tab"
    echo ""
    echo "6. In Jaeger, you'll see the full distributed trace with:"
    echo "   - HTTP request span"
    echo "   - analyze_threat parent span"
    echo "   - Individual agent spans (running in parallel)"
    echo "   - Response generation span"
    echo ""
    echo "========================================="
    echo ""
    
    # Open Jaeger in browser
    echo "Opening Jaeger UI with the latest trace..."
    if command -v open &> /dev/null; then
        open "$JAEGER_URL"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "$JAEGER_URL"
    else
        echo "Please open this URL manually: $JAEGER_URL"
    fi
else
    echo "⚠ No traces found in Jaeger yet"
    echo "   Try running this script again in a few seconds"
fi

echo ""
echo "========================================="
echo "Tips:"
echo "========================================="
echo "- Dashboard refresh is set to 30s (slower than before)"
echo "- Logs panel shows max 100 lines"
echo "- Use the PAUSE button to stop log streaming"
echo "- Use the time picker to view historical logs"
echo "========================================="

