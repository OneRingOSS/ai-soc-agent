#!/bin/bash
# Deploy Observability Stack to Kubernetes
# Deploys Prometheus, Grafana, Jaeger, and Loki using Helm charts
#
# Usage:
#   ./deploy-observability.sh              # Deploy observability stack
#   ./deploy-observability.sh --cleanup    # Remove observability stack
#   ./deploy-observability.sh --help       # Show help

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
NAMESPACE="observability"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Helper functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}"; }

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --cleanup)
                cleanup_observability
                exit 0
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --cleanup    Remove observability stack"
                echo "  --help       Show this help message"
                echo ""
                echo "Components:"
                echo "  - Prometheus (metrics collection)"
                echo "  - Grafana (visualization)"
                echo "  - Jaeger (distributed tracing)"
                echo "  - Loki (log aggregation)"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Cleanup function
cleanup_observability() {
    log_section "Cleaning Up Observability Stack"
    echo ""
    
    log_info "Uninstalling Helm releases..."
    helm uninstall kube-prometheus-stack -n "$NAMESPACE" 2>/dev/null || log_warning "kube-prometheus-stack not found"
    helm uninstall jaeger -n "$NAMESPACE" 2>/dev/null || log_warning "jaeger not found"
    helm uninstall loki -n "$NAMESPACE" 2>/dev/null || log_warning "loki not found"
    
    log_info "Deleting namespace..."
    kubectl delete namespace "$NAMESPACE" --timeout=60s 2>/dev/null || log_warning "namespace not found"
    
    log_success "Cleanup complete"
}

# Deploy Prometheus + Grafana using kube-prometheus-stack
deploy_prometheus_grafana() {
    log_info "Deploying Prometheus + Grafana (kube-prometheus-stack)..."
    
    # Add Prometheus community Helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
    helm repo update
    
    # Deploy kube-prometheus-stack (includes Prometheus, Grafana, Alertmanager)
    helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
        --namespace "$NAMESPACE" \
        --create-namespace \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set grafana.adminPassword=admin \
        --set grafana.service.type=ClusterIP \
        --set prometheus.service.type=ClusterIP \
        --wait --timeout=300s
    
    log_success "Prometheus + Grafana deployed"
}

# Deploy Jaeger for distributed tracing
deploy_jaeger() {
    log_info "Deploying Jaeger..."
    
    # Add Jaegertracing Helm repo
    helm repo add jaegertracing https://jaegertracing.github.io/helm-charts 2>/dev/null || true
    helm repo update
    
    # Deploy Jaeger all-in-one
    helm install jaeger jaegertracing/jaeger \
        --namespace "$NAMESPACE" \
        --set provisionDataStore.cassandra=false \
        --set allInOne.enabled=true \
        --set storage.type=memory \
        --set agent.enabled=false \
        --set collector.enabled=false \
        --set query.enabled=false \
        --wait --timeout=180s
    
    log_success "Jaeger deployed"
}

# Deploy Loki for log aggregation
deploy_loki() {
    log_info "Deploying Loki + Promtail..."
    
    # Add Grafana Helm repo
    helm repo add grafana https://grafana.github.io/helm-charts 2>/dev/null || true
    helm repo update
    
    # Deploy Loki stack (includes Loki + Promtail)
    helm install loki grafana/loki-stack \
        --namespace "$NAMESPACE" \
        --set loki.enabled=true \
        --set promtail.enabled=true \
        --set grafana.enabled=false \
        --wait --timeout=180s
    
    log_success "Loki + Promtail deployed"
}

# Main deployment
main() {
    log_section "Deploying K8s Observability Stack"
    echo ""
    
    # Deploy components
    deploy_prometheus_grafana
    echo ""
    deploy_jaeger
    echo ""
    deploy_loki
    echo ""
    
    log_section "Deployment Complete"
    echo ""
    log_success "All observability components deployed!"
    echo ""
    log_info "Access services via port-forward:"
    echo "  Grafana:    kubectl port-forward -n $NAMESPACE svc/kube-prometheus-stack-grafana 3000:80"
    echo "  Prometheus: kubectl port-forward -n $NAMESPACE svc/kube-prometheus-stack-prometheus 9090:9090"
    echo "  Jaeger:     kubectl port-forward -n $NAMESPACE svc/jaeger-query 16686:16686"
    echo ""
    log_info "Grafana credentials: admin / admin"
}

# Parse arguments
parse_args "$@"

# Run main
main

