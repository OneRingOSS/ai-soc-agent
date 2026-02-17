#!/bin/bash
# =============================================================================
# SOC Agent System — K8s Live Demo Script
# =============================================================================
# Run this DURING your interview/demo for a quick interactive demonstration.
# Prerequisites: Run setup_demo.sh first!
#
# Usage: bash soc-agent-system/k8s/demo/run_demo.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
NAMESPACE="soc-agent-demo"
RELEASE_NAME="soc-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=9080
FRONTEND_PORT=9081

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

echo ""
log_section "SOC Agent System — K8s Live Demo"
echo ""

# ─────────────────────────────────────────────────
# Step 1: Verify Environment
# ─────────────────────────────────────────────────
log_section "Step 1: Verifying Environment"
echo ""

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_error "Namespace '$NAMESPACE' not found!"
    echo ""
    echo "Please run the setup script first:"
    echo "  bash soc-agent-system/k8s/demo/setup_demo.sh"
    exit 1
fi

# Check if pods are running
BACKEND_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=soc-backend --field-selector=status.phase=Running -o name | wc -l)
FRONTEND_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=soc-frontend --field-selector=status.phase=Running -o name | wc -l)
REDIS_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=redis --field-selector=status.phase=Running -o name | wc -l)

if [ "$BACKEND_PODS" -lt 1 ] || [ "$FRONTEND_PODS" -lt 1 ] || [ "$REDIS_PODS" -lt 1 ]; then
    log_error "Not all pods are running!"
    echo ""
    kubectl get pods -n "$NAMESPACE"
    echo ""
    echo "Please run the setup script first:"
    echo "  bash soc-agent-system/k8s/demo/setup_demo.sh"
    exit 1
fi

log_success "Backend pods: $BACKEND_PODS"
log_success "Frontend pods: $FRONTEND_PODS"
log_success "Redis pods: $REDIS_PODS"
echo ""

# Show HPA status
log_info "HPA Status:"
kubectl get hpa -n "$NAMESPACE" 2>/dev/null || log_warning "HPA not found (may not be configured)"
echo ""

# ─────────────────────────────────────────────────
# Step 2: Set Up Port Forwards
# ─────────────────────────────────────────────────
log_section "Step 2: Setting Up Port Forwards"
echo ""

# Kill any existing port-forwards
pkill -f "kubectl port-forward.*$NAMESPACE" 2>/dev/null || true
sleep 2

log_info "Starting port-forward to backend (localhost:$BACKEND_PORT)..."
kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 > /dev/null 2>&1 &
BACKEND_PF_PID=$!

log_info "Starting port-forward to frontend (localhost:$FRONTEND_PORT)..."
kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-frontend $FRONTEND_PORT:80 > /dev/null 2>&1 &
FRONTEND_PF_PID=$!

# Wait for port-forwards to be ready
sleep 3

# Verify connectivity
if curl -s http://localhost:$BACKEND_PORT/health | grep -q "healthy"; then
    log_success "Backend accessible at http://localhost:$BACKEND_PORT"
else
    log_error "Backend health check failed"
    exit 1
fi

if curl -s http://localhost:$FRONTEND_PORT/ | grep -q "<!DOCTYPE html>"; then
    log_success "Frontend accessible at http://localhost:$FRONTEND_PORT"
else
    log_warning "Frontend check failed (may still be loading)"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 3: Open Dashboards
# ─────────────────────────────────────────────────
log_section "Step 3: Opening Dashboards"
echo ""

log_info "Opening SOC Dashboard in browser..."
open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true
echo "  → SOC Dashboard: http://localhost:$FRONTEND_PORT"
echo ""

log_info "You can also access via Ingress:"
echo "  → http://localhost:8080/ (with Host: soc-agent.local header)"
echo "  → curl -H \"Host: soc-agent.local\" http://localhost:8080/"
echo ""

sleep 2

# ─────────────────────────────────────────────────
# Step 4: Show Current State
# ─────────────────────────────────────────────────
log_section "Step 4: Current System State"
echo ""

log_info "Fetching current threats..."
THREAT_COUNT=$(curl -s http://localhost:$BACKEND_PORT/api/threats | grep -o '"id"' | wc -l | tr -d ' ')
log_success "Current threats in system: $THREAT_COUNT"
echo ""

# ─────────────────────────────────────────────────
# Step 5: Run Load Test
# ─────────────────────────────────────────────────
log_section "Step 5: Load Test"
echo ""

echo "This will run a 2-minute Locust load test with 20 users."
echo "The test will generate requests across all threat types and show"
echo "how the K8s deployment handles load with multiple pods."
echo ""
read -p "Press Enter to start the load test (or Ctrl+C to skip)..."
echo ""

# Check if Locust is installed
LOCUST_CMD=""
if [ -f "$SCRIPT_DIR/../../backend/venv/bin/locust" ]; then
    LOCUST_CMD="$SCRIPT_DIR/../../backend/venv/bin/locust"
    log_info "Using Locust from venv"
elif command -v locust &> /dev/null; then
    LOCUST_CMD="locust"
    log_info "Using system Locust"
else
    log_error "Locust not installed. Install with: pip install locust"
    log_warning "Skipping load test"
    LOCUST_CMD=""
fi

if [ -n "$LOCUST_CMD" ]; then
    LOCUSTFILE="$SCRIPT_DIR/../../loadtests/locustfile.py"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    REPORT_DIR="$SCRIPT_DIR"

    log_info "Running Locust load test (2 minutes, 20 users, spawn rate 5)..."
    echo ""

    cd "$SCRIPT_DIR/../../loadtests"

    "$LOCUST_CMD" -f locustfile.py \
        --host=http://localhost:$BACKEND_PORT \
        --headless \
        --users 20 \
        --spawn-rate 5 \
        --run-time 2m \
        --html="${REPORT_DIR}/k8s-demo-report-${TIMESTAMP}.html" \
        --csv="${REPORT_DIR}/k8s-demo-${TIMESTAMP}" \
        2>&1 | while IFS= read -r line; do
            echo "  [locust] $line"
        done

    echo ""
    log_success "Load test completed!"
    echo ""

    # Show report location
    if [ -f "${REPORT_DIR}/k8s-demo-report-${TIMESTAMP}.html" ]; then
        log_success "HTML Report: ${REPORT_DIR}/k8s-demo-report-${TIMESTAMP}.html"
        open "${REPORT_DIR}/k8s-demo-report-${TIMESTAMP}.html" 2>/dev/null || true
    fi

    if [ -f "${REPORT_DIR}/k8s-demo-${TIMESTAMP}_stats.csv" ]; then
        log_info "CSV Stats: ${REPORT_DIR}/k8s-demo-${TIMESTAMP}_stats.csv"
    fi
    echo ""
fi

# ─────────────────────────────────────────────────
# Step 6: Show Post-Load State
# ─────────────────────────────────────────────────
log_section "Step 6: Post-Load System State"
echo ""

log_info "Fetching updated threat count..."
THREAT_COUNT_AFTER=$(curl -s http://localhost:$BACKEND_PORT/api/threats | grep -o '"id"' | wc -l | tr -d ' ')
log_success "Threats after load test: $THREAT_COUNT_AFTER"
echo ""

log_info "Pod status:"
kubectl get pods -n "$NAMESPACE" -l app=soc-backend
echo ""

log_info "HPA status (check if it scaled up):"
kubectl get hpa -n "$NAMESPACE" 2>/dev/null || log_warning "HPA not found"
echo ""

# ─────────────────────────────────────────────────
# Demo Complete
# ─────────────────────────────────────────────────
log_section "Demo Complete!"
echo ""
log_success "Your K8s demo is complete!"
echo ""
echo "📋 What you demonstrated:"
echo "  ✅ Kubernetes deployment with Helm"
echo "  ✅ Multi-pod backend with HPA configuration"
echo "  ✅ Redis for cross-pod state sharing"
echo "  ✅ Nginx Ingress for routing"
echo "  ✅ Load testing with Locust"
echo "  ✅ Production-ready architecture"
echo ""
echo "🎯 Key talking points:"
echo "  • Horizontal Pod Autoscaler (2-8 replicas based on CPU)"
echo "  • Rolling updates with zero downtime (maxUnavailable=0)"
echo "  • Redis Pub/Sub for multi-pod coordination"
echo "  • Ingress controller for external access"
echo "  • Health checks and readiness probes"
echo ""
echo "📊 Resources to show:"
echo "  • Deployment: kubectl get deployment -n $NAMESPACE"
echo "  • Pods: kubectl get pods -n $NAMESPACE"
echo "  • HPA: kubectl get hpa -n $NAMESPACE"
echo "  • Services: kubectl get svc -n $NAMESPACE"
echo "  • Ingress: kubectl get ingress -n $NAMESPACE"
echo ""
echo "🌐 Access points:"
echo "  • Frontend (port-forward): http://localhost:$FRONTEND_PORT"
echo "  • Backend (port-forward): http://localhost:$BACKEND_PORT"
echo "  • Via Ingress: http://localhost:8080/ (Host: soc-agent.local)"
echo ""
echo "🧹 When done, clean up with:"
echo "  bash soc-agent-system/k8s/demo/teardown_demo.sh"
echo ""

# Cleanup function for port-forwards on exit
cleanup() {
    log_info "Cleaning up port-forwards..."
    kill $BACKEND_PF_PID $FRONTEND_PF_PID 2>/dev/null || true
}

trap cleanup EXIT

log_info "Port-forwards will remain active. Press Ctrl+C to exit and clean up."
echo ""

# Keep script running to maintain port-forwards
wait

