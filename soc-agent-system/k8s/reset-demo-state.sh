#!/bin/bash
# Demo State Reset Script
# Clears all demo data from Redis to prevent false positives between demo runs

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  SOC Agent Demo State Reset${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Check namespace
NAMESPACE=${1:-soc-agent-demo}
echo -e "${YELLOW}Target namespace: ${NAMESPACE}${NC}"
echo ""

# Step 1: Check Redis is accessible
echo -e "${YELLOW}[1/4] Checking Redis connectivity...${NC}"
if ! kubectl get pod -n "$NAMESPACE" -l app=redis &>/dev/null; then
    echo -e "${RED}❌ Redis pod not found in namespace: $NAMESPACE${NC}"
    echo -e "${YELLOW}Available namespaces:${NC}"
    kubectl get namespaces
    exit 1
fi

REDIS_POD=$(kubectl get pod -n "$NAMESPACE" -l app=redis -o jsonpath='{.items[0].metadata.name}')
echo -e "${GREEN}✅ Redis pod: $REDIS_POD${NC}"
echo ""

# Step 2: Show current Redis keys
echo -e "${YELLOW}[2/4] Current Redis keys...${NC}"
echo ""
echo -e "${BLUE}Threat keys:${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "threat:*" | head -5
THREAT_COUNT=$(kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "threat:*" | wc -l)
echo -e "Total: ${THREAT_COUNT} threat keys"
echo ""

echo -e "${BLUE}VT cache keys:${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "vt:pkg:*"
VT_COUNT=$(kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "vt:pkg:*" | wc -l)
echo -e "Total: ${VT_COUNT} VT cache keys"
echo ""

echo -e "${BLUE}Other keys:${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "*" | grep -v "^threat:" | grep -v "^vt:pkg:" || echo "(none)"
echo ""

# Step 3: Ask for confirmation
echo -e "${YELLOW}[3/4] Confirm cleanup${NC}"
echo ""
echo -e "${RED}WARNING: This will delete:${NC}"
echo -e "  - All threat analysis results (threat:*, threats:*)"
echo -e "  - All historical incidents (historical:*, incidents:*)"
echo -e "  - Threat counter (threats:total_count)"
echo ""
echo -e "${GREEN}This will KEEP:${NC}"
echo -e "  - VT cache (vt:pkg:*) - demo data needed for enrichment"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled by user${NC}"
    exit 0
fi
echo ""

# Step 4: Clean up Redis
echo -e "${YELLOW}[4/4] Cleaning Redis...${NC}"

# Delete threat keys
echo -e "${BLUE}Deleting threat keys...${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli --scan --pattern "threat:*" | \
    xargs -I {} kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli DEL {} 2>/dev/null || true

# Delete threats sorted set
echo -e "${BLUE}Deleting threats:by_created...${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli DEL "threats:by_created" || true

# Delete threat counter
echo -e "${BLUE}Resetting threats:total_count...${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli DEL "threats:total_count" || true

# Delete historical incident keys (if they exist)
echo -e "${BLUE}Deleting historical incident keys...${NC}"
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli --scan --pattern "historical:*" | \
    xargs -I {} kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli DEL {} 2>/dev/null || true
kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli --scan --pattern "incidents:*" | \
    xargs -I {} kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli DEL {} 2>/dev/null || true

echo -e "${GREEN}✅ Redis cleanup complete${NC}"
echo ""

# Step 5: Verify cleanup
echo -e "${YELLOW}Verifying cleanup...${NC}"
REMAINING_THREATS=$(kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "threat:*" | wc -l)
REMAINING_VT=$(kubectl exec -n "$NAMESPACE" "$REDIS_POD" -- redis-cli KEYS "vt:pkg:*" | wc -l)

echo ""
echo -e "${BLUE}After cleanup:${NC}"
echo -e "  Threats: ${REMAINING_THREATS} (should be 0)"
echo -e "  VT cache: ${REMAINING_VT} (should be 3 - preserved)"
echo ""

if [ "$REMAINING_THREATS" -eq 0 ]; then
    echo -e "${GREEN}✅ All threat data cleared${NC}"
else
    echo -e "${RED}⚠️  Some threat keys remain - manual cleanup may be needed${NC}"
fi

# Step 6: Restart backend pods to clear in-memory state
echo ""
echo -e "${YELLOW}Restarting backend pods to clear in-memory state...${NC}"
kubectl rollout restart deployment/soc-agent-backend -n "$NAMESPACE" &>/dev/null || true
echo -e "${GREEN}✅ Backend pods restarting${NC}"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Demo State Reset Complete!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Frontend should now show no threats."
echo "VT enrichment cache preserved - new threats will show malware findings."
echo ""
echo "To verify:"
echo "  kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli KEYS \"threat:*\""
echo "  (should return: (empty array))"
echo ""
