#!/bin/bash
# Resilience Integration Tests
# Tests pod failures, fallback mechanisms, and rolling updates
#
# Usage:
#   ./test_resilience.sh              # Run tests, leave deployment running
#   ./test_resilience.sh --cleanup    # Run tests, then cleanup
#   ./test_resilience.sh --help       # Show help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
NAMESPACE="${NAMESPACE:-soc-agent-test}"
RELEASE_NAME="${RELEASE_NAME:-soc-agent-test}"
CHART_PATH="../charts/soc-agent"
BACKEND_PORT=9080
CLEANUP_AFTER_TESTS=false

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                CLEANUP_AFTER_TESTS=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --cleanup    Tear down deployment after tests"
                echo "  --help       Show this help message"
                echo ""
                echo "Prerequisites:"
                echo "  - Kind cluster must be running"
                echo "  - Docker images must be built and loaded"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; ((TESTS_PASSED++)) || true; }
log_error() { echo -e "${RED}[✗]${NC} $1"; ((TESTS_FAILED++)) || true; FAILED_TESTS+=("$1"); }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Test: Deploy SOC Agent
test_deploy() {
    log_info "Deploying SOC Agent..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Deploy
    if helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set redis.enabled=true \
        --set backend.replicas=2 \
        --wait --timeout=300s; then
        log_success "Deployment successful"
    else
        log_error "Deployment failed"
        return 1
    fi
    
    sleep 10
}

# Test: Kill Redis pod and verify fallback
test_redis_failure_fallback() {
    log_info "Testing Redis pod failure and fallback..."
    
    # Get Redis pod
    REDIS_POD=$(kubectl get pod -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$REDIS_POD" ]; then
        log_error "Redis pod not found"
        return 1
    fi
    
    log_info "Deleting Redis pod: $REDIS_POD"
    kubectl delete pod -n "$NAMESPACE" "$REDIS_POD"
    
    # Wait a bit for backend to detect Redis failure
    sleep 5
    
    # Port-forward to backend
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5
    
    # Try to create a threat (should work with in-memory fallback)
    RESPONSE=$(curl -s -X POST http://localhost:$BACKEND_PORT/api/threats/trigger \
        -H "Content-Type: application/json" \
        -d '{"threat_type": "bot_traffic"}')
    
    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
    
    if echo "$RESPONSE" | grep -q '"id"'; then
        log_success "Backend fell back to in-memory store after Redis failure"
    else
        log_error "Backend did not handle Redis failure gracefully"
        return 1
    fi
    
    # Wait for Redis to restart
    log_info "Waiting for Redis pod to restart (30s)..."
    sleep 30
    
    # Verify Redis pod is running again
    if kubectl get pod -n "$NAMESPACE" -l app=redis | grep -q "Running"; then
        log_success "Redis pod restarted successfully"
    else
        log_warning "Redis pod not running yet"
    fi
}

# Test: Kill backend pod and verify recovery
test_backend_pod_failure() {
    log_info "Testing backend pod failure and recovery..."
    
    # Get one backend pod
    BACKEND_POD=$(kubectl get pod -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$BACKEND_POD" ]; then
        log_error "Backend pod not found"
        return 1
    fi
    
    log_info "Deleting backend pod: $BACKEND_POD"
    kubectl delete pod -n "$NAMESPACE" "$BACKEND_POD"
    
    # Wait for new pod to start
    log_info "Waiting for new backend pod to start (30s)..."
    sleep 30
    
    # Verify backend pods are running
    RUNNING_PODS=$(kubectl get pods -n "$NAMESPACE" -l app=soc-backend --field-selector=status.phase=Running -o name | wc -l)
    
    if [ "$RUNNING_PODS" -ge 2 ]; then
        log_success "Backend pod recovered ($RUNNING_PODS pods running)"
    else
        log_error "Backend pod did not recover properly"
        return 1
    fi
}

# Test: Rolling update with zero downtime
test_rolling_update() {
    log_info "Testing rolling update with zero downtime..."

    # Start port-forward in background
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5

    # Start continuous health checks in background
    HEALTH_CHECK_FAILED=0
    (
        for i in {1..30}; do
            if ! curl -s http://localhost:$BACKEND_PORT/api/health | grep -q "healthy"; then
                echo "Health check failed at iteration $i"
                exit 1
            fi
            sleep 1
        done
    ) &
    HEALTH_PID=$!

    # Trigger rolling update by changing an annotation
    log_info "Triggering rolling update..."
    kubectl patch deployment -n "$NAMESPACE" "${RELEASE_NAME}-backend" \
        -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"test-update\":\"$(date +%s)\"}}}}}"

    # Wait for health checks to complete
    if wait $HEALTH_PID; then
        log_success "Rolling update completed with zero downtime"
    else
        log_error "Service experienced downtime during rolling update"
        HEALTH_CHECK_FAILED=1
    fi

    # Kill port-forward
    kill $PF_PID 2>/dev/null || true

    # Wait for rollout to complete
    kubectl rollout status deployment -n "$NAMESPACE" -l app=soc-backend --timeout=60s

    if [ $HEALTH_CHECK_FAILED -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Cleanup function
cleanup_deployment() {
    log_info "========================================="
    log_info "Cleaning up deployment..."
    log_info "========================================="

    # Kill any port-forwards
    pkill -f "kubectl port-forward" 2>/dev/null || true

    # Uninstall Helm release
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true
        log_success "Helm release uninstalled"
    fi

    # Delete namespace
    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        kubectl delete namespace "$NAMESPACE" --timeout=60s || true
        log_success "Namespace deleted"
    fi
}

# Main test execution
main() {
    log_info "========================================="
    log_info "Resilience Tests"
    log_info "========================================="
    echo ""

    # Run tests
    test_deploy || exit 1
    test_redis_failure_fallback
    test_backend_pod_failure
    test_rolling_update

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

        if [ "$CLEANUP_AFTER_TESTS" = true ]; then
            echo ""
            cleanup_deployment
        fi
        exit 1
    else
        log_success "All resilience tests passed!"
    fi
}

# Cleanup port-forwards on exit
trap 'pkill -f "kubectl port-forward" 2>/dev/null || true' EXIT

# Parse arguments
parse_args "$@"

# Run main tests
main

# Cleanup if requested
if [ "$CLEANUP_AFTER_TESTS" = true ]; then
    echo ""
    cleanup_deployment
fi

