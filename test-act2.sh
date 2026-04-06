#!/bin/bash
# Test ACT2 adversarial detection
# Should show adversarial badge with 18 poisoned notes detected

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}  Testing ACT2: Note Poisoning (Catch)${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

echo -e "${GREEN}Triggering ACT2 (detector ENABLED)...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"adversarial_scenario": "note_poisoning_catch", "adversarial_detector_enabled": true}')

echo ""
echo -e "${YELLOW}Response Summary:${NC}"
echo "$RESPONSE" | jq '{
  id: .id,
  customer: .signal.customer_name,
  severity: .severity,
  manipulation_detected: .adversarial_detection.manipulation_detected,
  confidence: .adversarial_detection.confidence,
  attack_vector: .adversarial_detection.attack_vector,
  anomaly_count: (.adversarial_detection.anomalies | length),
  fp_score: .false_positive_score.score
}'

echo ""
MANIPULATION=$(echo "$RESPONSE" | jq -r '.adversarial_detection.manipulation_detected')
if [ "$MANIPULATION" = "true" ]; then
    echo -e "${GREEN}✅ SUCCESS: Adversarial manipulation detected!${NC}"
    echo ""
    echo -e "${YELLOW}Anomalies:${NC}"
    echo "$RESPONSE" | jq '.adversarial_detection.anomalies'
else
    echo -e "${RED}❌ FAILURE: No adversarial manipulation detected!${NC}"
    echo ""
    echo -e "${YELLOW}Debugging info:${NC}"
    echo "Adversarial detector enabled: $(echo "$RESPONSE" | jq '.adversarial_detection')"
fi

echo ""
echo -e "${YELLOW}Full response saved to: /tmp/act2-response.json${NC}"
echo "$RESPONSE" | jq '.' > /tmp/act2-response.json
