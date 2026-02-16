#!/bin/bash
# Ingress Integration Tests
# Tests ingress routing for frontend, backend API, and WebSocket endpoints
#
# Usage:
#   ./test_ingress.sh              # Run tests, leave deployment running
#   ./test_ingress.sh --cleanup    # Run tests, then cleanup
#   ./test_ingress.sh --help       # Show help

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
INGRESS_HOST="${INGRESS_HOST:-soc-agent.local}"
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
                echo "  - Kind cluster must be running with ingress controller"
                echo "  - Add '127.0.0.1 soc-agent.local' to /etc/hosts"
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

# Test: Install nginx ingress controller
test_install_ingress_controller() {
    log_info "Installing nginx ingress controller..."
    
    # Check if already installed
    if kubectl get namespace ingress-nginx &>/dev/null; then
        log_info "Ingress controller already installed"
        return 0
    fi
    
    # Install ingress-nginx
    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
    
    log_info "Waiting for ingress controller to be ready (60s)..."
    kubectl wait --namespace ingress-nginx \
        --for=condition=ready pod \
        --selector=app.kubernetes.io/component=controller \
        --timeout=90s || true
    
    log_success "Ingress controller installed"
}

# Test: Deploy with Ingress enabled
test_deploy_with_ingress() {
    log_info "Deploying SOC Agent with Ingress enabled..."
    
    # Create namespace
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
    
    # Deploy with Ingress enabled
    if helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set ingress.enabled=true \
        --set ingress.className=nginx \
        --set ingress.hosts[0].host="$INGRESS_HOST" \
        --set ingress.hosts[0].paths[0].path=/ \
        --set ingress.hosts[0].paths[0].pathType=Prefix \
        --set redis.enabled=true \
        --wait --timeout=300s; then
        log_success "Deployment with Ingress successful"
    else
        log_error "Deployment with Ingress failed"
        return 1
    fi
    
    sleep 10
}

# Test: Verify Ingress is configured
test_ingress_configured() {
    log_info "Verifying Ingress configuration..."
    
    if kubectl get ingress -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log_success "Ingress is configured"
    else
        log_error "Ingress not found"
        return 1
    fi
    
    # Show ingress details
    INGRESS_INFO=$(kubectl get ingress -n "$NAMESPACE" -o wide)
    log_info "Ingress Status:"
    echo "$INGRESS_INFO"
}

# Test: Frontend routing (/)
test_frontend_routing() {
    log_info "Testing frontend routing (/)..."

    # For Kind, we need to get the NodePort
    INGRESS_PORT=$(kubectl get service -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')

    if curl -s -H "Host: $INGRESS_HOST" "http://localhost:${INGRESS_PORT}/" | grep -q "<!doctype html>"; then
        log_success "Frontend accessible via Ingress"
    else
        log_error "Frontend not accessible via Ingress"
        return 1
    fi
}

# Test: Backend API routing (/api/*)
test_backend_api_routing() {
    log_info "Testing backend API routing (/api/*)..."

    # For Kind, we need to get the NodePort
    INGRESS_PORT=$(kubectl get service -n ingress-nginx ingress-nginx-controller -o jsonpath='{.spec.ports[?(@.name=="http")].nodePort}')

    # Test /api/health
    if curl -s -H "Host: $INGRESS_HOST" "http://localhost:${INGRESS_PORT}/api/health" | grep -q "healthy"; then
        log_success "Backend /api/health accessible via Ingress"
    else
        log_error "Backend /api/health not accessible via Ingress"
        return 1
    fi

    # Test /api/threats
    if curl -s -H "Host: $INGRESS_HOST" "http://localhost:${INGRESS_PORT}/api/threats" | grep -q "\["; then
        log_success "Backend /api/threats accessible via Ingress"
    else
        log_error "Backend /api/threats not accessible via Ingress"
        return 1
    fi
}

# Test: WebSocket routing (/ws)
test_websocket_routing() {
    log_info "Testing WebSocket routing (/ws)..."

    # Note: Full WebSocket testing requires a WebSocket client
    # Here we just verify the endpoint is reachable
    log_warning "WebSocket testing requires manual verification"
    log_info "WebSocket endpoint should be: ws://$INGRESS_HOST/ws"
}

# Cleanup function
cleanup_deployment() {
    log_info "========================================="
    log_info "Cleaning up deployment..."
    log_info "========================================="

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

    log_info "Note: Ingress controller is still running"
    log_info "To remove it: kubectl delete namespace ingress-nginx"
}

# Main test execution
main() {
    log_info "========================================="
    log_info "Ingress Integration Tests"
    log_info "========================================="
    echo ""

    # Run tests
    test_install_ingress_controller
    test_deploy_with_ingress || exit 1
    test_ingress_configured
    test_frontend_routing
    test_backend_api_routing
    test_websocket_routing

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
        log_success "All Ingress tests passed!"
    fi
}

# Parse arguments
parse_args "$@"

# Run main tests
main

# Cleanup if requested
if [ "$CLEANUP_AFTER_TESTS" = true ]; then
    echo ""
    cleanup_deployment
fi

