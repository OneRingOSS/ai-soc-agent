#!/bin/bash
# Validation Test Suite
# Runs comprehensive tests to verify nothing is broken after changes

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

FAILED_TESTS=0
PASSED_TESTS=0

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Deployment Validation Test Suite${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Check all pods are running
echo -e "${YELLOW}[Test 1/8] Checking pod status...${NC}"
if kubectl get pods -n soc-agent-demo | grep -E "Running|Completed" | grep -v "Error\|CrashLoop" > /dev/null; then
    echo -e "${GREEN}✅ PASS: All pods are running${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: Some pods are not running${NC}"
    kubectl get pods -n soc-agent-demo
    ((FAILED_TESTS++))
fi
echo ""

# Test 2: Check ServiceMonitor exists
echo -e "${YELLOW}[Test 2/8] Checking ServiceMonitor...${NC}"
if kubectl get servicemonitor soc-agent-backend -n observability &>/dev/null; then
    echo -e "${GREEN}✅ PASS: ServiceMonitor exists${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: ServiceMonitor not found${NC}"
    ((FAILED_TESTS++))
fi
echo ""

# Test 3: Check NetworkPolicy has ingress rules
echo -e "${YELLOW}[Test 3/8] Checking NetworkPolicy ingress rules...${NC}"
if kubectl get networkpolicy soc-backend-egress -n soc-agent-demo -o yaml | grep -q "Ingress"; then
    echo -e "${GREEN}✅ PASS: NetworkPolicy has ingress rules${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: NetworkPolicy missing ingress rules${NC}"
    ((FAILED_TESTS++))
fi
echo ""

# Test 4: Test backend health endpoint (via frontend service)
echo -e "${YELLOW}[Test 4/8] Testing backend health endpoint...${NC}"
POD=$(kubectl get pod -n soc-agent-demo -l app=soc-backend -o jsonpath='{.items[0].metadata.name}')
if curl -sf http://localhost:8080/health &>/dev/null; then
    echo -e "${GREEN}✅ PASS: Backend health endpoint responding${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: Backend health endpoint not responding${NC}"
    ((FAILED_TESTS++))
fi
echo ""

# Test 5: Test metrics endpoint (via port-forward)
echo -e "${YELLOW}[Test 5/8] Testing metrics endpoint...${NC}"
# Start temporary port-forward
kubectl port-forward -n soc-agent-demo deployment/soc-agent-backend 8001:8000 &>/dev/null &
PF_PID=$!
sleep 2
if curl -sf http://localhost:8001/metrics 2>/dev/null | grep -q "soc_threats_processed_total"; then
    echo -e "${GREEN}✅ PASS: Metrics endpoint exposing SOC metrics${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: Metrics endpoint not working${NC}"
    ((FAILED_TESTS++))
fi
kill $PF_PID 2>/dev/null || true
echo ""

# Test 6: Check OpenAI API key is configured
echo -e "${YELLOW}[Test 6/8] Checking OpenAI API key...${NC}"
if kubectl exec -n soc-agent-demo $POD -- env | grep -q "OPENAI_API_KEY=sk-"; then
    echo -e "${GREEN}✅ PASS: OpenAI API key configured${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: OpenAI API key not found${NC}"
    ((FAILED_TESTS++))
fi
echo ""

# Test 7: Check FORCE_MOCK_MODE is false
echo -e "${YELLOW}[Test 7/8] Checking live mode...${NC}"
if kubectl exec -n soc-agent-demo $POD -- env | grep -q "FORCE_MOCK_MODE=false"; then
    echo -e "${GREEN}✅ PASS: Live mode enabled (FORCE_MOCK_MODE=false)${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: Mock mode active${NC}"
    ((FAILED_TESTS++))
fi
echo ""

# Test 8: Test ACT2 adversarial detection
echo -e "${YELLOW}[Test 8/8] Testing ACT2 adversarial detection...${NC}"
RESPONSE=$(curl -sf -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}' 2>/dev/null)

if echo "$RESPONSE" | jq -e '.adversarial_detection.manipulation_detected == true' &>/dev/null; then
    echo -e "${GREEN}✅ PASS: ACT2 detection working (manipulation_detected=true)${NC}"
    ((PASSED_TESTS++))
else
    echo -e "${RED}❌ FAIL: ACT2 detection not working${NC}"
    echo "Response: $RESPONSE" | jq '.adversarial_detection'
    ((FAILED_TESTS++))
fi
echo ""

# Summary
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Validation Results${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}/8"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}/8"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}Deployment is healthy and all features working.${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED!${NC}"
    echo -e "${YELLOW}Review failures above and fix before deploying.${NC}"
    exit 1
fi
