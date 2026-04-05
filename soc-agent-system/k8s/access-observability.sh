#!/bin/bash
# Observability Stack Access Script
# Sets up port forwards for Grafana, Prometheus, Loki, and Jaeger

set -e

echo "════════════════════════════════════════════════════════════"
echo "  Observability Stack Access Setup"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check if observability namespace exists
if ! kubectl get namespace observability &>/dev/null; then
    echo "❌ Observability namespace not found"
    echo "Please install the observability stack first"
    exit 1
fi

# Function to check if port is already in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t &>/dev/null; then
        echo "⚠️  Port $port already in use"
        return 1
    fi
    return 0
}

# Kill existing port-forwards for observability
echo "[1/5] Cleaning up existing port-forwards..."
pkill -f "kubectl port-forward.*observability" 2>/dev/null || true
sleep 2
echo "✅ Cleaned up old port-forwards"
echo ""

# Set up Grafana port-forward
echo "[2/5] Setting up Grafana access (port 3000)..."
if check_port 3000; then
    kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 > /dev/null 2>&1 &
    GRAFANA_PID=$!
    sleep 2
    echo "✅ Grafana: http://localhost:3000"
    echo "   Username: admin"
    echo "   Password: prom-operator"
else
    echo "⚠️  Grafana port 3000 already in use - skipping"
fi
echo ""

# Set up Prometheus port-forward
echo "[3/5] Setting up Prometheus access (port 9090)..."
if check_port 9090; then
    kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 > /dev/null 2>&1 &
    PROMETHEUS_PID=$!
    sleep 2
    echo "✅ Prometheus: http://localhost:9090"
else
    echo "⚠️  Prometheus port 9090 already in use - skipping"
fi
echo ""

# Set up Loki port-forward
echo "[4/5] Setting up Loki access (port 3100)..."
if check_port 3100; then
    kubectl port-forward -n observability svc/loki 3100:3100 > /dev/null 2>&1 &
    LOKI_PID=$!
    sleep 2
    echo "✅ Loki: http://localhost:3100"
else
    echo "⚠️  Loki port 3100 already in use - skipping"
fi
echo ""

# Set up Jaeger port-forward
echo "[5/5] Setting up Jaeger access (port 16686)..."
if check_port 16686; then
    kubectl port-forward -n observability svc/jaeger 16686:16686 > /dev/null 2>&1 &
    JAEGER_PID=$!
    sleep 2
    echo "✅ Jaeger: http://localhost:16686"
else
    echo "⚠️  Jaeger port 16686 already in use - skipping"
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════"
echo "  ✅ Observability Stack Access Ready!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Access URLs:"
echo "  📊 Grafana:    http://localhost:3000  (admin / prom-operator)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  📝 Loki:       http://localhost:3100"
echo "  🔍 Jaeger:     http://localhost:16686"
echo ""
echo "Pre-configured Grafana Dashboards:"
echo "  • Kubernetes / Compute Resources / Cluster"
echo "  • Kubernetes / Compute Resources / Namespace (Pods)"
echo "  • Loki / Logs (for log aggregation)"
echo "  • Jaeger / Distributed Tracing"
echo ""
echo "To stop port-forwards:"
echo "  pkill -f 'kubectl port-forward.*observability'"
echo ""
echo "Port-forwards will run in background. Press Ctrl+C to keep them running."
echo "Or run 'fg' to bring to foreground and Ctrl+C to stop."
echo ""

# Keep script running to maintain port-forwards
echo "Port-forwards are running. Press Ctrl+C to stop all."
wait
