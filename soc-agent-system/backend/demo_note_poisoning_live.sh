#!/bin/bash
# Live Demo Script for Historical Note Poisoning Detection
# This script demonstrates the attack in a real-world scenario with the UX running
# Works with both local backend and Kind cluster deployments

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "🎬 LIVE DEMO: Historical Note Poisoning Detection"
echo "================================================================================"
echo ""
echo "This demo shows a REAL-WORLD attack scenario where:"
echo "  • Threats appear in the actual UX threat feed"
echo "  • The adversarial detector catches fabricated analyst notes"
echo "  • You can see the detection in both logs AND the UI"
echo ""
echo "================================================================================"
echo ""

# Detect deployment type
DEPLOYMENT_TYPE="unknown"
BACKEND_URL=""
FRONTEND_URL=""
NAMESPACE="soc-agent-demo"

echo -e "${BLUE}[1/6] Detecting deployment type...${NC}"

# Check for Kind cluster
if kubectl get namespace "$NAMESPACE" > /dev/null 2>&1; then
    echo -e "${CYAN}Found Kind cluster deployment in namespace: $NAMESPACE${NC}"
    DEPLOYMENT_TYPE="kind"

    # Check if ingress is accessible
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        BACKEND_URL="http://localhost:8080"
        FRONTEND_URL="http://localhost:8080"
        echo -e "${GREEN}✅ Kind cluster accessible via ingress at localhost:8080${NC}"
    else
        echo -e "${YELLOW}⚠️  Ingress not accessible. Setting up port-forward...${NC}"

        # Kill any existing port-forwards
        pkill -f "kubectl port-forward.*soc-agent-backend" 2>/dev/null || true

        # Start port-forward in background
        kubectl port-forward -n "$NAMESPACE" svc/soc-agent-backend 8000:8000 > /dev/null 2>&1 &
        PF_PID=$!
        sleep 3

        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            BACKEND_URL="http://localhost:8000"
            FRONTEND_URL="http://localhost:8080"  # Ingress for frontend
            echo -e "${GREEN}✅ Port-forward established (PID: $PF_PID)${NC}"
        else
            echo -e "${RED}❌ Failed to establish port-forward${NC}"
            exit 1
        fi
    fi
# Check for local backend
elif curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${CYAN}Found local backend deployment${NC}"
    DEPLOYMENT_TYPE="local"
    BACKEND_URL="http://localhost:8000"
    FRONTEND_URL="http://localhost:3000"
    echo -e "${GREEN}✅ Local backend accessible at localhost:8000${NC}"
else
    echo -e "${RED}❌ No backend found${NC}"
    echo ""
    echo "Please start either:"
    echo ""
    echo "Option 1: Kind Cluster"
    echo "  cd soc-agent-system/k8s"
    echo "  ./deploy.sh"
    echo "  # Access via http://localhost:8080"
    echo ""
    echo "Option 2: Local Backend"
    echo "  cd soc-agent-system/backend"
    echo "  source venv/bin/activate"
    echo "  PYTHONPATH=src uvicorn main:app --host 0.0.0.0 --port 8000"
    echo ""
    exit 1
fi

echo ""
echo -e "${CYAN}Deployment Configuration:${NC}"
echo -e "  Type: ${DEPLOYMENT_TYPE}"
echo -e "  Backend API: ${BACKEND_URL}"
echo -e "  Frontend UI: ${FRONTEND_URL}"
echo ""

# Check if virtual environment is activated (only for local deployment)
if [[ "$DEPLOYMENT_TYPE" == "local" ]] && [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating...${NC}"
    source venv/bin/activate
fi

echo ""
echo -e "${BLUE}[2/6] Checking current threat count...${NC}"
BEFORE_COUNT=$(curl -s "${BACKEND_URL}/api/threats" | jq 'length' 2>/dev/null || echo "0")
echo -e "${CYAN}Current threats in feed: ${BEFORE_COUNT}${NC}"

echo ""
echo "================================================================================"
echo -e "${YELLOW}🎭 ACT 1: THE BYPASS (Detector Disabled)${NC}"
echo "================================================================================"
echo ""
echo "Scenario: Attacker injects 18 fabricated analyst notes"
echo "Expected: Attack bypasses detection, threat appears as 'benign'"
echo ""
read -p "Press Enter to trigger ACT 1..."
echo ""

# Create a Python script to inject the attack via API
cat > /tmp/inject_note_poisoning_act1.py << 'PYTHON_SCRIPT'
import asyncio
import sys
sys.path.insert(0, 'src')

from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType
from agents.coordinator import CoordinatorAgent
import httpx

async def main():
    # Red Team injects attack
    injector = AdversarialInjector()
    attack_data = injector.inject_historical_note_poisoning_attack(
        customer_name="DEMO_NotePoisonCorp_ACT1",
        threat_type=ThreatType.ANOMALY_DETECTION
    )
    
    signal = attack_data["signal"]
    historical_context = attack_data["historical_context"]
    
    print(f"✓ Attack signal created:")
    print(f"  - Customer: {signal.customer_name}")
    print(f"  - Threat type: {signal.threat_type.value}")
    print(f"  - Poisoned notes: 18/20")
    print()
    
    # Analyze with detector DISABLED
    coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=False)
    analysis = await coordinator.analyze_threat(
        signal,
        historical_context_override=historical_context
    )
    
    # Save to threat store via API
    async with httpx.AsyncClient() as client:
        # We need to manually save since we're bypassing the API
        # Instead, let's just print the result
        print(f"✓ Analysis complete:")
        print(f"  - Severity: {analysis.severity.value}")
        print(f"  - FP Score: {analysis.false_positive_score.score:.2f}")
        print(f"  - Adversarial detected: {analysis.adversarial_detection.manipulation_detected}")
        print(f"  - Requires review: {analysis.requires_human_review}")
        
        if not analysis.adversarial_detection.manipulation_detected:
            print()
            print("🚨 ATTACK BYPASSED DETECTION (as expected with detector disabled)")
        
        # Save via internal store
        from store import create_store
        import os

        # Use environment variable or default
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        store = await create_store(redis_url)
        await store.save_threat(analysis)
        print(f"  - Saved to threat store with ID: {analysis.id}")

asyncio.run(main())
PYTHON_SCRIPT

echo -e "${CYAN}Injecting ACT 1 attack...${NC}"
PYTHONPATH=.:src python /tmp/inject_note_poisoning_act1.py

echo ""
echo -e "${GREEN}✅ ACT 1 Complete${NC}"
echo ""
echo "Check the UX at ${FRONTEND_URL} to see the threat"
echo "Customer name: DEMO_NotePoisonCorp_ACT1"
echo ""
read -p "Press Enter to continue to ACT 2..."

echo ""
echo "================================================================================"
echo -e "${YELLOW}🎭 ACT 2: THE CATCH (Detector Enabled)${NC}"
echo "================================================================================"
echo ""
echo "Scenario: Same attack, but adversarial detector is ENABLED"
echo "Expected: Attack is detected, threat flagged for human review"
echo ""
read -p "Press Enter to trigger ACT 2..."
echo ""

# Create ACT 2 script
cat > /tmp/inject_note_poisoning_act2.py << 'PYTHON_SCRIPT'
import asyncio
import sys
sys.path.insert(0, 'src')

from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType
from agents.coordinator import CoordinatorAgent

async def main():
    # Red Team injects same attack
    injector = AdversarialInjector()
    attack_data = injector.inject_historical_note_poisoning_attack(
        customer_name="DEMO_NotePoisonCorp_ACT2",
        threat_type=ThreatType.ANOMALY_DETECTION
    )

    signal = attack_data["signal"]
    historical_context = attack_data["historical_context"]

    print(f"✓ Attack signal created:")
    print(f"  - Customer: {signal.customer_name}")
    print(f"  - Threat type: {signal.threat_type.value}")
    print(f"  - Poisoned notes: 18/20")
    print()

    # Analyze with detector ENABLED
    coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=True)
    analysis = await coordinator.analyze_threat(
        signal,
        historical_context_override=historical_context
    )

    print(f"✓ Analysis complete:")
    print(f"  - Severity: {analysis.severity.value}")
    print(f"  - FP Score: {analysis.false_positive_score.score:.2f}")
    print(f"  - Adversarial detected: {analysis.adversarial_detection.manipulation_detected}")
    print(f"  - Requires review: {analysis.requires_human_review}")

    if analysis.adversarial_detection.manipulation_detected:
        print()
        print("🚨 ADVERSARIAL MANIPULATION DETECTED!")
        print(f"  - Attack vector: {analysis.adversarial_detection.attack_vector}")
        print(f"  - Risk score: {analysis.adversarial_detection.risk_score:.2f}")
        print(f"  - Explanation: {analysis.adversarial_detection.explanation}")

    # Save via internal store
    from store import create_store
    import os

    # Use environment variable or default
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    store = await create_store(redis_url)
    await store.save_threat(analysis)
    print(f"  - Saved to threat store with ID: {analysis.id}")

asyncio.run(main())
PYTHON_SCRIPT

echo -e "${CYAN}Injecting ACT 2 attack...${NC}"
PYTHONPATH=.:src python /tmp/inject_note_poisoning_act2.py

echo ""
echo -e "${GREEN}✅ ACT 2 Complete${NC}"
echo ""
echo "Check the UX at ${FRONTEND_URL} to see the threat flagged for review"
echo "Customer name: DEMO_NotePoisonCorp_ACT2"
echo ""
read -p "Press Enter to continue to BASELINE..."

echo ""
echo "================================================================================"
echo -e "${YELLOW}🎭 BASELINE: Clean Signal (No Attack)${NC}"
echo "================================================================================"
echo ""
echo "Scenario: Legitimate threat with authentic analyst notes"
echo "Expected: No false positives, normal processing"
echo ""
read -p "Press Enter to trigger BASELINE..."
echo ""

# Create BASELINE script
cat > /tmp/inject_note_poisoning_baseline.py << 'PYTHON_SCRIPT'
import asyncio
import sys
sys.path.insert(0, 'src')

from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType
from agents.coordinator import CoordinatorAgent

async def main():
    # Red Team creates clean signal
    injector = AdversarialInjector()
    attack_data = injector.inject_historical_note_poisoning_attack(
        customer_name="DEMO_CleanCorp_BASELINE",
        threat_type=ThreatType.ANOMALY_DETECTION,
        inject_attack=False  # No attack
    )

    signal = attack_data["signal"]
    historical_context = attack_data["historical_context"]

    print(f"✓ Clean signal created:")
    print(f"  - Customer: {signal.customer_name}")
    print(f"  - Threat type: {signal.threat_type.value}")
    print(f"  - Poisoned notes: 0/20 (all authentic)")
    print()

    # Analyze with detector ENABLED
    coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=True)
    analysis = await coordinator.analyze_threat(
        signal,
        historical_context_override=historical_context
    )

    print(f"✓ Analysis complete:")
    print(f"  - Severity: {analysis.severity.value}")
    print(f"  - FP Score: {analysis.false_positive_score.score:.2f}")
    print(f"  - Adversarial detected: {analysis.adversarial_detection.manipulation_detected}")
    print(f"  - Requires review: {analysis.requires_human_review}")

    if not analysis.adversarial_detection.manipulation_detected:
        print()
        print("✅ NO FALSE POSITIVES - Clean signal processed normally")

    # Save via internal store
    from store import create_store
    import os

    # Use environment variable or default
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    store = await create_store(redis_url)
    await store.save_threat(analysis)
    print(f"  - Saved to threat store with ID: {analysis.id}")

asyncio.run(main())
PYTHON_SCRIPT

echo -e "${CYAN}Injecting BASELINE signal...${NC}"
PYTHONPATH=.:src python /tmp/inject_note_poisoning_baseline.py

echo ""
echo -e "${GREEN}✅ BASELINE Complete${NC}"
echo ""

echo "================================================================================"
echo -e "${GREEN}🎉 LIVE DEMO COMPLETE!${NC}"
echo "================================================================================"
echo ""
echo -e "${BLUE}[6/6] Checking final threat count...${NC}"
AFTER_COUNT=$(curl -s "${BACKEND_URL}/api/threats" | jq 'length' 2>/dev/null || echo "0")
echo -e "${CYAN}Threats in feed: ${AFTER_COUNT} (added 3 new threats)${NC}"
echo ""
echo "📊 Summary:"
echo "  ✓ ACT 1: Attack bypassed (detector disabled) - DEMO_NotePoisonCorp_ACT1"
echo "  ✓ ACT 2: Attack detected (detector enabled) - DEMO_NotePoisonCorp_ACT2"
echo "  ✓ BASELINE: No false positives - DEMO_CleanCorp_BASELINE"
echo ""
echo "🌐 View in UX:"
echo "  → Open ${FRONTEND_URL}"
echo "  → Look for threats with customer names starting with 'DEMO_'"
echo "  → ACT 2 should show 'Requires Human Review' badge"
echo ""
echo "🔍 Key Logs to Show:"
if [[ "$DEPLOYMENT_TYPE" == "kind" ]]; then
    echo "  • View backend logs: kubectl logs -n $NAMESPACE -l app=soc-backend --tail=100"
    echo "  • ACT 1: No adversarial detection log"
    echo "  • ACT 2: '🚨 ADVERSARIAL MANIPULATION DETECTED' with attack_vector='historical_note_fabrication'"
    echo "  • BASELINE: No adversarial detection log"
else
    echo "  • ACT 1: No adversarial detection log"
    echo "  • ACT 2: '🚨 ADVERSARIAL MANIPULATION DETECTED' with attack_vector='historical_note_fabrication'"
    echo "  • BASELINE: No adversarial detection log"
fi
echo ""
echo "================================================================================"

# Cleanup
rm -f /tmp/inject_note_poisoning_act1.py
rm -f /tmp/inject_note_poisoning_act2.py
rm -f /tmp/inject_note_poisoning_baseline.py

# Kill port-forward if we started it
if [[ -n "$PF_PID" ]]; then
    echo ""
    echo -e "${YELLOW}Cleaning up port-forward (PID: $PF_PID)...${NC}"
    kill $PF_PID 2>/dev/null || true
fi

