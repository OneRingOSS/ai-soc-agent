#!/bin/bash
# Setup OpenAI API Key for Live Mode
# Creates Kubernetes secret for backend to use real OpenAI API calls

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  OpenAI API Key Setup${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

NAMESPACE=${1:-soc-agent-demo}

# Check if API key is in environment
if [ -n "$OPENAI_API_KEY" ]; then
    echo -e "${GREEN}✅ Found OPENAI_API_KEY in environment${NC}"
    API_KEY="$OPENAI_API_KEY"
else
    # Prompt for API key
    echo -e "${YELLOW}Enter your OpenAI API key:${NC}"
    echo -e "${YELLOW}(Get one from: https://platform.openai.com/api-keys)${NC}"
    read -s API_KEY
    echo ""
    
    if [ -z "$API_KEY" ]; then
        echo -e "${RED}❌ No API key provided${NC}"
        exit 1
    fi
fi

# Validate format (sk-...)
if [[ ! "$API_KEY" =~ ^sk- ]]; then
    echo -e "${RED}❌ Invalid API key format (should start with 'sk-')${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API key format valid${NC}"
echo ""

# Check if secret already exists
if kubectl get secret openai-api-key -n "$NAMESPACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Secret 'openai-api-key' already exists${NC}"
    echo -e "${YELLOW}Delete it? (y/N):${NC}"
    read -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete secret openai-api-key -n "$NAMESPACE"
        echo -e "${GREEN}✅ Deleted existing secret${NC}"
    else
        echo -e "${YELLOW}Cancelled${NC}"
        exit 0
    fi
fi

# Create secret
echo -e "${YELLOW}Creating Kubernetes secret...${NC}"
kubectl create secret generic openai-api-key \
    --from-literal=OPENAI_API_KEY="$API_KEY" \
    -n "$NAMESPACE"

echo -e "${GREEN}✅ Secret created successfully${NC}"
echo ""

# Update deployment to use secret
echo -e "${YELLOW}Updating backend deployment...${NC}"
kubectl set env deployment/soc-agent-backend \
    --from=secret/openai-api-key \
    -n "$NAMESPACE"

echo -e "${GREEN}✅ Deployment updated${NC}"
echo ""

# Wait for rollout
echo -e "${YELLOW}Waiting for pods to restart...${NC}"
kubectl rollout status deployment/soc-agent-backend -n "$NAMESPACE" --timeout=120s

echo -e "${GREEN}✅ Pods restarted${NC}"
echo ""

# Verify
echo -e "${YELLOW}Verifying configuration...${NC}"
POD=$(kubectl get pod -n "$NAMESPACE" -l app=soc-backend -o jsonpath='{.items[0].metadata.name}')
if kubectl exec -n "$NAMESPACE" "$POD" -- env | grep -q "OPENAI_API_KEY=sk-"; then
    echo -e "${GREEN}✅ OpenAI API key configured in pod${NC}"
else
    echo -e "${RED}❌ API key not found in pod environment${NC}"
    exit 1
fi

# Check logs for mock mode
echo -e "${YELLOW}Checking backend logs...${NC}"
sleep 5
if kubectl logs -n "$NAMESPACE" "$POD" --tail=20 | grep -q "use_mock=False"; then
    echo -e "${GREEN}✅ Live mode active (use_mock=False)${NC}"
else
    echo -e "${YELLOW}⚠️  Could not confirm live mode from logs${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ OpenAI API Key Setup Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "Backend will now use real OpenAI API calls for LLM analysis."
echo "VT enrichment still uses cache (DEMO_MODE=true)."
echo ""
echo "To verify:"
echo "  kubectl logs -n $NAMESPACE -l app=soc-backend --tail=50 | grep 'use_mock'"
echo ""
