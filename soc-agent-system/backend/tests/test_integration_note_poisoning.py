"""Integration tests for Historical Note Poisoning detection.

Tests the full pipeline from coordinator to adversarial detector.
"""
import pytest
import sys
import asyncio
sys.path.insert(0, 'src')
sys.path.insert(0, 'tests')

from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector
from models import ThreatSignal, ThreatType
from adversarial_mock_data.historical_notes import get_poisoned_notes, get_real_notes


class TestNotePoisoningIntegration:
    """Integration tests for note poisoning detection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.injector = AdversarialInjector()
        self.coordinator_enabled = CoordinatorAgent(
            use_mock=True,
            adversarial_detector_enabled=True
        )
        self.coordinator_disabled = CoordinatorAgent(
            use_mock=True,
            adversarial_detector_enabled=False
        )
    
    @pytest.mark.asyncio
    async def test_full_pipeline_with_poisoned_notes(self):
        """Test full pipeline detects poisoned notes."""
        # Create attack
        attack = self.injector.inject_historical_note_poisoning_attack(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )

        # Analyze with detector enabled
        analysis = await self.coordinator_enabled.analyze_threat(
            attack["signal"],
            historical_context_override=attack["historical_context"]
        )
        
        # Verify detection
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is True
        assert analysis.adversarial_detection.attack_vector == "historical_note_fabrication"
        assert len(analysis.adversarial_detection.anomalies) > 0
        
        # Check anomaly details
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.type == "historical_note_fabrication"
        assert anomaly.severity == "critical"
        assert anomaly.confidence > 0.9
        
        print(f"✅ Full pipeline detected poisoned notes with confidence: {anomaly.confidence:.2f}")
    
    @pytest.mark.asyncio
    async def test_detector_disabled_bypasses_check(self):
        """Test that disabled detector bypasses the check."""
        # Create attack
        attack = self.injector.inject_historical_note_poisoning_attack(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )

        # Analyze with detector disabled
        analysis = await self.coordinator_disabled.analyze_threat(
            attack["signal"],
            historical_context_override=attack["historical_context"]
        )
        
        # Verify no detection
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is False
        assert len(analysis.adversarial_detection.anomalies) == 0
        
        print("✅ Disabled detector correctly bypassed check")
    
    @pytest.mark.asyncio
    async def test_small_sample_not_flagged(self):
        """Test that small samples are not flagged."""
        # Create signal
        signal = ThreatSignal(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION,
            metadata={"source_ip": "192.168.1.1"}
        )

        # Use only 4 poisoned notes (below threshold)
        small_context = {
            "similar_incidents": get_poisoned_notes()[:4]
        }

        # Analyze with detector enabled
        analysis = await self.coordinator_enabled.analyze_threat(
            signal,
            historical_context_override=small_context
        )
        
        # Should not detect due to small sample size
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is False
        
        print("✅ Small sample correctly not flagged")
    
    @pytest.mark.asyncio
    async def test_attack_metadata_preserved(self):
        """Test that attack metadata is preserved through pipeline."""
        # Create attack
        attack = self.injector.inject_historical_note_poisoning_attack(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )

        # Verify attack structure
        assert attack["attack_type"] == "historical_note_poisoning"
        assert attack["signal"] is not None
        assert attack["historical_context"] is not None
        assert len(attack["historical_context"]["similar_incidents"]) >= 5

        # Analyze
        analysis = await self.coordinator_enabled.analyze_threat(
            attack["signal"],
            historical_context_override=attack["historical_context"]
        )

        # Verify metadata in anomaly
        assert len(analysis.adversarial_detection.anomalies) > 0
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.metadata is not None
        assert "note_count" in anomaly.metadata
        assert anomaly.metadata["note_count"] == len(attack["historical_context"]["similar_incidents"])
        
        print("✅ Attack metadata preserved through pipeline")
    
    @pytest.mark.asyncio
    async def test_detection_result_structure(self):
        """Test that detection result has correct structure."""
        # Create attack
        attack = self.injector.inject_historical_note_poisoning_attack(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION
        )

        # Analyze
        analysis = await self.coordinator_enabled.analyze_threat(
            attack["signal"],
            historical_context_override=attack["historical_context"]
        )
        
        # Verify structure
        det = analysis.adversarial_detection
        assert hasattr(det, 'manipulation_detected')
        assert hasattr(det, 'confidence')
        assert hasattr(det, 'risk_score')
        assert hasattr(det, 'attack_vector')
        assert hasattr(det, 'anomalies')
        assert hasattr(det, 'contradictions')
        
        assert isinstance(det.anomalies, list)
        assert isinstance(det.contradictions, list)
        assert isinstance(det.confidence, float)
        assert isinstance(det.risk_score, float)
        
        print("✅ Detection result structure is correct")

