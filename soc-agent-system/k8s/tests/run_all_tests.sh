#!/bin/bash
# Master Test Runner for All K8s Integration Tests
# Runs all test suites in sequence with comprehensive reporting
#
# Usage:
#   ./run_all_tests.sh              # Run all tests, leave deployments running
#   ./run_all_tests.sh --cleanup    # Run all tests, cleanup after each
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
                echo "  --cleanup    Cleanup after each test suite"
                echo "  --help       Show this help message"
                echo ""
                echo "Test Suites:"
                echo "  1. Integration Tests (basic deployment)"
                echo "  2. Connectivity Tests (E2E scenarios)"
                echo "  3. Observability Stack Tests"
                echo "  4. HPA Tests (autoscaling)"
                echo "  5. Ingress Tests (routing)"
                echo "  6. Resilience Tests (failures & recovery)"
                echo "  7. Performance Tests (load testing)"
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

# Run a test suite
run_test_suite() {
    local suite_name="$1"
    local script_name="$2"
    local cleanup_flag=""
    
    if [ "$CLEANUP_AFTER_TESTS" = true ]; then
        cleanup_flag="--cleanup"
    fi
    
    ((TOTAL_SUITES++)) || true
    
    echo ""
    log_section "$suite_name"
    echo ""
    
    if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
        log_error "Test script not found: $script_name"
        FAILED_SUITES+=("$suite_name (script not found)")
        return 1
    fi
    
    if cd "$SCRIPT_DIR" && ./"$script_name" $cleanup_flag; then
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
    log_info "Cleanup mode: $([ "$CLEANUP_AFTER_TESTS" = true ] && echo "ENABLED" || echo "DISABLED")"
    echo ""
    
    # Run all test suites
    run_test_suite "1. Integration Tests" "integration_test.sh" || true
    run_test_suite "2. Connectivity Tests" "test_connectivity.sh" || true
    run_test_suite "3. Observability Stack Tests" "test_observability.sh" || true
    run_test_suite "4. HPA Tests" "test_hpa.sh" || true
    run_test_suite "5. Ingress Tests" "test_ingress.sh" || true
    run_test_suite "6. Resilience Tests" "test_resilience.sh" || true
    run_test_suite "7. Performance Tests" "test_performance.sh" || true
    
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

