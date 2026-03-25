#!/bin/bash
# Demo script for Historical Note Poisoning adversarial attack detection
# This script demonstrates the "Two-Act" demo pattern

set -e

echo "================================================================================"
echo "🎭 RED TEAM MODE: Historical Note Poisoning Detection Demo"
echo "================================================================================"
echo ""
echo "This demo shows how the AI SOC Agent system detects fabricated analyst notes"
echo "designed to bias the system toward False Positive conclusions."
echo ""
echo "Why This Matters:"
echo "  • Traditional rule-based systems CANNOT detect this attack"
echo "  • Only LLM semantic reasoning can identify linguistic plausibility"
echo "  • Demonstrates core advantage of agentic SOC systems"
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

echo -e "${BLUE}📋 Historical Note Poisoning - Two-Act Demo${NC}"
echo ""
echo "System Components:"
echo "  ✓ Adversarial Detector (src/analyzers/adversarial_detector.py)"
echo "  ✓ Red Team Injector (src/red_team/adversarial_injector.py)"
echo "  ✓ Coordinator Integration (src/agents/coordinator.py)"
echo "  ✓ Mock Historical Notes (tests/adversarial_mock_data/historical_notes.py)"
echo ""
echo "Demo Pattern: Two-Act Structure"
echo "  Act 1: BYPASS - Show the vulnerability (detector disabled)"
echo "  Act 2: CATCH - Show the security control (detector enabled)"
echo ""
echo "Attack Characteristics:"
echo "  • 18 poisoned notes with identical templated structure"
echo "  • All resolved by 'admin_svc' service account (not human analysts)"
echo "  • Suspiciously fast resolution times (3 minutes each)"
echo "  • Generic team references (no specific names or tickets)"
echo "  • Temporal pattern: 1 note/day over 18 days"
echo ""

echo "================================================================================"
echo -e "${CYAN}🎬 ACT 1: THE BYPASS - Vulnerability Without Detection${NC}"
echo "================================================================================"
echo ""
echo -e "${YELLOW}Scenario: Adversarial detector is DISABLED${NC}"
echo "Expected: Poisoned notes successfully bias system toward False Positive"
echo ""
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_act1_bypass_with_detector_disabled -v -s --tb=short
echo ""

echo "================================================================================"
echo -e "${CYAN}🎬 ACT 2: THE CATCH - Security Control Enabled${NC}"
echo "================================================================================"
echo ""
echo -e "${YELLOW}Scenario: Adversarial detector is ENABLED${NC}"
echo "Expected: System detects 'historical_note_fabrication' attack vector"
echo ""
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_act2_catch_with_detector_enabled -v -s --tb=short
echo ""

echo "================================================================================"
echo -e "${CYAN}🎬 BASELINE: NO FALSE POSITIVES - Real Analyst Notes${NC}"
echo "================================================================================"
echo ""
echo -e "${YELLOW}Scenario: Authentic analyst notes (no attack)${NC}"
echo "Expected: No adversarial alerts on legitimate notes"
echo ""
pytest tests/test_e2e_note_poisoning.py::TestE2ENotePoisoning::test_e2e_no_false_positive_on_real_notes -v -s --tb=short
echo ""

echo "================================================================================"
echo -e "${GREEN}✅ Two-Act Demo Complete!${NC}"
echo "================================================================================"
echo ""
echo "What You Just Saw:"
echo "  ✓ ACT 1: Poisoned notes bypassed detection when detector disabled"
echo "  ✓ ACT 2: Same attack caught when detector enabled"
echo "  ✓ BASELINE: Real analyst notes did not trigger false alerts"
echo ""
echo "Attack Signatures Detected:"
echo "  • Templated note structure (identical patterns)"
echo "  • Service account authorship (admin_svc vs. human analysts)"
echo "  • Unrealistic resolution times (3 min for complex SQL injection)"
echo "  • Missing work item references (no JIRA tickets, no colleague names)"
echo "  • Temporal clustering (1 note/day pattern)"
echo ""
echo "Why Rules Can't Catch This:"
echo "  ✗ No single field is 'wrong' (all values are technically valid)"
echo "  ✗ Service accounts are legitimate (can't ban them)"
echo "  ✗ Fast resolutions happen (some issues are quick)"
echo "  ✓ Only LLM semantic reasoning detects 'linguistic implausibility'"
echo ""
echo "Detection Method:"
echo "  • LLM analyzes note authenticity using semantic reasoning"
echo "  • Compares poisoned notes vs. real analyst notes"
echo "  • Identifies fabrication signatures (templating, generic language)"
echo "  • Flags for manual review when threshold exceeded (5+ notes)"
echo ""
echo "Next Steps:"
echo "  → Review test results above for detailed detection logic"
echo "  → Check docs/specs/Adversarial Demo Spec  Historical Note Poisoning.md"
echo "  → Run full test suite: pytest tests/test_*note_poisoning*.py -v"
echo ""
echo "================================================================================"

