#!/bin/bash
# Cleanup script for SOC Agent Kubernetes test environment
# Tears down Helm deployment, namespace, and optionally the Kind cluster
#
# Usage:
#   ./cleanup.sh                    # Cleanup deployment only
#   ./cleanup.sh --delete-cluster   # Cleanup deployment and delete Kind cluster
#   ./cleanup.sh --help             # Show help

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
CLUSTER_NAME="${CLUSTER_NAME:-soc-agent-cluster}"
DELETE_CLUSTER=false

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --delete-cluster)
                DELETE_CLUSTER=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --delete-cluster   Also delete the Kind cluster"
                echo "  --help             Show this help message"
                echo ""
                echo "Environment variables:"
                echo "  NAMESPACE      Kubernetes namespace (default: soc-agent-test)"
                echo "  RELEASE_NAME   Helm release name (default: soc-agent-test)"
                echo "  CLUSTER_NAME   Kind cluster name (default: soc-agent-cluster)"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# Main cleanup function
cleanup() {
    log_info "========================================="
    log_info "SOC Agent Cleanup"
    log_info "========================================="
    echo ""
    
    # Kill any port-forwards
    log_info "Stopping port-forwards..."
    pkill -f "kubectl port-forward" 2>/dev/null || true
    log_success "Port-forwards stopped"
    
    # Uninstall Helm release
    if command -v helm &> /dev/null && helm list -n "$NAMESPACE" 2>/dev/null | grep -q "$RELEASE_NAME"; then
        log_info "Uninstalling Helm release: $RELEASE_NAME"
        helm uninstall "$RELEASE_NAME" -n "$NAMESPACE" || true
        log_success "Helm release uninstalled"
    else
        log_warning "Helm release not found or helm not installed"
    fi
    
    # Delete namespace
    if command -v kubectl &> /dev/null && kubectl get namespace "$NAMESPACE" &>/dev/null; then
        log_info "Deleting namespace: $NAMESPACE"
        kubectl delete namespace "$NAMESPACE" --timeout=60s || true
        log_success "Namespace deleted"
    else
        log_warning "Namespace not found or kubectl not installed"
    fi
    
    # Delete Kind cluster if requested
    if [ "$DELETE_CLUSTER" = true ]; then
        if command -v kind &> /dev/null && kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
            log_info "Deleting Kind cluster: $CLUSTER_NAME"
            kind delete cluster --name "$CLUSTER_NAME" || true
            log_success "Kind cluster deleted"
        else
            log_warning "Kind cluster not found or kind not installed"
        fi
    fi
    
    echo ""
    log_success "Cleanup complete!"
    
    if [ "$DELETE_CLUSTER" != true ]; then
        echo ""
        log_info "Note: Kind cluster is still running. To delete it, run:"
        log_info "  $0 --delete-cluster"
        log_info "  OR"
        log_info "  kind delete cluster --name $CLUSTER_NAME"
    fi
}

# Parse arguments and run cleanup
parse_args "$@"
cleanup

