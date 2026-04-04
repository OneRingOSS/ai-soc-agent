#!/bin/bash
# Start port-forwarding for observability dashboards
# This script sets up access to Grafana, Prometheus, AlertManager, and Jaeger

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

# Kill any existing port-forwards
log_info "Cleaning up existing port-forwards..."
pkill -f "port-forward.*observability" 2>/dev/null || true
sleep 2

log_section "Starting Observability Dashboards"
echo ""

# Start Grafana
log_info "Starting Grafana on http://localhost:3000..."
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 > /dev/null 2>&1 &
GRAFANA_PID=$!
sleep 2

# Start Prometheus
log_info "Starting Prometheus on http://localhost:9090..."
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 > /dev/null 2>&1 &
PROMETHEUS_PID=$!
sleep 2

# Start AlertManager
log_info "Starting AlertManager on http://localhost:9093..."
kubectl port-forward -n observability svc/kube-prometheus-stack-alertmanager 9093:9093 > /dev/null 2>&1 &
ALERTMANAGER_PID=$!
sleep 2

# Start Jaeger
log_info "Starting Jaeger on http://localhost:16686..."
kubectl port-forward -n observability svc/jaeger 16686:16686 > /dev/null 2>&1 &
JAEGER_PID=$!
sleep 2

echo ""
log_section "Dashboards Ready!"
echo ""
log_success "All dashboards are now accessible:"
echo ""
echo "  📊 Main SOC Agent UI:    http://localhost:8080"
echo "  📈 Grafana Dashboard:    http://localhost:3000"
echo "     - Username: admin"
echo "     - Password: admin"
echo ""
echo "  🔍 Prometheus:           http://localhost:9090"
echo "  🚨 AlertManager:         http://localhost:9093"
echo "  🔗 Jaeger Tracing:       http://localhost:16686"
echo ""
log_info "Port-forward PIDs:"
echo "  - Grafana: $GRAFANA_PID"
echo "  - Prometheus: $PROMETHEUS_PID"
echo "  - AlertManager: $ALERTMANAGER_PID"
echo "  - Jaeger: $JAEGER_PID"
echo ""
log_info "Press Ctrl+C to stop all port-forwards, or run:"
echo "  pkill -f 'port-forward.*observability'"
echo ""

# Wait for user interrupt
trap 'log_info "Stopping port-forwards..."; kill $GRAFANA_PID $PROMETHEUS_PID $ALERTMANAGER_PID $JAEGER_PID 2>/dev/null; exit 0' INT TERM

# Keep script running
wait

