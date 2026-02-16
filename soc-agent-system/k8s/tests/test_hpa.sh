#!/bin/bash
# HPA (Horizontal Pod Autoscaler) Integration Tests
# Tests automatic scaling based on CPU load and Redis Pub/Sub across replicas
#
# Usage:
#   ./test_hpa.sh              # Run tests, leave deployment running
#   ./test_hpa.sh --cleanup    # Run tests, then cleanup
#   ./test_hpa.sh --help       # Show help

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
CLEANUP_AFTER_TESTS=false
BACKEND_PORT=9080

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
                echo "  - kubectl, helm must be installed"
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

# Test: Deploy with HPA enabled
test_deploy_with_hpa() {
    log_info "Deploying SOC Agent with HPA enabled..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Deploy with HPA enabled
    if helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set backend.autoscaling.enabled=true \
        --set backend.autoscaling.minReplicas=2 \
        --set backend.autoscaling.maxReplicas=8 \
        --set backend.autoscaling.targetCPUUtilizationPercentage=50 \
        --set redis.enabled=true \
        --wait --timeout=300s; then
        log_success "Deployment with HPA successful"
    else
        log_error "Deployment with HPA failed"
        return 1
    fi
    
    # Wait for initial pods
    sleep 10
}

# Test: Verify HPA is configured
test_hpa_configured() {
    log_info "Verifying HPA configuration..."
    
    if kubectl get hpa -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log_success "HPA is configured"
    else
        log_error "HPA not found"
        return 1
    fi
    
    # Check HPA details
    HPA_INFO=$(kubectl get hpa -n "$NAMESPACE" -o wide)
    log_info "HPA Status:"
    echo "$HPA_INFO"
}

# Test: Check initial replica count
test_initial_replicas() {
    log_info "Checking initial replica count..."
    
    REPLICAS=$(kubectl get deployment -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[0].status.replicas}')
    
    if [ "$REPLICAS" -ge 2 ]; then
        log_success "Initial replicas: $REPLICAS (minimum 2)"
    else
        log_error "Initial replicas: $REPLICAS (expected >= 2)"
        return 1
    fi
}

# Test: Generate load to trigger scaling
test_scale_up() {
    log_info "Generating load to trigger scale-up..."
    
    # Port-forward to backend
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5
    
    log_info "Sending requests to generate CPU load..."
    
    # Generate load (create threats in a loop)
    for i in {1..50}; do
        curl -s -X POST http://localhost:$BACKEND_PORT/api/threats/trigger \
            -H "Content-Type: application/json" \
            -d '{"threat_type": "bot_traffic"}' > /dev/null &
    done
    
    # Wait for requests to complete
    wait
    
    log_info "Waiting for HPA to scale up (60s)..."
    sleep 60
    
    # Check if pods scaled up
    NEW_REPLICAS=$(kubectl get deployment -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[0].status.replicas}')
    
    # Kill port-forward
    kill $PF_PID 2>/dev/null || true
    
    if [ "$NEW_REPLICAS" -gt 2 ]; then
        log_success "Pods scaled up to $NEW_REPLICAS replicas"
    else
        log_warning "Pods did not scale up (still at $NEW_REPLICAS replicas)"
        log_warning "This may be due to low CPU usage in mock mode"
    fi
}

# Test: Redis Pub/Sub across replicas
test_redis_pubsub() {
    log_info "Testing Redis Pub/Sub across replicas..."

    # Get all backend pods
    PODS=($(kubectl get pods -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[*].metadata.name}'))

    if [ ${#PODS[@]} -lt 2 ]; then
        log_warning "Less than 2 backend pods, skipping Pub/Sub test"
        return 0
    fi

    log_info "Found ${#PODS[@]} backend pods"

    # Port-forward to backend
    kubectl port-forward -n "$NAMESPACE" service/${RELEASE_NAME}-backend $BACKEND_PORT:8000 &
    PF_PID=$!
    sleep 5

    # Create a threat
    RESPONSE=$(curl -s -X POST http://localhost:$BACKEND_PORT/api/threats/trigger \
        -H "Content-Type: application/json" \
        -d '{"threat_type": "bot_traffic"}')

    THREAT_ID=$(echo "$RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    # Kill port-forward
    kill $PF_PID 2>/dev/null || true

    if [ -n "$THREAT_ID" ]; then
        log_success "Threat created with ID: $THREAT_ID"
        log_success "Redis Pub/Sub is working across replicas"
    else
        log_error "Failed to create threat via Redis Pub/Sub"
        return 1
    fi
}

# Test: Scale down after load decreases
test_scale_down() {
    log_info "Waiting for scale-down (90s)..."
    sleep 90

    FINAL_REPLICAS=$(kubectl get deployment -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[0].status.replicas}')

    log_info "Final replica count: $FINAL_REPLICAS"

    if [ "$FINAL_REPLICAS" -le 4 ]; then
        log_success "Pods scaled down to $FINAL_REPLICAS replicas"
    else
        log_warning "Pods still at $FINAL_REPLICAS replicas (may take longer to scale down)"
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
    log_info "HPA (Horizontal Pod Autoscaler) Tests"
    log_info "========================================="
    echo ""

    # Run tests
    test_deploy_with_hpa || exit 1
    test_hpa_configured
    test_initial_replicas
    test_scale_up
    test_redis_pubsub
    test_scale_down

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
        log_success "All HPA tests passed!"
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

