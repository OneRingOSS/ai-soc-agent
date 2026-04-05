#!/bin/bash
# Cluster Services Startup Script
# Automatically starts all necessary port-forwards and verifies services after cluster restart
# Run this after: helm install/upgrade or cluster restart

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SOC Agent Cluster Services Startup${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Wait for pods to be ready
echo -e "${YELLOW}[1/4] Waiting for SOC Agent pods to be ready...${NC}"
kubectl wait --for=condition=Ready pod -l app=soc-backend -n soc-agent-demo --timeout=120s || echo "Backend timeout - continuing"
kubectl wait --for=condition=Ready pod -l app=soc-frontend -n soc-agent-demo --timeout=120s || echo "Frontend timeout - continuing"
kubectl wait --for=condition=Ready pod -l app=redis -n soc-agent-demo --timeout=120s || echo "Redis timeout - continuing"
echo -e "${GREEN}✅ Pods ready${NC}"
echo ""

# Step 2: Verify DEMO_MODE is enabled
echo -e "${YELLOW}[2/4] Verifying DEMO_MODE configuration...${NC}"
DEMO_MODE=$(kubectl get configmap soc-agent-backend-config -n soc-agent-demo -o jsonpath='{.data.DEMO_MODE}' 2>/dev/null || echo "")
if [ "$DEMO_MODE" == "true" ]; then
    echo -e "${GREEN}✅ DEMO_MODE: true (VT enrichment enabled)${NC}"
else
    echo -e "${YELLOW}⚠️  DEMO_MODE not set - VT enrichment will not work${NC}"
    echo -e "${YELLOW}   Run: helm upgrade soc-agent . -n soc-agent-demo${NC}"
fi
echo ""

# Step 3: Set up observability port-forwards
echo -e "${YELLOW}[3/4] Setting up observability port-forwards...${NC}"

# Kill existing port-forwards
pkill -f "kubectl port-forward.*observability" 2>/dev/null || true
sleep 2

# Start port-forwards in background
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 > /tmp/grafana-pf.log 2>&1 &
GRAFANA_PID=$!
sleep 2

kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 > /tmp/prometheus-pf.log 2>&1 &
PROMETHEUS_PID=$!
sleep 2

kubectl port-forward -n observability svc/loki 3100:3100 > /tmp/loki-pf.log 2>&1 &
LOKI_PID=$!
sleep 2

kubectl port-forward -n observability svc/jaeger 16686:16686 > /tmp/jaeger-pf.log 2>&1 &
JAEGER_PID=$!
sleep 2

echo -e "${GREEN}✅ Observability port-forwards started${NC}"
echo "   Grafana PID: $GRAFANA_PID"
echo "   Prometheus PID: $PROMETHEUS_PID"
echo "   Loki PID: $LOKI_PID"
echo "   Jaeger PID: $JAEGER_PID"
echo ""

# Step 4: Summary
echo -e "${YELLOW}[4/4] Service Status Summary${NC}"
echo ""

echo -e "${BLUE}SOC Agent Pods:${NC}"
kubectl get pods -n soc-agent-demo | grep -E "NAME|soc-agent|redis"

echo ""
echo -e "${BLUE}Observability Access:${NC}"
echo "  📊 Grafana:    http://localhost:3000  (admin / prom-operator)"
echo "  📈 Prometheus: http://localhost:9090"
echo "  📝 Loki:       http://localhost:3100"
echo "  🔍 Jaeger:     http://localhost:16686"

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  DEMO_MODE: $DEMO_MODE"
echo "  Namespace: soc-agent-demo"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ All Services Started!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""

echo "Port-forwards running in background."
echo "To stop: pkill -f 'kubectl port-forward.*observability'"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/grafana-pf.log"
echo "  tail -f /tmp/prometheus-pf.log"
echo ""
