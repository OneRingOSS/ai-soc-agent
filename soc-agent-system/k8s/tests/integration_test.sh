#!/bin/bash
# Integration test suite for SOC Agent Kubernetes deployment
# Tests Helm chart deployment, pod health, service connectivity, and E2E flows

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${NAMESPACE:-soc-agent-test}"
RELEASE_NAME="${RELEASE_NAME:-soc-agent-test}"
TIMEOUT="${TIMEOUT:-300}"  # 5 minutes
CHART_PATH="../charts/soc-agent"

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
    FAILED_TESTS+=("$1")
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Test functions
test_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found"
        return 1
    fi
    log_success "kubectl found"
    
    if ! command -v helm &> /dev/null; then
        log_error "helm not found"
        return 1
    fi
    log_success "helm found"
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        return 1
    fi
    log_success "Connected to Kubernetes cluster"
}

test_deploy_helm_chart() {
    log_info "Deploying Helm chart..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Deploy Helm chart
    if helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set backend.image.tag=latest \
        --set frontend.image.tag=latest \
        --set redis.enabled=true \
        --set backend.autoscaling.enabled=false \
        --wait --timeout="${TIMEOUT}s"; then
        log_success "Helm chart deployed successfully"
    else
        log_error "Failed to deploy Helm chart"
        return 1
    fi
}

test_pods_running() {
    log_info "Checking if all pods are running..."
    
    # Wait for pods to be ready
    if kubectl wait --for=condition=ready pod \
        --selector="app.kubernetes.io/instance=$RELEASE_NAME" \
        --namespace="$NAMESPACE" \
        --timeout="${TIMEOUT}s"; then
        log_success "All pods are running"
    else
        log_error "Some pods failed to start"
        kubectl get pods -n "$NAMESPACE"
        return 1
    fi
    
    # Show pod status
    kubectl get pods -n "$NAMESPACE"
}

test_services_exist() {
    log_info "Checking if services exist..."
    
    local services=("backend" "frontend" "redis")
    for svc in "${services[@]}"; do
        if kubectl get service "${RELEASE_NAME}-${svc}" -n "$NAMESPACE" &> /dev/null; then
            log_success "Service ${svc} exists"
        else
            log_error "Service ${svc} not found"
        fi
    done
}

test_backend_health() {
    log_info "Testing backend health endpoint..."
    
    # Port-forward backend service
    kubectl port-forward -n "$NAMESPACE" "service/${RELEASE_NAME}-backend" 8080:8000 &
    PF_PID=$!
    sleep 3
    
    # Test health endpoint
    if curl -sf http://localhost:8080/health > /dev/null; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        kill $PF_PID 2>/dev/null || true
        return 1
    fi
    
    kill $PF_PID 2>/dev/null || true
}

# Main execution
main() {
    log_info "========================================="
    log_info "SOC Agent K8s Integration Test Suite"
    log_info "========================================="
    echo ""
    
    # Run tests
    test_prerequisites || exit 1
    test_deploy_helm_chart || exit 1
    test_pods_running || exit 1
    test_services_exist
    test_backend_health
    
    # Summary
    echo ""
    log_info "========================================="
    log_info "Test Summary"
    log_info "========================================="
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        echo ""
        log_error "Failed tests:"
        for test in "${FAILED_TESTS[@]}"; do
            echo "  - $test"
        done
        exit 1
    else
        log_success "All tests passed!"
    fi
}

# Cleanup on exit
cleanup() {
    log_info "Cleaning up port-forwards..."
    pkill -f "kubectl port-forward" 2>/dev/null || true
}
trap cleanup EXIT

main "$@"

