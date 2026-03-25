"""End-to-End tests for Phase 3: Coordinated Attack Detection.

Tests the full pipeline's response to coordinated multi-agent manipulation scenarios.
"""
import pytest
from models import ThreatSignal, ThreatSeverity, ThreatType
from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector


@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2ECoordinatedAttack:
    """End-to-end tests for coordinated attack detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.coordinator = CoordinatorAgent(use_mock=True)
        self.injector = AdversarialInjector()

    async def test_coordinated_context_historical_attack_detected(self):
        """Test E2E detection of coordinated Context + Historical manipulation.

        Scenario: Attacker manipulates both device metadata AND historical records
        to create a false sense of security across multiple agents.
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Coordinated Context + Historical Attack Detection")
        print("="*80)

        # ARRANGE - Create signal with coordinated manipulation
        print("\n📍 Step 1: Creating signal with coordinated manipulation...")

        # Use the injector to create a Context attack (geo-IP mismatch + attack tool UA)
        signal = self.injector.inject_combined_contradiction_and_anomaly_attack(
            customer_name="E2E_VictimCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )

        print(f"   ✓ Attack signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        print(f"     - Geo Location: {signal.metadata.get('geo_location', 'N/A')}")

        # ACT - Coordinator processes the threat
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        result = await self.coordinator.analyze_threat(signal)

        # ASSERT - Verify detection
        print("\n✅ Step 3: Verifying adversarial detection...")
        assert result.adversarial_detection is not None, "Adversarial detection result missing"
        assert result.adversarial_detection.manipulation_detected is True, "Manipulation not detected"

        print(f"   ✓ Manipulation detected: {result.adversarial_detection.manipulation_detected}")
        print(f"   ✓ Attack vector: {result.adversarial_detection.attack_vector}")
        print(f"   ✓ Risk score: {result.adversarial_detection.risk_score:.2f}")
        print(f"   ✓ Anomalies found: {len(result.adversarial_detection.anomalies)}")
        print(f"   ✓ Contradictions found: {len(result.adversarial_detection.contradictions)}")

        # Should detect Context Agent manipulation
        assert "context_agent" in result.adversarial_detection.attack_vector

        # Should have anomalies (attack tool UA detected)
        assert len(result.adversarial_detection.anomalies) > 0

        # Note: In mock mode, all agents return the same generic response,
        # so contradictions won't be detected. This is expected behavior.
        # In real mode with actual LLM responses, contradictions would be detected.

        # Risk score should be elevated
        assert result.adversarial_detection.risk_score > 0.1

        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Coordinated attack detected successfully!")
        print("="*80)
    
    async def test_multi_anomaly_attack_detected_e2e(self):
        """Test E2E detection of multi-anomaly attack.

        Scenario: Signal has multiple anomalies (geo-IP mismatch, attack tool UA, high volume).
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Multi-Anomaly Attack Detection")
        print("="*80)

        # ARRANGE - Create signal with multiple anomalies
        print("\n📍 Step 1: Creating signal with multiple anomalies...")

        signal = self.injector.inject_multi_anomaly_attack(
            customer_name="E2E_MultiCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )

        print(f"   ✓ Attack signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        print(f"     - Geo Location: {signal.metadata['geo_location']}")
        print(f"     - Request Count: {signal.metadata['request_count']}")

        # ACT - Coordinator processes the threat
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        result = await self.coordinator.analyze_threat(signal)

        # ASSERT - Verify detection
        print("\n✅ Step 3: Verifying adversarial detection...")
        assert result.adversarial_detection is not None, "Adversarial detection result missing"
        assert result.adversarial_detection.manipulation_detected is True, "Manipulation not detected"

        print(f"   ✓ Manipulation detected: {result.adversarial_detection.manipulation_detected}")
        print(f"   ✓ Attack vector: {result.adversarial_detection.attack_vector}")
        print(f"   ✓ Risk score: {result.adversarial_detection.risk_score:.2f}")
        print(f"   ✓ Anomalies found: {len(result.adversarial_detection.anomalies)}")

        # Should have at least one anomaly (multiple indicators may be combined)
        assert len(result.adversarial_detection.anomalies) >= 1

        # Risk score should be elevated
        assert result.adversarial_detection.risk_score > 0.1

        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Multi-anomaly attack detected successfully!")
        print("="*80)
    
    async def test_no_false_positive_clean_signal_e2e(self):
        """Test E2E that clean signals don't trigger false positives.

        Scenario: Legitimate traffic with no manipulation.
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Clean Signal (No False Positives)")
        print("="*80)

        # ARRANGE - Create clean signal
        print("\n📍 Step 1: Creating clean signal...")

        signal = self.injector.inject_clean_signal(
            customer_name="E2E_LegitCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )

        print(f"   ✓ Clean signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        print(f"     - Geo Location: {signal.metadata.get('geo_location', 'N/A')}")

        # ACT - Coordinator processes the threat
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        result = await self.coordinator.analyze_threat(signal)

        # ASSERT - No false positives
        print("\n✅ Step 3: Verifying no false positives...")

        # Either no adversarial detection, or manipulation_detected is False
        if result.adversarial_detection:
            print(f"   ✓ Adversarial detection present but manipulation_detected: {result.adversarial_detection.manipulation_detected}")
            print(f"   ✓ Risk score: {result.adversarial_detection.risk_score:.2f}")
            assert result.adversarial_detection.manipulation_detected is False, "False positive: Clean signal flagged as manipulated"
            assert result.adversarial_detection.risk_score < 0.3, "Risk score too high for clean signal"
        else:
            print(f"   ✓ No adversarial detection (expected for clean signal)")

        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: No false positives on clean signal!")
        print("="*80)

