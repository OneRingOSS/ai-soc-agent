"""End-to-End test for Historical Note Poisoning adversarial attack detection.

This test demonstrates the full system flow for the "Two-Act Demo":
1. Act 1 (Bypass): Red Team injects poisoned notes, detector disabled → attack bypasses
2. Act 2 (Catch): Same attack, detector enabled → attack caught
3. No False Positive: Real analyst notes should not trigger detection

This validates the complete Historical Note Poisoning feature from injection to detection.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType


@pytest.mark.e2e
class TestE2ENotePoisoning:
    """End-to-end tests for Historical Note Poisoning adversarial attacks."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.injector = AdversarialInjector()
    
    @pytest.mark.asyncio
    async def test_e2e_act1_bypass_with_detector_disabled(self):
        """E2E Act 1: Poisoned notes bypass detection when detector is disabled.
        
        Scenario:
        - Attacker injects 18 fabricated resolution notes
        - Adversarial detector is DISABLED
        - Attack bypasses detection
        - System processes normally without flagging manipulation
        """
        print("\n" + "="*80)
        print("🎭 E2E ACT 1: BYPASS - Detector Disabled")
        print("="*80)
        
        # ARRANGE - Red Team injects attack
        print("\n📍 Step 1: Red Team injects poisoned notes...")
        attack_data = self.injector.inject_historical_note_poisoning_attack(
            customer_name="E2E_NotePoisonCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )
        signal = attack_data["signal"]
        historical_context = attack_data["historical_context"]
        
        print(f"   ✓ Attack signal created:")
        print(f"     - Threat type: {signal.threat_type.value}")
        print(f"     - Source IP: {signal.metadata.get('source_ip', 'N/A')}")
        print(f"\n   ✓ Poisoned historical context:")
        print(f"     - Similar incidents: {len(historical_context['similar_incidents'])}")
        poisoned_count = sum(1 for inc in historical_context['similar_incidents']
                            if hasattr(inc, 'resolved_by') and inc.resolved_by == 'admin_svc')
        print(f"     - Poisoned notes: {poisoned_count}/{len(historical_context['similar_incidents'])}")
        
        # ACT - Coordinator processes with detector DISABLED
        print("\n🔄 Step 2: Coordinator processes with detector DISABLED...")
        coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=False)
        analysis = await coordinator.analyze_threat(
            signal,
            historical_context_override=historical_context
        )
        
        # ASSERT - Verify attack bypassed
        print("\n✅ Step 3: Verifying attack bypassed detection...")
        assert analysis is not None, "Analysis result missing"
        assert analysis.status.value == "completed", "Analysis not completed"
        assert analysis.adversarial_detection is not None, "Detector result should exist"
        assert not analysis.adversarial_detection.manipulation_detected, "Detector disabled - should not detect"

        print(f"   ✓ Analysis status: {analysis.status.value}")
        print(f"   ✓ Adversarial detection: Disabled (no manipulation detected)")
        print(f"   ✓ Severity: {analysis.severity.value}")
        
        print("\n" + "="*80)
        print("✅ ACT 1 PASSED: Attack bypassed when detector disabled!")
        print("="*80 + "\n")
    
    @pytest.mark.asyncio
    async def test_e2e_act2_catch_with_detector_enabled(self):
        """E2E Act 2: Poisoned notes caught when detector is enabled.
        
        Scenario:
        - Same attack as Act 1
        - Adversarial detector is ENABLED
        - Attack is CAUGHT
        - System flags manipulation and recommends manual review
        """
        print("\n" + "="*80)
        print("🎭 E2E ACT 2: CATCH - Detector Enabled")
        print("="*80)
        
        # ARRANGE - Red Team injects same attack
        print("\n📍 Step 1: Red Team injects poisoned notes...")
        attack_data = self.injector.inject_historical_note_poisoning_attack(
            customer_name="E2E_NotePoisonCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )
        signal = attack_data["signal"]
        historical_context = attack_data["historical_context"]
        
        print(f"   ✓ Attack signal created (same as Act 1)")
        print(f"     - Similar incidents: {len(historical_context['similar_incidents'])}")
        
        # ACT - Coordinator processes with detector ENABLED
        print("\n🔄 Step 2: Coordinator processes with detector ENABLED...")
        coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=True)
        analysis = await coordinator.analyze_threat(
            signal,
            historical_context_override=historical_context
        )
        
        # ASSERT - Verify attack caught
        print("\n✅ Step 3: Verifying attack was CAUGHT...")
        assert analysis is not None, "Analysis result missing"
        assert analysis.status.value == "completed", "Analysis not completed"
        assert analysis.adversarial_detection is not None, "Adversarial detection missing"
        assert analysis.adversarial_detection.manipulation_detected, "Manipulation should be detected"
        
        print(f"   ✓ Analysis status: {analysis.status.value}")
        print(f"   ✓ Manipulation detected: {analysis.adversarial_detection.manipulation_detected}")
        print(f"   ✓ Attack vector: {analysis.adversarial_detection.attack_vector}")
        print(f"   ✓ Confidence: {analysis.adversarial_detection.confidence:.2f}")
        
        # ASSERT - Verify anomaly details
        assert len(analysis.adversarial_detection.anomalies) > 0, "Should have anomalies"
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.type == "historical_note_fabrication", "Should detect note fabrication"
        
        print(f"\n   ✓ Anomaly type: {anomaly.type}")
        print(f"   ✓ Anomaly description: {anomaly.description[:80]}...")
        
        print("\n" + "="*80)
        print("✅ ACT 2 PASSED: Attack caught when detector enabled!")
        print("="*80 + "\n")
    
    @pytest.mark.asyncio
    async def test_e2e_no_false_positive_on_real_notes(self):
        """E2E: Real analyst notes should NOT trigger false positive.
        
        Scenario:
        - No attack injected (clean historical data)
        - Adversarial detector is ENABLED
        - System should NOT flag manipulation
        - Validates detector doesn't create false positives
        """
        print("\n" + "="*80)
        print("🎭 E2E: NO FALSE POSITIVE - Real Analyst Notes")
        print("="*80)

        # ARRANGE - Create clean signal (no attack)
        print("\n📍 Step 1: Creating clean threat signal...")
        from models import ThreatSignal, HistoricalIncident, ThreatSeverity
        from datetime import datetime
        from tests.adversarial_mock_data.historical_notes import REAL_ANALYST_NOTES
        import uuid

        signal = ThreatSignal(
            id="e2e-clean-001",
            customer_name="E2E_CleanCorp",
            threat_type=ThreatType.ANOMALY_DETECTION,
            severity="medium",
            timestamp=datetime.utcnow(),
            metadata={
                "source_ip": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "request_path": "/api/users?id=1"
            }
        )

        # Create clean historical context with REAL analyst notes
        # Use only 4 notes (below the 5-note threshold for detection)

        clean_context = {
            "similar_incidents": [
                HistoricalIncident(
                    id=str(uuid.uuid4()),
                    customer_name="E2E_CleanCorp",
                    incident_id=note["incident_id"],
                    threat_type=ThreatType.ANOMALY_DETECTION,
                    severity=ThreatSeverity.MEDIUM,
                    resolution=note["resolution_note"],
                    resolved_by=note["analyst_id"],
                    resolved_as=note["resolved_as"],
                    resolution_time_minutes=note["resolution_time_minutes"],
                    timestamp=datetime.fromisoformat(note["timestamp"].replace('Z', '+00:00'))
                )
                for note in REAL_ANALYST_NOTES
            ]
        }

        print(f"   ✓ Clean signal created:")
        print(f"     - Threat type: {signal.threat_type.value}")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"\n   ✓ Clean historical context:")
        print(f"     - Similar incidents: {len(clean_context['similar_incidents'])}")
        print(f"     - All from real analysts (sarah.chen, james.okafor, etc.)")

        # ACT - Coordinator processes with detector ENABLED
        print("\n🔄 Step 2: Coordinator processes with detector ENABLED...")
        coordinator = CoordinatorAgent(use_mock=True, adversarial_detector_enabled=True)
        analysis = await coordinator.analyze_threat(
            signal,
            historical_context_override=clean_context
        )

        # ASSERT - Verify NO false positive
        print("\n✅ Step 3: Verifying NO false positive...")
        assert analysis is not None, "Analysis result missing"
        assert analysis.status.value == "completed", "Analysis not completed"

        # Note: With only 4 real notes, we're below the threshold of 5
        # So the check should be skipped, not flagged
        if analysis.adversarial_detection is not None:
            # If detection ran (shouldn't with <5 notes), verify no manipulation
            assert not analysis.adversarial_detection.manipulation_detected, \
                "Should NOT detect manipulation in real analyst notes"
            print(f"   ✓ Manipulation detected: False (correct)")
        else:
            print(f"   ✓ Detection skipped (below 5-note threshold)")

        print(f"   ✓ Analysis status: {analysis.status.value}")
        print(f"   ✓ Severity: {analysis.severity.value}")

        print("\n" + "="*80)
        print("✅ NO FALSE POSITIVE PASSED: Real notes not flagged!")
        print("="*80 + "\n")

