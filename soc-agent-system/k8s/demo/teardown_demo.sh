#!/bin/bash
# =============================================================================
# SOC Agent System — K8s Demo Teardown Script
# =============================================================================
# Run this AFTER your demo to clean up all resources.
#
# Usage: bash soc-agent-system/k8s/demo/teardown_demo.sh
#        bash soc-agent-system/k8s/demo/teardown_demo.sh --delete-cluster
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
CLUSTER_NAME="soc-agent-cluster"
NAMESPACE="soc-agent-demo"
RELEASE_NAME="soc-agent"
DELETE_CLUSTER=false

# Parse arguments
if [ "$1" = "--delete-cluster" ]; then
    DELETE_CLUSTER=true
fi

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

echo ""
log_section "SOC Agent System — K8s Demo Teardown"
echo ""

# ─────────────────────────────────────────────────
# Step 1: Kill Port Forwards
# ─────────────────────────────────────────────────
log_section "Step 1: Cleaning Up Port Forwards"
echo ""

log_info "Killing any port-forward processes..."
pkill -f "kubectl port-forward.*$NAMESPACE" 2>/dev/null || true
log_success "Port-forwards cleaned up"
echo ""

# ─────────────────────────────────────────────────
# Step 2: Uninstall Helm Release
# ─────────────────────────────────────────────────
log_section "Step 2: Uninstalling Helm Release"
echo ""

if helm list -n "$NAMESPACE" | grep -q "$RELEASE_NAME"; then
    log_info "Uninstalling Helm release '$RELEASE_NAME'..."
    helm uninstall "$RELEASE_NAME" -n "$NAMESPACE"
    log_success "Helm release uninstalled"
else
    log_warning "Helm release '$RELEASE_NAME' not found"
fi
echo ""

# ─────────────────────────────────────────────────
# Step 3: Delete Namespace
# ─────────────────────────────────────────────────
log_section "Step 3: Deleting Namespace"
echo ""

if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_info "Deleting namespace '$NAMESPACE'..."
    kubectl delete namespace "$NAMESPACE" --timeout=60s
    log_success "Namespace deleted"
else
    log_warning "Namespace '$NAMESPACE' not found"
fi
echo ""

# ─────────────────────────────────────────────────
# Step 4: Delete Kind Cluster (Optional)
# ─────────────────────────────────────────────────
if [ "$DELETE_CLUSTER" = true ]; then
    log_section "Step 4: Deleting Kind Cluster"
    echo ""
    
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        log_info "Deleting Kind cluster '$CLUSTER_NAME'..."
        kind delete cluster --name "$CLUSTER_NAME"
        log_success "Kind cluster deleted"
    else
        log_warning "Kind cluster '$CLUSTER_NAME' not found"
    fi
    echo ""
else
    log_section "Step 4: Keeping Kind Cluster"
    echo ""
    log_info "Kind cluster '$CLUSTER_NAME' is still running"
    log_info "To delete it later, run:"
    echo "  kind delete cluster --name $CLUSTER_NAME"
    echo ""
    log_info "Or run this script with --delete-cluster flag:"
    echo "  bash soc-agent-system/k8s/demo/teardown_demo.sh --delete-cluster"
    echo ""
fi

# ─────────────────────────────────────────────────
# Teardown Complete
# ─────────────────────────────────────────────────
log_section "Teardown Complete!"
echo ""

if [ "$DELETE_CLUSTER" = true ]; then
    log_success "All resources have been cleaned up!"
    echo ""
    echo "📋 What was deleted:"
    echo "  ✅ Helm release: $RELEASE_NAME"
    echo "  ✅ Namespace: $NAMESPACE"
    echo "  ✅ Kind cluster: $CLUSTER_NAME"
    echo ""
    echo "🔄 To set up again, run:"
    echo "  bash soc-agent-system/k8s/demo/setup_demo.sh"
else
    log_success "Demo resources cleaned up!"
    echo ""
    echo "📋 What was deleted:"
    echo "  ✅ Helm release: $RELEASE_NAME"
    echo "  ✅ Namespace: $NAMESPACE"
    echo ""
    echo "📋 What remains:"
    echo "  ⚠️  Kind cluster: $CLUSTER_NAME (still running)"
    echo "  ⚠️  Nginx Ingress Controller (still installed)"
    echo ""
    echo "💡 This allows you to quickly re-run the demo without rebuilding images:"
    echo "  bash soc-agent-system/k8s/demo/setup_demo.sh"
    echo ""
    echo "🗑️  To delete everything including the cluster:"
    echo "  bash soc-agent-system/k8s/demo/teardown_demo.sh --delete-cluster"
fi

echo ""

