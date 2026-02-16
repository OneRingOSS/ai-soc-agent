#!/bin/bash
# Check if all prerequisites are installed for K8s testing

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

echo "========================================="
echo "Checking Prerequisites for K8s Testing"
echo "========================================="
echo ""

missing=0

# Check kubectl
if command -v kubectl &> /dev/null; then
    version=$(kubectl version --client -o json 2>/dev/null | grep -o '"gitVersion":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    log_success "kubectl installed ($version)"
else
    log_error "kubectl NOT installed"
    ((missing++))
fi

# Check helm
if command -v helm &> /dev/null; then
    version=$(helm version --short 2>/dev/null | grep -o 'v[0-9.]*' || echo "unknown")
    log_success "helm installed ($version)"
else
    log_error "helm NOT installed"
    ((missing++))
fi

# Check kind
if command -v kind &> /dev/null; then
    version=$(kind version 2>/dev/null | grep -o 'v[0-9.]*' || echo "unknown")
    log_success "kind installed ($version)"
else
    log_error "kind NOT installed"
    ((missing++))
fi

# Check docker
if command -v docker &> /dev/null; then
    version=$(docker --version 2>/dev/null | grep -o '[0-9]*\.[0-9]*\.[0-9]*' | head -1 || echo "unknown")
    log_success "docker installed ($version)"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        log_success "Docker daemon is running"
    else
        log_error "Docker daemon is NOT running"
        ((missing++))
    fi
else
    log_error "docker NOT installed"
    ((missing++))
fi

echo ""
echo "========================================="

if [ $missing -eq 0 ]; then
    log_success "All prerequisites are installed!"
    echo ""
    log_info "You can now run the tests:"
    echo "  ./setup_and_test.sh    # Complete setup and test"
    echo "  ./integration_test.sh  # Just integration tests"
    echo "  ./test_connectivity.sh # Just connectivity tests"
    exit 0
else
    log_error "$missing prerequisite(s) missing or not running"
    echo ""
    log_info "Installation instructions (macOS):"
    echo ""
    
    if ! command -v kubectl &> /dev/null; then
        echo "  # Install kubectl:"
        echo "  brew install kubectl"
        echo ""
    fi
    
    if ! command -v helm &> /dev/null; then
        echo "  # Install helm:"
        echo "  brew install helm"
        echo ""
    fi
    
    if ! command -v kind &> /dev/null; then
        echo "  # Install kind:"
        echo "  brew install kind"
        echo ""
    fi
    
    if ! command -v docker &> /dev/null; then
        echo "  # Install Docker Desktop:"
        echo "  Download from: https://www.docker.com/products/docker-desktop"
        echo "  Or: brew install --cask docker"
        echo ""
    fi
    
    echo "After installation, run this script again to verify."
    exit 1
fi

