#!/bin/bash
# Test script to generate traffic and WebSocket connections for dashboard verification

set -e

echo "========================================="
echo "Dashboard Metrics Test Script"
echo "========================================="
echo ""

# Port-forward to backend if not already running
if ! pgrep -f "port-forward.*soc-agent-backend.*8000" > /dev/null; then
    echo "Starting port-forward to backend..."
    kubectl port-forward -n soc-agent-test svc/soc-agent-backend 8000:8000 > /dev/null 2>&1 &
    sleep 3
fi

echo "Step 1: Generating HTTP traffic..."
echo "  - Sending 100 requests to various endpoints"
for i in {1..25}; do
    curl -s http://localhost:8000/health > /dev/null
    curl -s http://localhost:8000/metrics > /dev/null
    curl -s http://localhost:8000/api/threats > /dev/null
    curl -s http://localhost:8000/ready > /dev/null
done
echo "  ✓ Generated 100 HTTP requests"
echo ""

echo "Step 2: Creating WebSocket connections..."
echo "  - Opening 5 WebSocket connections (will stay open for 30 seconds)"

# Create WebSocket connections using Python
python3 << 'PYTHON_EOF' &
import asyncio
import websockets
import signal
import sys

connections = []

async def connect_websocket(id):
    try:
        uri = "ws://localhost:8000/ws"
        async with websockets.connect(uri) as websocket:
            print(f"  ✓ WebSocket {id} connected")
            connections.append(websocket)
            # Keep connection alive for 30 seconds
            await asyncio.sleep(30)
            print(f"  - WebSocket {id} closing")
    except Exception as e:
        print(f"  ✗ WebSocket {id} failed: {e}")

async def main():
    tasks = [connect_websocket(i) for i in range(1, 6)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  - WebSocket connections interrupted")
        sys.exit(0)
PYTHON_EOF

WS_PID=$!
sleep 5  # Wait for WebSocket connections to establish

echo ""
echo "Step 3: Verifying metrics in Prometheus..."
echo ""

# Check HTTP request metrics
echo "  HTTP Request Rate:"
HTTP_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[1m]))' | jq -r '.data.result[0].value[1] // "0"')
echo "    Current rate: ${HTTP_RATE} req/sec"

# Check WebSocket connections
echo ""
echo "  WebSocket Connections:"
WS_COUNT=$(curl -s 'http://localhost:9090/api/v1/query?query=sum(soc_active_websocket_connections)' | jq -r '.data.result[0].value[1] // "0"')
echo "    Active connections: ${WS_COUNT}"

# Check active pods
echo ""
echo "  Active Backend Pods:"
POD_COUNT=$(curl -s 'http://localhost:9090/api/v1/query?query=count(count%20by%20(pod)%20(http_requests_total))' | jq -r '.data.result[0].value[1] // "0"')
echo "    Pod count: ${POD_COUNT}"

echo ""
echo "Step 4: Waiting for Prometheus to scrape (15 seconds)..."
sleep 15

echo ""
echo "Step 5: Final metrics check..."
echo ""

# Re-check metrics after scrape
HTTP_RATE=$(curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total[1m]))' | jq -r '.data.result[0].value[1] // "0"')
WS_COUNT=$(curl -s 'http://localhost:9090/api/v1/query?query=sum(soc_active_websocket_connections)' | jq -r '.data.result[0].value[1] // "0"')
POD_COUNT=$(curl -s 'http://localhost:9090/api/v1/query?query=count(count%20by%20(pod)%20(http_requests_total))' | jq -r '.data.result[0].value[1] // "0"')

echo "  HTTP Request Rate: ${HTTP_RATE} req/sec"
echo "  WebSocket Connections: ${WS_COUNT}"
echo "  Active Pods: ${POD_COUNT}"

echo ""
echo "========================================="
echo "✓ Test Complete!"
echo "========================================="
echo ""
echo "Dashboard should now show:"
echo "  - HTTP Request Rate graph with data"
echo "  - Active WebSocket Connections: ${WS_COUNT}"
echo "  - Active Pods: ${POD_COUNT}"
echo "  - Per-pod request rate breakdown"
echo ""
echo "WebSocket connections will close in ~10 seconds..."
echo "Refresh the Grafana dashboard to see the metrics!"
echo ""

# Wait for WebSocket connections to close
wait $WS_PID 2>/dev/null || true

echo "✓ WebSocket connections closed"

