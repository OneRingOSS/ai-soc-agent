#!/bin/bash
# Demo script for Phase 3: Coordinated Attack & Ensemble Validation Detection
# This script demonstrates advanced multi-agent adversarial detection

set -e

echo "================================================================================"
echo "🎯 RED TEAM MODE: Phase 3 - Coordinated Attack Detection Demo"
echo "================================================================================"
echo ""
echo "This demo shows how the AI SOC Agent system detects:"
echo "  1. Coordinated attacks (simultaneous Context + Historical manipulation)"
echo "  2. Ensemble validation (Priority Agent as outlier vs consensus)"
echo ""
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating...${NC}"
    source venv/bin/activate
fi

echo -e "${BLUE}📋 Phase 3: Coordinated Attack & Ensemble Validation - Live Demo${NC}"
echo ""
echo "System Components:"
echo "  ✓ Enhanced Adversarial Detector (src/analyzers/adversarial_detector.py)"
echo "  ✓ Coordinated Attack Detection (_check_coordinated_attack)"
echo "  ✓ Ensemble Validation (_check_priority_agent_outlier)"
echo "  ✓ Red Team Injector (src/red_team/adversarial_injector.py)"
echo ""

echo "================================================================================"
echo -e "${CYAN}🔍 Live Demo Scenarios${NC}"
echo "================================================================================"
echo ""
echo "Scenario 1: Coordinated Multi-Agent Attack"
echo "  → Geo-IP mismatch + Attack tool User-Agent (combined manipulation)"
echo "  → System detects coordinated manipulation pattern"
echo "  → Risk score elevated due to multi-vector attack"
echo ""
echo "Scenario 2: Multi-Anomaly Detection (Including High Volume)"
echo "  → Geo-IP mismatch + Attack tool UA + High request volume (3000 requests)"
echo "  → System aggregates all anomalies into comprehensive risk assessment"
echo "  → Demonstrates detection of high volume attacks (>1000 threshold)"
echo ""
echo "Scenario 3: Clean Signal Validation"
echo "  → Legitimate traffic with no manipulation"
echo "  → Validates no false positives on clean signals"
echo ""
echo "Note: Unit tests for ensemble validation are part of CI/CD pipeline."
echo "      Run 'pytest tests/test_adversarial_detector_coordinated.py' for full suite."
echo ""

echo "================================================================================"
echo -e "${BLUE}🎯 Live Demo: End-to-End Attack Detection${NC}"
echo "================================================================================"
echo ""

echo -e "${YELLOW}Scenario 1: Coordinated Multi-Agent Attack${NC}"
echo "Attack: Geo-IP mismatch + Attack tool User-Agent (combined)"
pytest tests/test_e2e_coordinated_attack.py::TestE2ECoordinatedAttack::test_coordinated_context_historical_attack_detected -v -s --tb=short
echo ""

echo -e "${YELLOW}Scenario 2: Multi-Anomaly Detection (Geo-IP + Attack Tool + HIGH VOLUME)${NC}"
echo "Attack: Private IP + Public location + Attack tool UA + 3000 requests"
echo "Note: This demonstrates HIGH REQUEST VOLUME detection (>1000 threshold)"
pytest tests/test_e2e_coordinated_attack.py::TestE2ECoordinatedAttack::test_multi_anomaly_attack_detected_e2e -v -s --tb=short
echo ""

echo -e "${YELLOW}Scenario 3: Clean Signal Validation (No False Positives)${NC}"
echo "Attack: None (legitimate traffic)"
pytest tests/test_e2e_coordinated_attack.py::TestE2ECoordinatedAttack::test_no_false_positive_clean_signal_e2e -v -s --tb=short
echo ""

echo "================================================================================"
echo -e "${GREEN}✅ Phase 3 Live Demo Complete!${NC}"
echo "================================================================================"
echo ""
echo "What You Just Saw (E2E Validation):"
echo "  ✓ Coordinated multi-agent attack detected (Geo-IP + Attack tool UA)"
echo "  ✓ Multi-anomaly detection including HIGH VOLUME (3000 requests > 1000 threshold)"
echo "  ✓ Clean signal validation (no false positives)"
echo "  ✓ Full pipeline: Signal → Coordinator → Detection → Risk Scoring"
echo ""
echo "Attack Vectors Demonstrated (E2E):"
echo "  1. Geo-IP mismatch (Private IP + Public location)"
echo "  2. Attack tool User-Agent (nikto, sqlmap, etc.)"
echo "  3. High request volume (3000 requests, threshold: 1000)"
echo "  4. Multi-anomaly aggregation (all of the above combined)"
echo ""
echo "Additional Capabilities (Tested in CI/CD):"
echo "  • Ensemble validation (Priority Agent outlier detection)"
echo "  • Coordinated attack detection (2+ agents threshold)"
echo "  • Context-Priority contradictions"
echo ""
echo "Key Metrics:"
echo "  → High Volume Threshold: >1000 requests"
echo "  → MIN_AGENTS_FOR_CONSENSUS: 3"
echo "  → COORDINATED_ATTACK_THRESHOLD: 2"
echo "  → Risk Score Range: 0.0 - 1.0"
echo ""
echo "Evolution from Previous Phases:"
echo "  Phase 1: Single agent (Context) manipulation detection"
echo "  Phase 2: Single agent (Historical) manipulation detection"
echo "  Phase 3: Multi-agent coordination + Ensemble validation ✨"
echo ""
echo "For Full Test Suite (Including Unit Tests):"
echo "  → pytest tests/test_adversarial_detector_coordinated.py -v"
echo "  → pytest tests/test_e2e_coordinated_attack.py -v"
echo ""
echo "================================================================================"

