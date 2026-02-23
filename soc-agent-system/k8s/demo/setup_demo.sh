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
# Step 5: Deploy SOC Agent System (Sequential)
# ─────────────────────────────────────────────────
log_section "Step 5: Deploying SOC Agent System"
echo ""

# Create namespace
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f - || true
log_success "Namespace '$NAMESPACE' created"
echo ""

# ─────────────────────────────────────────────────
# Step 5a: Deploy Redis First
# ─────────────────────────────────────────────────
log_info "[1/3] Deploying Redis..."
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set backend.enabled=false \
    --set frontend.enabled=false \
    --set redis.enabled=true \
    --set ingress.enabled=false \
    --wait --timeout=120s

log_success "Redis deployed"

log_info "Waiting for Redis pod to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=redis \
    -n "$NAMESPACE" \
    --timeout=60s

log_success "Redis pod is ready"

# Test Redis connectivity
log_info "Testing Redis connectivity..."
sleep 3  # Give Redis a moment to fully initialize

REDIS_POD=$(kubectl get pod -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli ping | grep -q "PONG"; then
    log_success "Redis is accepting connections (PING -> PONG)"
else
    log_error "Redis is not responding to PING"
    exit 1
fi

echo ""

# ─────────────────────────────────────────────────
# Step 5b: Deploy Backend
# ─────────────────────────────────────────────────
log_info "[2/3] Deploying Backend (with HPA)..."
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set backend.enabled=true \
    --set backend.hpa.enabled=true \
    --set backend.hpa.minReplicas=2 \
    --set backend.hpa.maxReplicas=8 \
    --set frontend.enabled=false \
    --set redis.enabled=true \
    --set ingress.enabled=false \
    --wait --timeout=120s

log_success "Backend deployed"

log_info "Waiting for backend pods to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=soc-backend \
    -n "$NAMESPACE" \
    --timeout=120s

log_success "Backend pods are ready"

# Test backend Redis connectivity
log_info "Verifying backend connected to Redis..."
sleep 3  # Give backend time to establish connection

REDIS_CHECK=$(kubectl logs -n "$NAMESPACE" -l app=soc-backend --tail=50 | grep -c "Redis connection successful" || echo "0")
if [ "$REDIS_CHECK" -gt 0 ]; then
    log_success "Backend successfully connected to Redis"
else
    log_error "Backend failed to connect to Redis"
    kubectl logs -n "$NAMESPACE" -l app=soc-backend --tail=20 | grep -i redis
    exit 1
fi

echo ""

# ─────────────────────────────────────────────────
# Step 5c: Deploy Frontend and Ingress
# ─────────────────────────────────────────────────
log_info "[3/3] Deploying Frontend and Ingress..."
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set backend.enabled=true \
    --set backend.hpa.enabled=true \
    --set backend.hpa.minReplicas=2 \
    --set backend.hpa.maxReplicas=8 \
    --set frontend.enabled=true \
    --set redis.enabled=true \
    --set ingress.enabled=true \
    --set ingress.host=localhost \
    --set observability.enabled=true \
    --wait --timeout=120s

log_success "Frontend and Ingress deployed"

log_info "Waiting for frontend pod to be ready..."
kubectl wait --for=condition=ready pod \
    -l app=soc-frontend \
    -n "$NAMESPACE" \
    --timeout=60s

log_success "Frontend pod is ready"

# Test frontend
log_info "Testing frontend accessibility..."
sleep 3  # Give ingress a moment to update

if curl -s "http://localhost:8080/" | grep -q "<!DOCTYPE html>"; then
    log_success "Frontend is accessible via ingress"
else
    log_error "Frontend is not accessible"
    exit 1
fi

log_success "All components deployed successfully"
echo ""

# ─────────────────────────────────────────────────
# Step 6: Show Deployment Status
# ─────────────────────────────────────────────────
log_section "Step 6: Deployment Status"
echo ""

log_info "All pods:"
kubectl get pods -n "$NAMESPACE"
echo ""

log_info "All services:"
kubectl get svc -n "$NAMESPACE"
echo ""

log_info "Ingress:"
kubectl get ingress -n "$NAMESPACE"
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
# Step 7: Test Backend API
# ─────────────────────────────────────────────────
log_section "Step 7: Testing Backend API"
echo ""

log_info "Testing backend health endpoint..."
HEALTH_RESPONSE=$(curl -s "http://localhost:8080/health")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    log_success "Backend health check passed"
    echo "  Response: $HEALTH_RESPONSE"
else
    log_error "Backend health check failed"
    echo "  Response: $HEALTH_RESPONSE"
    exit 1
fi

echo ""

# ─────────────────────────────────────────────────
# Step 8: Pre-populate Some Data (Optional)
# ─────────────────────────────────────────────────
log_section "Step 8: Pre-populating Demo Data"
echo ""

log_info "Creating sample threats for demo..."

# Create diverse threat types
THREAT_TYPES=("bot_traffic" "proxy_network" "device_compromise" "geo_anomaly" "rate_limit_breach")
CREATED=0

for threat_type in "${THREAT_TYPES[@]}"; do
    RESPONSE=$(curl -s -X POST "http://localhost:8080/api/threats/trigger" \
        -H "Content-Type: application/json" \
        -d "{\"threat_type\": \"$threat_type\"}")

    if echo "$RESPONSE" | grep -q '"id"'; then
        CREATED=$((CREATED + 1))
        log_info "  ✓ Created $threat_type threat"
    else
        log_warning "  ✗ Failed to create $threat_type threat"
    fi
    sleep 0.5
done

log_success "Created $CREATED sample threats"

# Verify threats are stored
THREAT_COUNT=$(curl -s "http://localhost:8080/api/threats" | jq 'length' 2>/dev/null || echo "0")
log_info "Total threats in system: $THREAT_COUNT"

echo ""

# ─────────────────────────────────────────────────
# Setup Complete!
# ─────────────────────────────────────────────────
log_section "Setup Complete!"
echo ""
log_success "Your K8s demo environment is ready!"
echo ""
echo "📋 What was set up:"
echo "  ✅ Kind cluster: $CLUSTER_NAME (3 nodes)"
echo "  ✅ Namespace: $NAMESPACE"
echo "  ✅ Nginx Ingress Controller"
echo "  ✅ SOC Agent System (backend, frontend, Redis)"
echo "  ✅ HPA configured (2-8 replicas)"
echo "  ✅ Redis state management (verified connectivity)"
echo "  ✅ Sample threats pre-populated ($THREAT_COUNT threats)"
echo ""
echo "🚀 Access the Application:"
echo "  🌐 Web UI:    http://localhost:8080"
echo "  🔍 Health:    curl http://localhost:8080/health"
echo "  📊 API:       curl http://localhost:8080/api/threats"
echo ""
echo "🛠️  Useful Commands:"
echo "  • View all resources:    kubectl get all -n $NAMESPACE"
echo "  • View backend logs:     kubectl logs -n $NAMESPACE -l app=soc-backend --tail=50"
echo "  • Create test threat:    curl -X POST http://localhost:8080/api/threats/trigger \\"
echo "                             -H 'Content-Type: application/json' \\"
echo "                             -d '{\"threat_type\": \"bot_traffic\"}'"
echo "  • Restart backend:       kubectl rollout restart deployment/soc-agent-backend -n $NAMESPACE"
echo ""
echo "📚 Demo Scripts:"
echo "  • Run full demo:         bash soc-agent-system/k8s/demo/run_demo.sh"
echo "  • OpenAI live demo:      bash soc-agent-system/k8s/demo/generate_threat_with_openai.sh"
echo "  • Teardown:              bash soc-agent-system/k8s/demo/teardown_demo.sh"
echo ""
log_info "The environment will remain running until you tear it down."
log_info "Open http://localhost:8080 in your browser to see the dashboard!"
echo ""

