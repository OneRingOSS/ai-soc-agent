#!/bin/bash
# Deploy Sealed Secrets Controller and Demo Secret
# Demonstrates GitOps-safe secret encryption

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Deploying Sealed Secrets${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Install controller if not present
echo -e "${YELLOW}Step 1: Checking if Sealed Secrets controller is installed...${NC}"
if kubectl get deployment sealed-secrets-controller -n kube-system &>/dev/null; then
    echo -e "${GREEN}✅ Controller already installed${NC}"
else
    echo -e "${YELLOW}Installing Sealed Secrets controller v0.24.5...${NC}"
    kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.5/controller.yaml
    echo -e "${YELLOW}Waiting for controller to be ready...${NC}"
    kubectl wait --for=condition=Available --timeout=120s -n kube-system deployment/sealed-secrets-controller
    echo -e "${GREEN}✅ Controller installed${NC}"
fi
echo ""

# Step 2: Verify kubeseal CLI
echo -e "${YELLOW}Step 2: Verifying kubeseal CLI...${NC}"
if command -v kubeseal &>/dev/null; then
    KUBESEAL_VERSION=$(kubeseal --version 2>&1 | head -1)
    echo -e "${GREEN}✅ kubeseal installed: $KUBESEAL_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  kubeseal CLI not found. Installing via Homebrew...${NC}"
    brew install kubeseal
    echo -e "${GREEN}✅ kubeseal installed${NC}"
fi
echo ""

# Step 3: Create demo SealedSecret
echo -e "${YELLOW}Step 3: Creating demo SealedSecret...${NC}"
kubectl create secret generic demo-api-key \
    --from-literal=openai-api-key=sk-demo-1234567890abcdefghijklmnopqrstuvwxyz \
    --from-literal=virustotal-api-key=vt-demo-abcdef1234567890 \
    --namespace=soc-agent-demo \
    --dry-run=client -o yaml | \
    kubeseal -o yaml > $(dirname "$0")/demo-sealed-secret.yaml

echo -e "${GREEN}✅ SealedSecret created: demo-sealed-secret.yaml${NC}"
echo ""

# Step 4: Deploy the SealedSecret
echo -e "${YELLOW}Step 4: Deploying SealedSecret to cluster...${NC}"
kubectl apply -f $(dirname "$0")/demo-sealed-secret.yaml
echo -e "${GREEN}✅ SealedSecret deployed${NC}"
echo ""

# Step 5: Verify the Secret was created
echo -e "${YELLOW}Step 5: Verifying Secret was unsealed...${NC}"
sleep 3
if kubectl get secret demo-api-key -n soc-agent-demo &>/dev/null; then
    echo -e "${GREEN}✅ Secret 'demo-api-key' created successfully${NC}"
    echo -e "${GREEN}   Controller decrypted SealedSecret → Secret${NC}"
else
    echo -e "${YELLOW}⚠️  Secret not yet created, controller may still be processing${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Sealed Secrets Deployed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Verification:${NC}"
echo -e "  kubectl get sealedsecret -n soc-agent-demo"
echo -e "  kubectl get secret demo-api-key -n soc-agent-demo"
echo ""
echo -e "${GREEN}Demo:${NC}"
echo -e "  cat soc-agent-system/k8s/sealed-secrets/demo-sealed-secret.yaml"
echo -e "  # Shows encrypted ciphertext (safe to commit to Git)"
echo ""
echo -e "${GREEN}Security Properties:${NC}"
echo -e "  ✅ Private key never leaves cluster"
echo -e "  ✅ Encrypted secret safe to commit to Git"
echo -e "  ✅ Auto-rotation every 30 days"
echo -e "  ✅ GitOps workflow compatible"
echo ""
