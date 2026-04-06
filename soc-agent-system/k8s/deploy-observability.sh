#!/bin/bash
# Deploy Observability Stack (Prometheus, Grafana, Loki, Jaeger)
# Run this once per cluster to enable metrics, logging, and tracing

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Observability Stack Deployment${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Create observability namespace
echo -e "${YELLOW}[1/4] Creating observability namespace...${NC}"
kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
echo -e "${GREEN}✅ Namespace created${NC}"
echo ""

# Step 2: Add Helm repos
echo -e "${YELLOW}[2/4] Adding Helm repositories...${NC}"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
echo -e "${GREEN}✅ Helm repos added${NC}"
echo ""

# Step 3: Install kube-prometheus-stack (Prometheus + Grafana)
echo -e "${YELLOW}[3/4] Installing kube-prometheus-stack...${NC}"
if helm list -n observability | grep -q kube-prometheus-stack; then
    echo "  kube-prometheus-stack already installed, upgrading..."
    helm upgrade kube-prometheus-stack prometheus-community/kube-prometheus-stack \
        --namespace observability \
        --set grafana.admin Password=admin \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --wait --timeout 5m
else
    echo "  Installing kube-prometheus-stack..."
    helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
        --namespace observability \
        --set grafana.adminPassword=admin \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --wait --timeout 5m
fi
echo -e "${GREEN}✅ kube-prometheus-stack installed${NC}"
echo ""

# Step 4: Install Loki (Logging)
echo -e "${YELLOW}[3.5/4] Installing Loki...${NC}"
if helm list -n observability | grep -q loki; then
    echo "  Loki already installed, skipping..."
else
    echo "  Installing Loki..."
    helm install loki grafana/loki \
        --namespace observability \
        --set loki.auth_enabled=false \
        --set loki.commonConfig.replication_factor=1 \
        --set loki.storage.type=filesystem \
        --wait --timeout 5m
fi
echo -e "${GREEN}✅ Loki installed${NC}"
echo ""

# Step 5: Install Jaeger (Tracing)
echo -e "${YELLOW}[4/4] Installing Jaeger...${NC}"
if helm list -n observability | grep -q jaeger; then
    echo "  Jaeger already installed, skipping..."
else
    echo "  Installing Jaeger..."
    helm install jaeger jaegertracing/jaeger \
        --namespace observability \
        --set provisionDataStore.cassandra=false \
        --set allInOne.enabled=true \
        --set storage.type=memory \
        --set agent.enabled=false \
        --set collector.enabled=false \
        --set query.enabled=false \
        --wait --timeout 5m
fi
echo -e "${GREEN}✅ Jaeger installed${NC}"
echo ""

# Step 6: Wait for pods to be ready
echo -e "${YELLOW}Waiting for all pods to be ready...${NC}"
kubectl wait --for=condition=Ready pod --all -n observability --timeout=300s || echo "Some pods may still be starting..."
echo ""

# Step 7: Show status
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Observability Stack Deployed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "Installed components:"
echo "  ✅ Prometheus (metrics collection)"
echo "  ✅ Grafana (dashboards)"
echo "  ✅ Loki (log aggregation)"
echo "  ✅ Jaeger (distributed tracing)"
echo ""
echo "Pod status:"
kubectl get pods -n observability
echo ""
echo "Services:"
kubectl get svc -n observability | grep -E "NAME|prometheus-stack-grafana|prometheus-stack-prometheus|loki|jaeger"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Start port-forwards:"
echo "   bash soc-agent-system/k8s/startup-cluster-services.sh"
echo ""
echo "2. Access services:"
echo "   📊 Grafana:    http://localhost:3000  (admin / admin)"
echo "   📈 Prometheus: http://localhost:9090"
echo "   📝 Loki:       http://localhost:3100"
echo "   🔍 Jaeger:     http://localhost:16686"
echo ""
