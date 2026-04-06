#!/bin/bash
# Deploy OPA Gatekeeper Policies
# Enforces security constraints at admission time

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}  Deploying OPA Gatekeeper Security Policies${NC}"
echo -e "${YELLOW}════════════════════════════════════════════════════════${NC}"
echo ""

# Check if Gatekeeper is running
echo -e "${YELLOW}Step 1: Checking if Gatekeeper is installed...${NC}"
if ! kubectl get namespace gatekeeper-system &>/dev/null; then
    echo -e "${YELLOW}Installing OPA Gatekeeper...${NC}"
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.15.0/deploy/gatekeeper.yaml
    echo -e "${YELLOW}Waiting for Gatekeeper to be ready...${NC}"
    sleep 10
    kubectl wait --for=condition=Available --timeout=120s -n gatekeeper-system deployment --all
    echo -e "${GREEN}✅ Gatekeeper installed${NC}"
else
    echo -e "${GREEN}✅ Gatekeeper already installed${NC}"
fi
echo ""

# Deploy ConstraintTemplates
echo -e "${YELLOW}Step 2: Deploying ConstraintTemplates...${NC}"
kubectl apply -f $(dirname "$0")/constraint-templates/
echo -e "${GREEN}✅ ConstraintTemplates deployed${NC}"
echo ""

# Wait for CRDs to be ready
echo -e "${YELLOW}Step 3: Waiting for CRDs to be established...${NC}"
sleep 5
echo -e "${GREEN}✅ CRDs ready${NC}"
echo ""

# Deploy Constraints
echo -e "${YELLOW}Step 4: Deploying Constraints...${NC}"
kubectl apply -f $(dirname "$0")/constraints/
echo -e "${GREEN}✅ Constraints deployed${NC}"
echo ""

# Verify deployment
echo -e "${YELLOW}Step 5: Verifying deployment...${NC}"
echo -e "${GREEN}ConstraintTemplates:${NC}"
kubectl get constrainttemplates
echo ""
echo -e "${GREEN}Constraints:${NC}"
kubectl get k8srequiredlabels,k8srequiredprobes,k8sblockautomounttoken -A
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ OPA Gatekeeper Policies Deployed!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Test Policy Enforcement:${NC}"
echo -e "  kubectl apply -f $(dirname "$0")/test-bad-pod.yaml"
echo ""
echo -e "${GREEN}Expected: Admission denied with policy violation message${NC}"
echo ""
