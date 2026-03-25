#!/bin/bash
# Demo script for Context Agent adversarial attack detection
# This script demonstrates the Red Team Mode capabilities

set -e

echo "================================================================================"
echo "🎯 RED TEAM MODE: Context Agent Adversarial Attack Detection Demo"
echo "================================================================================"
echo ""
echo "This demo shows how the AI SOC Agent system detects when the Context Agent"
echo "has been compromised and is providing misleading 'benign' classifications."
echo ""
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating...${NC}"
    source venv/bin/activate
fi

echo -e "${BLUE}📋 Phase 1: Context Agent Adversarial Detection - Live Demo${NC}"
echo ""
echo "System Components:"
echo "  ✓ Adversarial Detector (src/analyzers/adversarial_detector.py)"
echo "  ✓ Red Team Injector (src/red_team/adversarial_injector.py)"
echo "  ✓ Coordinator Integration (src/agents/coordinator.py)"
echo ""
echo "Demo Scenarios:"
echo "  1. Geo-IP Mismatch Attack (Private IP + Public Location)"
echo "  2. Attack Tool User-Agent Detection (sqlmap, nikto, etc.)"
echo ""
echo "Note: Unit tests are part of CI/CD pipeline, not live demos."
echo "      Run 'pytest tests/test_adversarial_*.py' separately for full test suite."
echo ""

echo "================================================================================"
echo -e "${BLUE}🎯 Live Demo: End-to-End Attack Detection${NC}"
echo "================================================================================"
echo ""

echo -e "${YELLOW}Scenario 1: Geo-IP Mismatch Attack${NC}"
echo "Attack: Private IP (192.168.1.100) claiming to be from public location"
pytest tests/test_e2e_context_attack.py::TestE2EContextAttack::test_e2e_geo_ip_mismatch_attack -v -s --tb=short
echo ""

echo -e "${YELLOW}Scenario 2: Attack Tool User-Agent Detection${NC}"
echo "Attack: Known attack tool (sqlmap) in User-Agent header"
pytest tests/test_e2e_context_attack.py::TestE2EContextAttack::test_e2e_attack_tool_user_agent -v -s --tb=short
echo ""

echo "================================================================================"
echo -e "${GREEN}✅ Live Demo Complete!${NC}"
echo "================================================================================"
echo ""
echo "What You Just Saw (E2E Validation):"
echo "  ✓ Geo-IP mismatch attack detected (Private IP + Public location)"
echo "  ✓ Attack tool User-Agent detected (sqlmap in headers)"
echo "  ✓ Full pipeline: Signal → Coordinator → Detection → Human Review Flag"
echo "  ✓ Real-world attack scenarios with actual risk scoring"
echo ""
echo "Attack Vectors Demonstrated (E2E):"
echo "  1. Geo-IP mismatches (private IP with public location)"
echo "  2. Attack tool User-Agents (sqlmap, nikto, etc.)"
echo ""
echo "Additional Capabilities (Tested in CI/CD):"
echo "  • Context-Priority contradictions"
echo "  • High request volume anomalies (>1000 requests)"
echo "  • Multi-anomaly aggregation"
echo ""
echo "Next Demos:"
echo "  → ./demo_coordinated_attack.sh - Phase 3 advanced scenarios"
echo ""
echo "For Full Test Suite:"
echo "  → pytest tests/test_adversarial_*.py -v"
echo ""
echo "================================================================================"

