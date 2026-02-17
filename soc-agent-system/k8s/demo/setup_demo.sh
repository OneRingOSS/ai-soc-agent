#!/bin/bash
# =============================================================================
# SOC Agent System — K8s Demo Setup Script
# =============================================================================
# Run this BEFORE your interview/demo to set up the entire infrastructure.
# This script takes 3-5 minutes to complete.
#
# Usage: bash soc-agent-system/k8s/demo/setup_demo.sh
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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_PATH="$SCRIPT_DIR/../charts/soc-agent"

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

echo ""
log_section "SOC Agent System — K8s Demo Setup"
echo ""
log_info "This script will set up the complete K8s infrastructure for your demo."
log_info "Estimated time: 3-5 minutes"
echo ""

# ─────────────────────────────────────────────────
# Step 1: Check Prerequisites
# ─────────────────────────────────────────────────
log_section "Step 1: Checking Prerequisites"
echo ""

MISSING_DEPS=false

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    MISSING_DEPS=true
else
    log_success "Docker installed"
fi

if ! command -v kind &> /dev/null; then
    log_error "Kind is not installed"
    MISSING_DEPS=true
else
    log_success "Kind installed"
fi

if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is not installed"
    MISSING_DEPS=true
else
    log_success "kubectl installed"
fi

if ! command -v helm &> /dev/null; then
    log_error "Helm is not installed"
    MISSING_DEPS=true
else
    log_success "Helm installed"
fi

if [ "$MISSING_DEPS" = true ]; then
    echo ""
    log_error "Missing required dependencies. Please install them first."
    exit 1
fi

echo ""

# ─────────────────────────────────────────────────
# Step 2: Create Kind Cluster (if not exists)
# ─────────────────────────────────────────────────
log_section "Step 2: Setting Up Kind Cluster"
echo ""

if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    log_warning "Kind cluster '$CLUSTER_NAME' already exists"
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deleting existing cluster..."
        kind delete cluster --name "$CLUSTER_NAME"
        log_success "Cluster deleted"
        echo ""
        log_info "Creating new Kind cluster..."
        kind create cluster --name "$CLUSTER_NAME" --config "$SCRIPT_DIR/../kind-config.yaml"
        log_success "Kind cluster created"
    else
        log_info "Using existing cluster"
    fi
else
    log_info "Creating Kind cluster..."
    kind create cluster --name "$CLUSTER_NAME" --config "$SCRIPT_DIR/../kind-config.yaml"
    log_success "Kind cluster created"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 3: Build and Load Docker Images
# ─────────────────────────────────────────────────
log_section "Step 3: Building Docker Images"
echo ""

log_info "Building backend image..."
cd "$SCRIPT_DIR/../../backend"
docker build -t soc-backend:latest .
log_success "Backend image built"

log_info "Building frontend image..."
cd "$SCRIPT_DIR/../../frontend"
docker build -t soc-frontend:latest .
log_success "Frontend image built"

echo ""
log_info "Loading images into Kind cluster..."
kind load docker-image soc-backend:latest --name "$CLUSTER_NAME"
kind load docker-image soc-frontend:latest --name "$CLUSTER_NAME"
log_success "Images loaded into Kind cluster"

echo ""

# ─────────────────────────────────────────────────
# Step 4: Install Nginx Ingress Controller
# ─────────────────────────────────────────────────
log_section "Step 4: Installing Nginx Ingress Controller"
echo ""

log_info "Installing nginx ingress controller for Kind..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

log_info "Waiting for ingress controller to be ready (60s timeout)..."
kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=60s

log_success "Nginx ingress controller ready"
echo ""

# ─────────────────────────────────────────────────
# Step 5: Deploy SOC Agent System
# ─────────────────────────────────────────────────
log_section "Step 5: Deploying SOC Agent System"
echo ""

# Create namespace
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
log_success "Namespace '$NAMESPACE' created"

# Deploy with Helm
log_info "Deploying SOC Agent with Helm..."
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set backend.hpa.enabled=true \
    --set backend.hpa.minReplicas=2 \
    --set backend.hpa.maxReplicas=8 \
    --set redis.enabled=true \
    --set ingress.enabled=true \
    --set ingress.host=soc-agent.local \
    --set observability.enabled=true \
    --wait --timeout=300s

log_success "SOC Agent deployed"
echo ""

# ─────────────────────────────────────────────────
# Step 6: Verify Deployment
# ─────────────────────────────────────────────────
log_section "Step 6: Verifying Deployment"
echo ""

log_info "Waiting for all pods to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=soc-backend \
    -n "$NAMESPACE" \
    --timeout=120s

kubectl wait --for=condition=ready pod \
    -l app=soc-frontend \
    -n "$NAMESPACE" \
    --timeout=60s

kubectl wait --for=condition=ready pod \
    -l app=redis \
    -n "$NAMESPACE" \
    --timeout=60s

log_success "All pods are ready"
echo ""

# Show deployment status
log_info "Deployment Status:"
echo ""
kubectl get pods -n "$NAMESPACE"
echo ""
kubectl get svc -n "$NAMESPACE"
echo ""
kubectl get ingress -n "$NAMESPACE"
echo ""

# ─────────────────────────────────────────────────
# Step 7: Test Connectivity
# ─────────────────────────────────────────────────
log_section "Step 7: Testing Connectivity"
echo ""

log_info "Testing backend health endpoint via Ingress..."
sleep 5  # Give ingress a moment to update

if curl -s -H "Host: soc-agent.local" "http://localhost:8080/health" | grep -q "healthy"; then
    log_success "Backend health check passed"
else
    log_warning "Backend health check failed (may need a moment to stabilize)"
fi

log_info "Testing frontend via Ingress..."
if curl -s -H "Host: soc-agent.local" "http://localhost:8080/" | grep -q "<!DOCTYPE html>"; then
    log_success "Frontend is accessible"
else
    log_warning "Frontend check failed (may need a moment to stabilize)"
fi

echo ""

# ─────────────────────────────────────────────────
# Step 8: Pre-populate Some Data (Optional)
# ─────────────────────────────────────────────────
log_section "Step 8: Pre-populating Demo Data"
echo ""

log_info "Creating a few sample threats for demo..."
for i in {1..5}; do
    curl -s -X POST -H "Host: soc-agent.local" "http://localhost:8080/api/threats/trigger" \
        -H "Content-Type: application/json" \
        -d '{"threat_type": "bot_traffic"}' > /dev/null
done

log_success "Created 5 sample threats"
echo ""

# ─────────────────────────────────────────────────
# Setup Complete!
# ─────────────────────────────────────────────────
log_section "Setup Complete!"
echo ""
log_success "Your K8s demo environment is ready!"
echo ""
echo "📋 What was set up:"
echo "  ✅ Kind cluster: $CLUSTER_NAME"
echo "  ✅ Namespace: $NAMESPACE"
echo "  ✅ Nginx Ingress Controller"
echo "  ✅ SOC Agent System (backend, frontend, Redis)"
echo "  ✅ HPA configured (2-8 replicas)"
echo "  ✅ Sample threats pre-populated"
echo ""
echo "🚀 Next Steps:"
echo "  1. Review the deployment:"
echo "     kubectl get all -n $NAMESPACE"
echo ""
echo "  2. Access the application:"
echo "     curl -H \"Host: soc-agent.local\" http://localhost:8080/"
echo "     (or add '127.0.0.1 soc-agent.local' to /etc/hosts and visit http://soc-agent.local:8080)"
echo ""
echo "  3. When ready for your demo, run:"
echo "     bash soc-agent-system/k8s/demo/run_demo.sh"
echo ""
echo "  4. After the demo, clean up with:"
echo "     bash soc-agent-system/k8s/demo/teardown_demo.sh"
echo ""
log_info "The environment will remain running until you tear it down."
echo ""

