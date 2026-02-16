#!/bin/bash
# Test connectivity to all SOC Agent services
# Tests frontend, backend API, WebSocket, and Redis connectivity

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NAMESPACE="${NAMESPACE:-soc-agent-test}"
RELEASE_NAME="${RELEASE_NAME:-soc-agent-test}"
BACKEND_PORT=8080
FRONTEND_PORT=8081

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((TESTS_PASSED++)); }
log_error() { echo -e "${RED}[✗]${NC} $1"; ((TESTS_FAILED++)); }

# Start port-forwards
start_port_forwards() {
    log_info "Starting port-forwards..."

    kubectl port-forward -n "$NAMESPACE" "service/${RELEASE_NAME}-backend" ${BACKEND_PORT}:8000 > /dev/null 2>&1 &
    BACKEND_PF_PID=$!

    kubectl port-forward -n "$NAMESPACE" "service/${RELEASE_NAME}-frontend" ${FRONTEND_PORT}:80 > /dev/null 2>&1 &
    FRONTEND_PF_PID=$!

    sleep 5
    log_success "Port-forwards started (backend: ${BACKEND_PORT}, frontend: ${FRONTEND_PORT})"
}

# Test backend endpoints
test_backend_endpoints() {
    log_info "Testing backend API endpoints..."

    # Health check
    if curl -sf http://localhost:${BACKEND_PORT}/health | grep -q "healthy"; then
        log_success "Backend /health endpoint working"
    else
        log_error "Backend /health endpoint failed"
    fi

    # Ready check
    if curl -sf http://localhost:${BACKEND_PORT}/ready > /dev/null; then
        log_success "Backend /ready endpoint working"
    else
        log_error "Backend /ready endpoint failed"
    fi

    # Metrics endpoint
    if curl -sf http://localhost:${BACKEND_PORT}/metrics | grep -q "process_cpu"; then
        log_success "Backend /metrics endpoint working"
    else
        log_error "Backend /metrics endpoint failed"
    fi

    # List threats
    if curl -sf http://localhost:${BACKEND_PORT}/api/threats > /dev/null; then
        log_success "Backend /api/threats endpoint working"
    else
        log_error "Backend /api/threats endpoint failed"
    fi
}

test_frontend_connectivity() {
    log_info "Testing frontend connectivity..."

    if curl -sf http://localhost:${FRONTEND_PORT}/ > /dev/null; then
        log_success "Frontend is accessible"
    else
        log_error "Frontend is not accessible"
    fi
}

test_threat_creation() {
    log_info "Testing threat creation (E2E)..."

    # Trigger a threat
    RESPONSE=$(curl -sf -X POST http://localhost:${BACKEND_PORT}/api/threats/trigger \
        -H "Content-Type: application/json" \
        -d '{"threat_type": "malware", "severity": "high"}')

    if echo "$RESPONSE" | grep -q "threat_id"; then
        log_success "Threat creation successful"

        # Extract threat ID
        THREAT_ID=$(echo "$RESPONSE" | grep -o '"threat_id":"[^"]*"' | cut -d'"' -f4)
        log_info "Created threat ID: $THREAT_ID"

        # Verify threat appears in list
        sleep 2
        if curl -sf http://localhost:${BACKEND_PORT}/api/threats | grep -q "$THREAT_ID"; then
            log_success "Threat appears in threat list"
        else
            log_error "Threat not found in threat list"
        fi
    else
        log_error "Threat creation failed"
    fi
}

test_redis_connectivity() {
    log_info "Testing Redis connectivity..."

    # Check if Redis pod is running
    if kubectl get pod -n "$NAMESPACE" -l "app.kubernetes.io/name=redis" 2>/dev/null | grep -q "Running"; then
        log_success "Redis pod is running"
    else
        log_error "Redis pod is not running"
        return 1
    fi

    # Test Redis connection from backend pod
    BACKEND_POD=$(kubectl get pod -n "$NAMESPACE" -l "app.kubernetes.io/component=backend" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$BACKEND_POD" ]; then
        if kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- sh -c "echo 'PING' | nc ${RELEASE_NAME}-redis 6379 2>/dev/null" | grep -q "PONG"; then
            log_success "Backend can connect to Redis"
        else
            log_error "Backend cannot connect to Redis"
        fi
    else
        log_error "Backend pod not found"
    fi
}

# Cleanup
cleanup() {
    log_info "Cleaning up port-forwards..."
    kill $BACKEND_PF_PID 2>/dev/null || true
    kill $FRONTEND_PF_PID 2>/dev/null || true
}
trap cleanup EXIT

# Main
main() {
    log_info "========================================="
    log_info "SOC Agent Connectivity Tests"
    log_info "========================================="
    echo ""

    start_port_forwards
    test_backend_endpoints
    test_frontend_connectivity
    test_threat_creation
    test_redis_connectivity

    echo ""
    log_info "========================================="
    log_info "Test Summary"
    log_info "========================================="
    log_success "Tests passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        log_error "Tests failed: $TESTS_FAILED"
        exit 1
    else
        log_success "All connectivity tests passed!"
    fi
}

main "$@"

