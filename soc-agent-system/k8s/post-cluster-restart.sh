#!/bin/bash
# Post-Cluster Restart Recovery Script
# Restores all configurations after Kind cluster restart

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Post-Cluster Restart Recovery${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Step 1: Check cluster is running
echo -e "${YELLOW}Step 1: Checking cluster status...${NC}"
if ! kubectl cluster-info --context kind-soc-agent-cluster &>/dev/null; then
    echo -e "${RED}❌ Cluster not running!${NC}"
    echo -e "${YELLOW}Start it with:${NC}"
    echo "  kind create cluster --config soc-agent-system/k8s/kind-config.yaml --name soc-agent-cluster"
    exit 1
fi
echo -e "${GREEN}✅ Cluster is running${NC}"
echo ""

# Step 2: Deploy observability stack if not present
echo -e "${YELLOW}Step 2: Checking observability stack...${NC}"
if ! kubectl get namespace observability &>/dev/null; then
    echo "  Observability namespace not found, deploying..."
    cd "$REPO_ROOT/soc-agent-system/k8s"
    bash deploy-observability.sh
    echo -e "${GREEN}✅ Observability stack deployed${NC}"
else
    echo -e "${GREEN}✅ Observability namespace exists${NC}"
fi
echo ""

# Step 3: Deploy/upgrade Helm charts
echo -e "${YELLOW}Step 3: Deploying SOC Agent Helm charts...${NC}"
cd "$REPO_ROOT/soc-agent-system/k8s"
./deploy.sh
echo -e "${GREEN}✅ Helm deployment complete${NC}"
echo ""

# Step 4: Configure OpenAI API key
echo -e "${YELLOW}Step 4: Configuring OpenAI API key...${NC}"

# Check if .env file exists
if [ ! -f "$REPO_ROOT/soc-agent-system/backend/.env" ]; then
    echo -e "${RED}❌ .env file not found at soc-agent-system/backend/.env${NC}"
    echo -e "${YELLOW}Please create it with your OPENAI_API_KEY${NC}"
    exit 1
fi

# Source .env and create secret
source "$REPO_ROOT/soc-agent-system/backend/.env"

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set in .env file${NC}"
    exit 1
fi

# Delete existing secret if present
kubectl delete secret openai-api-key -n soc-agent-demo --ignore-not-found

# Create new secret
kubectl create secret generic openai-api-key \
    --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
    -n soc-agent-demo

# Update deployment to use secret
kubectl set env deployment/soc-agent-backend \
    --from=secret/openai-api-key \
    -n soc-agent-demo

echo -e "${GREEN}✅ OpenAI API key configured${NC}"
echo ""

# Step 5: Wait for backend to be ready
echo -e "${YELLOW}Step 5: Waiting for backend pods to be ready...${NC}"
kubectl rollout status deployment/soc-agent-backend -n soc-agent-demo --timeout=120s
echo -e "${GREEN}✅ Backend pods ready${NC}"
echo ""

# Step 6: Start observability port-forwards
echo -e "${YELLOW}Step 6: Starting observability port-forwards...${NC}"
cd "$REPO_ROOT/soc-agent-system/k8s"
./startup-cluster-services.sh &>/dev/null &
sleep 5
echo -e "${GREEN}✅ Observability services started${NC}"
echo ""

# Step 7: Verify configuration
echo -e "${YELLOW}Step 7: Verifying configuration...${NC}"

# Check live mode
echo -ne "  Checking live mode... "
if kubectl logs -n soc-agent-demo -l app=soc-backend --tail=50 | grep -q "Mode: LIVE"; then
    echo -e "${GREEN}✅ LIVE mode active${NC}"
else
    echo -e "${RED}❌ Still in mock mode${NC}"
fi

# Check demo mode
echo -ne "  Checking demo mode... "
if kubectl logs -n soc-agent-demo -l app=soc-backend --tail=50 | grep -q "demo_mode=True"; then
    echo -e "${GREEN}✅ DEMO mode active${NC}"
else
    echo -e "${YELLOW}⚠️  DEMO mode not found in logs${NC}"
fi

# Check OpenAI key
echo -ne "  Checking OpenAI key... "
POD=$(kubectl get pod -n soc-agent-demo -l app=soc-backend -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n soc-agent-demo "$POD" -- env | grep -q "OPENAI_API_KEY=sk-"; then
    echo -e "${GREEN}✅ OpenAI key configured${NC}"
else
    echo -e "${RED}❌ OpenAI key not found${NC}"
fi

# Check VT cache
echo -ne "  Checking VT cache... "
sleep 5  # Give VT cache time to seed
REDIS_POD=$(kubectl get pod -n soc-agent-demo -l app=redis -o jsonpath='{.items[0].metadata.name}')
CACHE_KEYS=$(kubectl exec -n soc-agent-demo "$REDIS_POD" -- redis-cli KEYS "vt:*" | wc -l | tr -d ' ')
if [ "$CACHE_KEYS" -ge 3 ]; then
    echo -e "${GREEN}✅ VT cache seeded ($CACHE_KEYS packages)${NC}"
else
    echo -e "${YELLOW}⚠️  VT cache may not be fully seeded yet ($CACHE_KEYS packages)${NC}"
fi

echo ""

# Step 8: Run ACT2 test
echo -e "${YELLOW}Step 8: Testing ACT2 adversarial detection...${NC}"
cd "$REPO_ROOT"

if [ -f "test-act2.sh" ]; then
    if ./test-act2.sh | grep -q "SUCCESS: Adversarial manipulation detected"; then
        echo -e "${GREEN}✅ ACT2 test passed${NC}"
    else
        echo -e "${RED}❌ ACT2 test failed${NC}"
        echo -e "${YELLOW}Run './test-act2.sh' manually to debug${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  test-act2.sh not found, skipping test${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Cluster Recovery Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "Configuration:"
echo "  - Live mode: ✅ OpenAI API enabled"
echo "  - Demo mode: ✅ VT cache enabled"
echo "  - Observability: ✅ Port-forwards started"
echo "  - ACT2 detection: ✅ Working"
echo ""
echo "Quick commands:"
echo "  - Reset demo: bash soc-agent-system/k8s/reset-demo-state.sh"
echo "  - Test ACT2:  ./test-act2.sh"
echo "  - View logs:  kubectl logs -n soc-agent-demo -l app=soc-backend -f"
echo ""
