#!/bin/bash
# Performance Integration Tests
# Runs Locust load tests against K8s deployment or Docker Compose and verifies state sharing
#
# Usage:
#   ./test_performance.sh                    # Run tests against K8s, leave deployment running
#   ./test_performance.sh --cleanup          # Run tests against K8s, then cleanup
#   ./test_performance.sh --mode docker      # Run tests against Docker Compose
#   ./test_performance.sh --help             # Show help

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
FRONTEND_PORT=9081
LOCUST_DIR="../../loadtests"
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
                echo "  - Locust must be installed (pip install locust)"
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

# Test: Deploy SOC Agent with multiple replicas
test_deploy() {
    log_info "Deploying SOC Agent with multiple replicas..."

    # Clean up any existing deployment first
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" 2>/dev/null || true
    kubectl delete namespace "$NAMESPACE" 2>/dev/null || true
    sleep 5

    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true

    # Deploy with 3 backend replicas (using HPA minReplicas)
    if helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set backend.hpa.minReplicas=3 \
        --set backend.hpa.maxReplicas=10 \
        --set redis.enabled=true \
        --wait --timeout=300s; then
        log_success "Deployment successful (3 backend replicas)"
    else
        log_error "Deployment failed"
        return 1
    fi

    # Wait for all pods to be ready
    log_info "Waiting for all pods to be ready..."
    sleep 15
}

# Test: Verify multiple replicas are running
test_verify_replicas() {
    log_info "Verifying multiple backend replicas..."
    
    REPLICAS=$(kubectl get pods -n "$NAMESPACE" -l app=soc-backend --field-selector=status.phase=Running -o name | wc -l)
    
    if [ "$REPLICAS" -ge 3 ]; then
        log_success "$REPLICAS backend replicas running"
    else
        log_error "Expected 3+ replicas, found $REPLICAS"
        return 1
    fi
}

# Test: Run Locust load test
test_locust_load() {
    log_info "Running Locust load test..."

    # Get script directory for absolute paths
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Find Locust (check venv first, then system)
    LOCUST_CMD=""
    if [ -f "$SCRIPT_DIR/../../backend/venv/bin/locust" ]; then
        LOCUST_CMD="$SCRIPT_DIR/../../backend/venv/bin/locust"
        log_info "Using Locust from venv: $LOCUST_CMD"
    elif command -v locust &> /dev/null; then
        LOCUST_CMD="locust"
        log_info "Using system Locust"
    else
        log_error "Locust not installed. Install with: pip install locust"
        return 1
    fi
    
    # Start port-forwards
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    BACKEND_PF_PID=$!
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-frontend $FRONTEND_PORT:80 &
    FRONTEND_PF_PID=$!
    sleep 5
    
    # Run Locust in headless mode
    log_info "Running Locust test (60 seconds, 10 users, 2 spawn rate)..."

    cd "$LOCUST_DIR"

    if "$LOCUST_CMD" -f locustfile.py \
        --headless \
        --users 10 \
        --spawn-rate 2 \
        --run-time 60s \
        --host http://localhost:$BACKEND_PORT \
        --html /tmp/locust_k8s_report.html \
        --csv /tmp/locust_k8s; then
        log_success "Locust load test completed"
    else
        log_error "Locust load test failed"
        kill $BACKEND_PF_PID $FRONTEND_PF_PID 2>/dev/null || true
        return 1
    fi
    
    # Kill port-forwards
    kill $BACKEND_PF_PID $FRONTEND_PF_PID 2>/dev/null || true
    
    # Analyze results
    if [ -f /tmp/locust_k8s_stats.csv ]; then
        log_info "Load test results:"
        cat /tmp/locust_k8s_stats.csv | head -5
    fi
}

# Test: Verify cross-pod state sharing via Redis
test_cross_pod_state() {
    log_info "Testing cross-pod state sharing via Redis..."
    
    # Port-forward to backend
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5
    
    # Create multiple threats
    log_info "Creating threats across multiple replicas..."
    for i in {1..10}; do
        curl -s -X POST http://localhost:$BACKEND_PORT/api/threats/trigger \
            -H "Content-Type: application/json" \
            -d '{"threat_type": "bot_traffic"}' > /dev/null
    done
    
    sleep 2
    
    # Get threats from API
    THREAT_COUNT=$(curl -s http://localhost:$BACKEND_PORT/api/threats | grep -o '"id"' | wc -l)
    
    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
    
    if [ "$THREAT_COUNT" -ge 10 ]; then
        log_success "Cross-pod state sharing working ($THREAT_COUNT threats found)"
    else
        log_error "Cross-pod state sharing issue (only $THREAT_COUNT threats found)"
        return 1
    fi
}

# Test: Measure response times
test_response_times() {
    log_info "Measuring response times with multiple replicas..."

    # Port-forward to backend
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5

    # Measure response time for health endpoint using curl's time measurement
    TOTAL_TIME=0
    ITERATIONS=10

    for i in $(seq 1 $ITERATIONS); do
        # Use curl's built-in time measurement (in seconds, with decimals)
        TIME_SECONDS=$(curl -s -o /dev/null -w '%{time_total}' http://localhost:$BACKEND_PORT/health)
        # Convert to milliseconds (multiply by 1000)
        TIME_MS=$(echo "$TIME_SECONDS * 1000" | bc)
        TOTAL_TIME=$(echo "$TOTAL_TIME + $TIME_MS" | bc)
    done

    AVG_TIME=$(echo "scale=0; $TOTAL_TIME / $ITERATIONS" | bc)

    # Kill port-forward
    kill $PF_PID 2>/dev/null || true

    log_info "Average response time: ${AVG_TIME}ms"

    if [ "$AVG_TIME" -lt 200 ]; then
        log_success "Response times are good (avg: ${AVG_TIME}ms)"
    else
        log_warning "Response times are slow (avg: ${AVG_TIME}ms)"
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

    # Clean up Locust reports
    rm -f /tmp/locust_k8s* 2>/dev/null || true
}

# Main test execution
main() {
    log_info "========================================="
    log_info "Performance Tests"
    log_info "========================================="
    echo ""

    # Run tests
    test_deploy || exit 1
    test_verify_replicas
    test_locust_load
    test_cross_pod_state
    test_response_times

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
        log_success "All performance tests passed!"

        if [ -f /tmp/locust_k8s_report.html ]; then
            log_info "Locust report saved to: /tmp/locust_k8s_report.html"
        fi
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

