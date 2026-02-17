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
BACKEND_PORT=9080
FRONTEND_PORT=9081

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((TESTS_PASSED++)) || true; }
log_error() { echo -e "${RED}[✗]${NC} $1"; ((TESTS_FAILED++)) || true; }

# Start port-forwards
start_port_forwards() {
    log_info "Starting port-forwards..."

    kubectl port-forward -n "$NAMESPACE" "service/${RELEASE_NAME}-backend" ${BACKEND_PORT}:8000 > /tmp/pf-backend.log 2>&1 &
    BACKEND_PF_PID=$!

    kubectl port-forward -n "$NAMESPACE" "service/${RELEASE_NAME}-frontend" ${FRONTEND_PORT}:80 > /tmp/pf-frontend.log 2>&1 &
    FRONTEND_PF_PID=$!

    # Wait for port-forwards to be ready
    log_info "Waiting for port-forwards to be ready..."
    sleep 3

    # Check if port-forwards are actually running
    set +e  # Temporarily disable exit on error
    ps -p $BACKEND_PF_PID > /dev/null 2>&1
    BACKEND_RUNNING=$?
    ps -p $FRONTEND_PF_PID > /dev/null 2>&1
    FRONTEND_RUNNING=$?
    set -e  # Re-enable exit on error

    if [ $BACKEND_RUNNING -ne 0 ]; then
        log_error "Backend port-forward failed to start"
        cat /tmp/pf-backend.log
        return 1
    fi

    if [ $FRONTEND_RUNNING -ne 0 ]; then
        log_error "Frontend port-forward failed to start"
        cat /tmp/pf-frontend.log
        return 1
    fi

    # Wait a bit more for the ports to be ready
    sleep 2
    log_success "Port-forwards started (backend: ${BACKEND_PORT}, frontend: ${FRONTEND_PORT})"
}

# Test backend endpoints
test_backend_endpoints() {
    log_info "Testing backend API endpoints..."

    # Health check
    HEALTH_RESPONSE=$(curl -s http://localhost:${BACKEND_PORT}/health 2>&1)
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        log_success "Backend /health endpoint working"
    else
        log_error "Backend /health endpoint failed: $HEALTH_RESPONSE"
        return 1
    fi

    # Ready check
    READY_RESPONSE=$(curl -s http://localhost:${BACKEND_PORT}/ready 2>&1)
    if [ $? -eq 0 ]; then
        log_success "Backend /ready endpoint working"
    else
        log_error "Backend /ready endpoint failed: $READY_RESPONSE"
    fi

    # Metrics endpoint
    METRICS_RESPONSE=$(curl -s http://localhost:${BACKEND_PORT}/metrics 2>&1)
    if echo "$METRICS_RESPONSE" | grep -q "process_cpu"; then
        log_success "Backend /metrics endpoint working"
    else
        log_error "Backend /metrics endpoint failed"
    fi

    # List threats
    THREATS_RESPONSE=$(curl -s http://localhost:${BACKEND_PORT}/api/threats 2>&1)
    if [ $? -eq 0 ]; then
        log_success "Backend /api/threats endpoint working"
    else
        log_error "Backend /api/threats endpoint failed: $THREATS_RESPONSE"
    fi
}

test_frontend_connectivity() {
    log_info "Testing frontend connectivity..."

    FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:${FRONTEND_PORT}/ 2>&1)
    if [ "$FRONTEND_RESPONSE" = "200" ]; then
        log_success "Frontend is accessible"
    else
        log_error "Frontend is not accessible (HTTP $FRONTEND_RESPONSE)"
    fi
}

test_threat_creation() {
    log_info "Testing threat creation (E2E)..."

    # Trigger a threat (using valid threat type)
    RESPONSE=$(curl -s -X POST http://localhost:${BACKEND_PORT}/api/threats/trigger \
        -H "Content-Type: application/json" \
        -d '{"threat_type": "bot_traffic"}' 2>&1)

    if echo "$RESPONSE" | grep -q '"id"'; then
        log_success "Threat creation successful"

        # Extract threat ID (field is "id", not "threat_id")
        THREAT_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
        log_info "Created threat ID: $THREAT_ID"

        # Verify threat appears in list
        sleep 2
        THREATS_LIST=$(curl -s http://localhost:${BACKEND_PORT}/api/threats 2>&1)
        if echo "$THREATS_LIST" | grep -q "$THREAT_ID"; then
            log_success "Threat appears in threat list"
        else
            log_error "Threat not found in threat list"
        fi
    else
        log_error "Threat creation failed: $RESPONSE"
    fi
}

test_redis_connectivity() {
    log_info "Testing Redis connectivity..."

    # Check if Redis pod is running (using correct label)
    if kubectl get pod -n "$NAMESPACE" -l "app=redis" 2>/dev/null | grep -q "Running"; then
        log_success "Redis pod is running"
    else
        log_error "Redis pod is not running"
        return 1
    fi

    # Test Redis connection from backend pod (using correct label)
    BACKEND_POD=$(kubectl get pod -n "$NAMESPACE" -l "app=soc-backend" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$BACKEND_POD" ]; then
        # Check if backend can reach Redis (using redis-cli if available, or check env var)
        REDIS_URL=$(kubectl exec -n "$NAMESPACE" "$BACKEND_POD" -- env | grep REDIS_URL || echo "")
        if [ -n "$REDIS_URL" ]; then
            log_success "Backend has REDIS_URL configured"
        else
            log_error "Backend does not have REDIS_URL configured"
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

    start_port_forwards || { log_error "Port forwards failed"; return 1; }
    test_backend_endpoints || { log_error "Backend endpoints test failed"; }
    test_frontend_connectivity || { log_error "Frontend connectivity test failed"; }
    test_threat_creation || { log_error "Threat creation test failed"; }
    test_redis_connectivity || { log_error "Redis connectivity test failed"; }

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

