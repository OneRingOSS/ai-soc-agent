"""End-to-End test for Context Agent adversarial attack detection.

This test demonstrates the full system flow:
1. Red Team injects a Context Agent attack
2. Coordinator processes the threat signal
3. Adversarial detector identifies the manipulation
4. System flags for human review
5. Full analysis is returned with detection details

This is the final validation (Gate 4) for Phase 1.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType


@pytest.mark.e2e
class TestE2EContextAttack:
    """End-to-end tests for Context Agent adversarial attacks."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.coordinator = CoordinatorAgent(use_mock=True)
        self.injector = AdversarialInjector()
    
    @pytest.mark.asyncio
    async def test_e2e_geo_ip_mismatch_attack(self):
        """E2E: Geo-IP mismatch attack is detected and flagged for review.
        
        Scenario:
        - Attacker sends malicious traffic from private IP (192.168.1.100)
        - Context Agent is compromised and reports public geo-location
        - Adversarial detector catches the inconsistency
        - System flags for human review
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Geo-IP Mismatch Attack Detection")
        print("="*80)
        
        # ARRANGE - Red Team injects attack
        print("\n📍 Step 1: Red Team injects Geo-IP mismatch attack...")
        signal = self.injector.inject_geo_ip_mismatch_attack(
            customer_name="E2E_TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )
        
        print(f"   ✓ Attack signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']} (Private)")
        print(f"     - Geo Location: {signal.metadata['geo_location']} (Public)")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        
        # ACT - Coordinator processes the threat
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        analysis = await self.coordinator.analyze_threat(signal)
        
        # ASSERT - Verify detection
        print("\n✅ Step 3: Verifying adversarial detection...")
        assert analysis.adversarial_detection is not None, "Adversarial detection result missing"
        assert analysis.adversarial_detection.manipulation_detected is True, "Manipulation not detected"
        
        print(f"   ✓ Manipulation detected: {analysis.adversarial_detection.manipulation_detected}")
        print(f"   ✓ Attack vector: {analysis.adversarial_detection.attack_vector}")
        print(f"   ✓ Risk score: {analysis.adversarial_detection.risk_score:.2f}")
        print(f"   ✓ Anomalies found: {len(analysis.adversarial_detection.anomalies)}")
        
        # ASSERT - Verify anomaly details
        assert len(analysis.adversarial_detection.anomalies) > 0, "No anomalies detected"
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.type == "geo_ip_mismatch", f"Expected 'geo_ip_mismatch', got '{anomaly.type}'"
        assert "Private IP" in anomaly.description
        
        print(f"\n   📋 Anomaly Details:")
        print(f"     - Type: {anomaly.type}")
        print(f"     - Severity: {anomaly.severity}")
        print(f"     - Description: {anomaly.description}")
        
        # ASSERT - Verify human review flag
        print("\n🚨 Step 4: Verifying human review flag...")
        assert analysis.requires_human_review is True, "Human review not required"
        assert analysis.review_reason is not None, "Review reason missing"
        assert "manipulation" in analysis.review_reason.lower(), "Review reason doesn't mention manipulation"
        
        print(f"   ✓ Requires human review: {analysis.requires_human_review}")
        print(f"   ✓ Review reason: {analysis.review_reason}")
        
        # ASSERT - Verify full analysis
        print("\n📊 Step 5: Verifying complete analysis...")
        assert analysis.status.value == "completed"
        assert analysis.severity is not None
        assert len(analysis.agent_analyses) == 5
        assert analysis.false_positive_score is not None
        assert analysis.response_plan is not None
        
        print(f"   ✓ Analysis status: {analysis.status.value}")
        print(f"   ✓ Severity: {analysis.severity.value}")
        print(f"   ✓ FP Score: {analysis.false_positive_score.score:.2f}")
        print(f"   ✓ Agents analyzed: {len(analysis.agent_analyses)}")
        
        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Geo-IP mismatch attack successfully detected!")
        print("="*80 + "\n")
    
    @pytest.mark.asyncio
    async def test_e2e_attack_tool_user_agent(self):
        """E2E: Attack tool User-Agent is detected and flagged.
        
        Scenario:
        - Attacker uses sqlmap to scan for vulnerabilities
        - Context Agent is compromised and reports benign activity
        - Adversarial detector catches the attack tool User-Agent
        - System flags for human review
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Attack Tool User-Agent Detection")
        print("="*80)
        
        # ARRANGE
        print("\n📍 Step 1: Red Team injects attack tool UA attack...")
        signal = self.injector.inject_attack_tool_ua_attack(
            customer_name="E2E_TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            attack_tool_index=0  # sqlmap
        )
        
        print(f"   ✓ Attack signal created:")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        
        # ACT
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        analysis = await self.coordinator.analyze_threat(signal)
        
        # ASSERT
        print("\n✅ Step 3: Verifying adversarial detection...")
        assert analysis.adversarial_detection.manipulation_detected is True
        assert len(analysis.adversarial_detection.anomalies) > 0

        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.type == "attack_tool_user_agent", f"Expected 'attack_tool_user_agent', got '{anomaly.type}'"
        assert "attack tool" in anomaly.description.lower()
        
        print(f"   ✓ Attack tool detected in User-Agent")
        print(f"   ✓ Anomaly: {anomaly.description}")
        print(f"   ✓ Requires review: {analysis.requires_human_review}")
        
        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Attack tool User-Agent successfully detected!")
        print("="*80 + "\n")

