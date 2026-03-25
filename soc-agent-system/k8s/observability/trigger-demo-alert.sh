#!/bin/bash
# =============================================================================
# Trigger Demo Alert - For Interview Demonstrations
# =============================================================================
# This script temporarily scales down the SOC agent backend to trigger alerts
# WARNING: Only use for demo purposes!
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

echo ""
log_warning "This will temporarily scale down the SOC agent backend to trigger alerts"
log_warning "The 'SOCAgentBackendDown' alert should fire within 1-2 minutes"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

log_info "Scaling backend to 0 replicas..."
kubectl scale deployment soc-agent-backend -n soc-agent-demo --replicas=0

log_success "Backend scaled down"
echo ""
log_info "Wait 1-2 minutes, then check:"
echo "  • Prometheus Alerts: http://localhost:9090/alerts (filter for 'SOCAgentBackendDown')"
echo "  • AlertManager: http://localhost:9093 (should show the alert)"
echo ""
log_warning "To restore the backend, run:"
echo "  kubectl scale deployment soc-agent-backend -n soc-agent-demo --replicas=2"
echo ""

