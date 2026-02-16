#!/bin/bash
# Master Test Runner for All K8s Integration Tests
# Runs all test suites in sequence with comprehensive reporting
#
# Usage:
#   ./run_all_tests.sh              # Run all tests, leave deployments running
#   ./run_all_tests.sh --cleanup    # Setup once, run all tests, cleanup at end (for CI/CD)
#   ./run_all_tests.sh --help       # Show help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
CLEANUP_AFTER_TESTS=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="${NAMESPACE:-soc-agent-test}"
RELEASE_NAME="${RELEASE_NAME:-soc-agent-test}"
CHART_PATH="$SCRIPT_DIR/../charts/soc-agent"

# Test results
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=()

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
                echo "  --cleanup    Setup once, run all tests, cleanup at end (recommended for CI/CD)"
                echo "  --help       Show this help message"
                echo ""
                echo "Test Suites:"
                echo "  1. Integration Tests (basic deployment)"
                echo "  2. Connectivity Tests (E2E scenarios)"
                echo "  3. Observability Stack Tests"
                echo "  4. HPA Tests (autoscaling) - SKIPPED (requires metrics-server)"
                echo "  5. Ingress Tests (routing)"
                echo "  6. Resilience Tests (failures & recovery)"
                echo "  7. Performance Tests (load testing)"
                echo ""
                echo "Note: HPA tests are skipped as functionality is covered by Performance Tests"
                echo ""
                echo "CI/CD Workflow:"
                echo "  ./run_all_tests.sh --cleanup"
                echo "  This will:"
                echo "    1. Deploy SOC Agent once"
                echo "    2. Run all test suites against the same deployment"
                echo "    3. Cleanup everything at the end"
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
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

# Setup deployment for all tests
setup_deployment() {
    log_section "Setting Up Test Environment"
    echo ""

    log_info "Deploying SOC Agent for testing..."

    # Clean up any existing deployment
    if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
        log_info "Cleaning up existing deployment..."
        helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true
    fi

    if kubectl get namespace "$NAMESPACE" &>/dev/null; then
        kubectl delete namespace "$NAMESPACE" --timeout=60s || true
    fi

    # Create namespace
    kubectl create namespace "$NAMESPACE"

    # Deploy with Helm
    helm install "$RELEASE_NAME" "$CHART_PATH" \
        --namespace "$NAMESPACE" \
        --set backend.hpa.enabled=false \
        --set backend.replicaCount=2 \
        --set redis.enabled=true \
        --set ingress.enabled=true \
        --set ingress.host=soc-agent.local \
        --wait --timeout=300s

    log_success "Deployment ready for testing"
    echo ""
}

# Cleanup deployment after all tests
cleanup_deployment() {
    log_section "Cleaning Up Test Environment"
    echo ""

    log_info "Uninstalling Helm release..."
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true

    log_info "Deleting namespace..."
    kubectl delete namespace "$NAMESPACE" --timeout=60s || true

    log_success "Cleanup complete"
    echo ""
}

# Run a test suite
run_test_suite() {
    local suite_name="$1"
    local script_name="$2"

    ((TOTAL_SUITES++)) || true

    echo ""
    log_section "$suite_name"
    echo ""

    if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
        log_error "Test script not found: $script_name"
        FAILED_SUITES+=("$suite_name (script not found)")
        return 1
    fi

    # Run test WITHOUT cleanup flag (deployment already exists)
    if cd "$SCRIPT_DIR" && ./"$script_name"; then
        log_success "$suite_name PASSED"
        ((PASSED_SUITES++)) || true
        return 0
    else
        log_error "$suite_name FAILED"
        FAILED_SUITES+=("$suite_name")
        return 1
    fi
}

# Main execution
main() {
    log_section "K8s Integration Test Suite - Master Runner"
    echo ""
    log_info "Starting comprehensive test suite..."
    log_info "Cleanup mode: $([ "$CLEANUP_AFTER_TESTS" = true ] && echo "ENABLED (CI/CD mode)" || echo "DISABLED")"
    echo ""

    # Setup deployment once if cleanup mode is enabled
    if [ "$CLEANUP_AFTER_TESTS" = true ]; then
        setup_deployment
    fi

    # Run all test suites (without individual cleanup)
    run_test_suite "1. Integration Tests" "integration_test.sh" || true
    run_test_suite "2. Connectivity Tests" "test_connectivity.sh" || true
    run_test_suite "3. Observability Stack Tests" "test_observability.sh" || true
    run_test_suite "4. HPA Tests" "test_hpa.sh" || true
    run_test_suite "5. Ingress Tests" "test_ingress.sh" || true
    run_test_suite "6. Resilience Tests" "test_resilience.sh" || true
    run_test_suite "7. Performance Tests" "test_performance.sh" || true

    # Cleanup deployment once if cleanup mode is enabled
    if [ "$CLEANUP_AFTER_TESTS" = true ]; then
        cleanup_deployment
    fi

    # Final summary
    echo ""
    log_section "Final Test Summary"
    echo ""
    log_info "Total test suites: $TOTAL_SUITES"
    log_success "Passed: $PASSED_SUITES"

    if [ ${#FAILED_SUITES[@]} -gt 0 ]; then
        log_error "Failed: ${#FAILED_SUITES[@]}"
        echo ""
        log_error "Failed test suites:"
        for suite in "${FAILED_SUITES[@]}"; do
            echo "  - $suite"
        done
        echo ""
        log_error "Some tests failed. Please review the output above."
        exit 1
    else
        echo ""
        log_success "🎉 All test suites passed! 🎉"
        echo ""
        exit 0
    fi
}

# Parse arguments
parse_args "$@"

# Run main
main

