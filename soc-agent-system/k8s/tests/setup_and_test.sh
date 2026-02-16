#!/bin/bash
# Complete setup and test script for SOC Agent Kubernetes deployment
# This script will:
# 1. Check prerequisites (kubectl, helm, kind, docker)
# 2. Create Kind cluster
# 3. Build Docker images
# 4. Load images into Kind
# 5. Run integration tests
# 6. Run connectivity tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Configuration
CLUSTER_NAME="${CLUSTER_NAME:-soc-agent-cluster}"
NAMESPACE="${NAMESPACE:-soc-agent-test}"
RELEASE_NAME="${RELEASE_NAME:-soc-agent-test}"

# Check prerequisites
check_prerequisites() {
    log_info "========================================="
    log_info "Checking Prerequisites"
    log_info "========================================="
    
    local missing=0
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Install: brew install kubectl"
        ((missing++))
    else
        log_success "kubectl found ($(kubectl version --client -o json 2>/dev/null | grep -o '"gitVersion":"[^"]*"' | cut -d'"' -f4))"
    fi
    
    if ! command -v helm &> /dev/null; then
        log_error "helm not found. Install: brew install helm"
        ((missing++))
    else
        log_success "helm found ($(helm version --short 2>/dev/null || echo 'installed'))"
    fi
    
    if ! command -v kind &> /dev/null; then
        log_error "kind not found. Install: brew install kind"
        ((missing++))
    else
        log_success "kind found ($(kind version 2>/dev/null | grep -o 'v[0-9.]*' || echo 'installed'))"
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "docker not found. Install Docker Desktop"
        ((missing++))
    else
        log_success "docker found ($(docker --version | grep -o '[0-9]*\.[0-9]*\.[0-9]*' | head -1))"
    fi
    
    if [ $missing -gt 0 ]; then
        log_error "$missing prerequisite(s) missing. Please install them first."
        echo ""
        log_info "Quick install (macOS):"
        echo "  brew install kubectl helm kind"
        echo "  # Install Docker Desktop from https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    log_success "All prerequisites installed!"
    echo ""
}

# Create Kind cluster
create_cluster() {
    log_info "========================================="
    log_info "Creating Kind Cluster"
    log_info "========================================="
    
    if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
        log_warning "Cluster '${CLUSTER_NAME}' already exists"
        read -p "Delete and recreate? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deleting existing cluster..."
            kind delete cluster --name "$CLUSTER_NAME"
        else
            log_info "Using existing cluster"
            return 0
        fi
    fi
    
    log_info "Creating Kind cluster '${CLUSTER_NAME}'..."
    if kind create cluster --name "$CLUSTER_NAME" --config ../kind-config.yaml; then
        log_success "Kind cluster created successfully"
    else
        log_error "Failed to create Kind cluster"
        exit 1
    fi
    
    # Verify cluster is ready
    log_info "Waiting for cluster to be ready..."
    kubectl cluster-info --context "kind-${CLUSTER_NAME}"
    log_success "Cluster is ready!"
    echo ""
}

# Build Docker images
build_images() {
    log_info "========================================="
    log_info "Building Docker Images"
    log_info "========================================="
    
    # Build backend
    log_info "Building backend image..."
    cd ../../backend
    if docker build -t soc-backend:latest -f Dockerfile .; then
        log_success "Backend image built successfully"
    else
        log_error "Failed to build backend image"
        exit 1
    fi
    
    # Build frontend
    log_info "Building frontend image..."
    cd ../frontend
    if docker build -t soc-frontend:latest -f Dockerfile .; then
        log_success "Frontend image built successfully"
    else
        log_error "Failed to build frontend image"
        exit 1
    fi
    
    cd ../k8s/tests
    echo ""
}

# Load images into Kind
load_images() {
    log_info "========================================="
    log_info "Loading Images into Kind"
    log_info "========================================="
    
    log_info "Loading backend image..."
    if kind load docker-image soc-backend:latest --name "$CLUSTER_NAME"; then
        log_success "Backend image loaded into Kind"
    else
        log_error "Failed to load backend image"
        exit 1
    fi
    
    log_info "Loading frontend image..."
    if kind load docker-image soc-frontend:latest --name "$CLUSTER_NAME"; then
        log_success "Frontend image loaded into Kind"
    else
        log_error "Failed to load frontend image"
        exit 1
    fi
    
    echo ""
}

# Main execution
main() {
    log_info "========================================="
    log_info "SOC Agent K8s Setup and Test"
    log_info "========================================="
    echo ""
    
    check_prerequisites
    create_cluster
    build_images
    load_images
    
    # Run integration tests
    log_info "========================================="
    log_info "Running Integration Tests"
    log_info "========================================="
    ./integration_test.sh
    
    echo ""
    
    # Run connectivity tests
    log_info "========================================="
    log_info "Running Connectivity Tests"
    log_info "========================================="
    ./test_connectivity.sh
    
    echo ""
    log_success "========================================="
    log_success "All Tests Completed Successfully!"
    log_success "========================================="
}

main "$@"

