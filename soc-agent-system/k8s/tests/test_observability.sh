#!/bin/bash
# Observability Stack Integration Tests
# Tests Prometheus, Grafana, Jaeger, and Loki deployment and functionality
#
# Usage:
#   ./test_observability.sh              # Run tests, leave deployment running
#   ./test_observability.sh --cleanup    # Run tests, then cleanup
#   ./test_observability.sh --help       # Show help

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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OBSERVABILITY_DIR="$SCRIPT_DIR/../../observability"
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
                echo "  --cleanup    Tear down observability stack after tests"
                echo "  --help       Show this help message"
                echo ""
                echo "Prerequisites:"
                echo "  - SOC Agent must be deployed (run integration_test.sh first)"
                echo "  - Docker Compose must be installed"
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

# Test: Deploy observability stack
test_deploy_observability() {
    log_info "Deploying observability stack..."
    
    if [ ! -d "$OBSERVABILITY_DIR" ]; then
        log_error "Observability directory not found: $OBSERVABILITY_DIR"
        return 1
    fi
    
    cd "$OBSERVABILITY_DIR"
    
    if docker-compose up -d; then
        log_success "Observability stack deployed"
    else
        log_error "Failed to deploy observability stack"
        return 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready (30s)..."
    sleep 30
}

# Test: Prometheus metrics scraping
test_prometheus_metrics() {
    log_info "Testing Prometheus metrics scraping..."
    
    # Check Prometheus is accessible
    if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus"; then
        log_success "Prometheus is healthy"
    else
        log_error "Prometheus health check failed"
        return 1
    fi
    
    # Check if Prometheus can scrape targets (we'll check after backend is deployed)
    TARGETS=$(curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"up"' | wc -l)
    if [ "$TARGETS" -gt 0 ]; then
        log_success "Prometheus has active targets ($TARGETS up)"
    else
        log_warning "Prometheus has no active targets (backend may not be deployed)"
    fi
}

# Test: Grafana accessibility
test_grafana_dashboard() {
    log_info "Testing Grafana dashboard accessibility..."
    
    # Check Grafana is accessible
    if curl -s http://localhost:3000/api/health | grep -q "ok"; then
        log_success "Grafana is accessible"
    else
        log_error "Grafana health check failed"
        return 1
    fi
    
    # Check if datasources are configured
    DATASOURCES=$(curl -s -u admin:admin http://localhost:3000/api/datasources | grep -o '"name"' | wc -l)
    if [ "$DATASOURCES" -gt 0 ]; then
        log_success "Grafana has $DATASOURCES datasource(s) configured"
    else
        log_warning "Grafana has no datasources configured"
    fi
}

# Test: Jaeger trace collection
test_jaeger_tracing() {
    log_info "Testing Jaeger trace collection..."
    
    # Check Jaeger is accessible
    if curl -s http://localhost:16686/ | grep -q "Jaeger"; then
        log_success "Jaeger UI is accessible"
    else
        log_error "Jaeger UI not accessible"
        return 1
    fi
    
    # Check if Jaeger API is working
    JAEGER_RESPONSE=$(curl -s http://localhost:16686/api/services)
    if echo "$JAEGER_RESPONSE" | grep -qE '(\[|\{)'; then
        log_success "Jaeger API is working"
    else
        log_warning "Jaeger API not responding (may need traces to be generated)"
    fi
}

# Test: Loki log aggregation
test_loki_logs() {
    log_info "Testing Loki log aggregation..."

    # Check Loki is accessible
    if curl -s http://localhost:3100/ready | grep -q "ready"; then
        log_success "Loki is ready"
    else
        log_error "Loki health check failed"
        return 1
    fi

    # Check Loki metrics endpoint
    if curl -s http://localhost:3100/metrics | grep -q "loki"; then
        log_success "Loki metrics endpoint is working"
    else
        log_warning "Loki metrics endpoint not responding"
    fi
}

# Cleanup function
cleanup_observability() {
    log_info "========================================="
    log_info "Cleaning up observability stack..."
    log_info "========================================="

    cd "$OBSERVABILITY_DIR"

    if docker-compose down; then
        log_success "Observability stack stopped and removed"
    else
        log_warning "Failed to cleanup observability stack"
    fi
}

# Main test execution
main() {
    log_info "========================================="
    log_info "Observability Stack Tests"
    log_info "========================================="
    echo ""

    # Run tests
    test_deploy_observability || exit 1
    test_prometheus_metrics
    test_grafana_dashboard
    test_jaeger_tracing
    test_loki_logs

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

        # Cleanup even on failure if requested
        if [ "$CLEANUP_AFTER_TESTS" = true ]; then
            echo ""
            cleanup_observability
        fi
        exit 1
    else
        log_success "All observability tests passed!"
    fi
}

# Parse arguments
parse_args "$@"

# Run main tests
main

# Cleanup if requested
if [ "$CLEANUP_AFTER_TESTS" = true ]; then
    echo ""
    cleanup_observability
fi

