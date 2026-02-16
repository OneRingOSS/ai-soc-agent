#!/bin/bash
# Verify K8s Observability Stack
# Tests that Prometheus, Grafana, Jaeger, and Loki are collecting data

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

# Port-forward cleanup
cleanup_port_forwards() {
    pkill -f "kubectl port-forward.*observability" 2>/dev/null || true
    pkill -f "kubectl port-forward.*soc-agent-test" 2>/dev/null || true
}

trap cleanup_port_forwards EXIT

log_section "Verifying K8s Observability Stack"
echo ""

# 1. Check Prometheus is scraping backend
log_info "Testing Prometheus metrics collection..."
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 >/dev/null 2>&1 &
sleep 3

# Query Prometheus for backend metrics
METRICS=$(curl -s "http://localhost:9090/api/v1/query?query=up{job='soc-agent-backend'}" | grep -o '"value":\[.*\]' || echo "")
if [ -n "$METRICS" ]; then
    log_success "Prometheus is scraping backend metrics"
else
    log_error "Prometheus is NOT scraping backend metrics"
fi

# 2. Check Grafana is accessible
log_info "Testing Grafana accessibility..."
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 >/dev/null 2>&1 &
sleep 3

if curl -s http://localhost:3000/api/health | grep -q "ok"; then
    log_success "Grafana is accessible"
else
    log_error "Grafana is NOT accessible"
fi

# 3. Check Jaeger is accessible
log_info "Testing Jaeger accessibility..."
kubectl port-forward -n observability svc/jaeger-query 16686:16686 >/dev/null 2>&1 &
sleep 3

if curl -s http://localhost:16686/ | grep -q "Jaeger"; then
    log_success "Jaeger is accessible"
else
    log_error "Jaeger is NOT accessible"
fi

# 4. Check Loki is accessible
log_info "Testing Loki accessibility..."
kubectl port-forward -n observability svc/loki 3100:3100 >/dev/null 2>&1 &
sleep 3

if curl -s http://localhost:3100/ready | grep -q "ready"; then
    log_success "Loki is accessible"
else
    log_error "Loki is NOT accessible"
fi

# 5. Generate some traffic to backend
log_info "Generating traffic to backend..."
kubectl port-forward -n soc-agent-test svc/soc-agent-backend 8000:8000 >/dev/null 2>&1 &
sleep 3

for i in {1..10}; do
    curl -s http://localhost:8000/health >/dev/null
    curl -s http://localhost:8000/api/threats >/dev/null
done

log_success "Generated 20 requests to backend"

# 6. Wait for metrics to be scraped
log_info "Waiting for Prometheus to scrape metrics (15s)..."
sleep 15

# 7. Verify metrics are being collected
BACKEND_REQUESTS=$(curl -s "http://localhost:9090/api/v1/query?query=http_requests_total" | grep -o '"value":\[.*\]' || echo "")
if [ -n "$BACKEND_REQUESTS" ]; then
    log_success "Backend request metrics are being collected"
else
    log_error "Backend request metrics NOT found"
fi

echo ""
log_section "Verification Complete"
echo ""
log_info "Access dashboards:"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  Jaeger:     http://localhost:16686"
echo ""
log_info "Port-forwards are still running. Press Ctrl+C to stop."
echo ""

# Keep port-forwards alive
wait

