"""Unit tests for Historical Note Poisoning detection.

Tests the _check_resolution_note_authenticity() method in AdversarialManipulationDetector.
"""
import pytest
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'tests')

from analyzers.adversarial_detector import AdversarialManipulationDetector
from models import ThreatSignal, ThreatType
from adversarial_mock_data.historical_notes import get_real_notes, get_poisoned_notes, get_mixed_notes


class TestHistoricalNotePoisoning:
    """Unit tests for note authenticity detection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = AdversarialManipulationDetector(use_mock=True)
        self.signal = ThreatSignal(
            customer_name="UnitTestCorp",
            threat_type=ThreatType.ANOMALY_DETECTION,
            metadata={"source_ip": "192.168.1.1"}
        )
    
    def test_poisoned_notes_detected(self):
        """Test that poisoned notes are detected as fabricated."""
        poisoned = get_poisoned_notes()
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        
        assert anomaly is not None, "Should detect fabrication"
        assert anomaly.type == "historical_note_fabrication"
        assert anomaly.severity == "critical"
        assert anomaly.confidence > 0.9, f"Confidence should be high: {anomaly.confidence}"
        assert len(anomaly.indicators) > 0, "Should have fabrication indicators"
        assert anomaly.metadata is not None, "Should have metadata"
        assert "suspicious_patterns" in anomaly.metadata
        print(f"✅ Detected poisoned notes with confidence: {anomaly.confidence:.2f}")
    
    def test_real_notes_below_threshold(self):
        """Test that real notes (only 4) are skipped due to sample size."""
        real = get_real_notes()

        # Real notes only has 4 items, which is below the threshold of 5
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, real
        )

        # Should be None because sample size < 5
        assert anomaly is None, "Should skip sample < 5"
        print("✅ Real notes (4 items) correctly skipped due to sample size")
    
    def test_small_sample_size_skipped(self):
        """Test that samples < 5 notes are skipped."""
        small_sample = get_poisoned_notes()[:4]  # Only 4 notes
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, small_sample
        )
        
        assert anomaly is None, "Should skip small samples"
        print("✅ Small sample size correctly skipped")
    
    def test_minimum_sample_size_processed(self):
        """Test that exactly 5 notes are processed."""
        min_sample = get_poisoned_notes()[:5]  # Exactly 5 notes
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, min_sample
        )
        
        assert anomaly is not None, "Should process minimum sample size"
        print("✅ Minimum sample size (5) correctly processed")
    
    def test_mock_mode_deterministic(self):
        """Test that mock mode returns consistent results."""
        poisoned = get_poisoned_notes()
        
        # Run twice
        anomaly1 = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        anomaly2 = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        
        assert anomaly1 is not None and anomaly2 is not None
        assert anomaly1.confidence == anomaly2.confidence, "Should be deterministic"
        assert anomaly1.type == anomaly2.type
        assert len(anomaly1.indicators) == len(anomaly2.indicators)
        print("✅ Mock mode is deterministic")
    
    def test_anomaly_structure(self):
        """Test that anomaly has correct structure."""
        poisoned = get_poisoned_notes()
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        
        assert anomaly is not None
        assert hasattr(anomaly, 'type')
        assert hasattr(anomaly, 'severity')
        assert hasattr(anomaly, 'description')
        assert hasattr(anomaly, 'confidence')
        assert hasattr(anomaly, 'indicators')
        assert hasattr(anomaly, 'metadata')
        
        assert isinstance(anomaly.indicators, list)
        assert isinstance(anomaly.metadata, dict)
        assert "suspicious_patterns" in anomaly.metadata
        assert "note_count" in anomaly.metadata
        assert anomaly.metadata["note_count"] == len(poisoned)
        print("✅ Anomaly structure is correct")
    
    def test_fabrication_indicators_present(self):
        """Test that fabrication indicators are populated."""
        poisoned = get_poisoned_notes()
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        
        assert anomaly is not None
        assert len(anomaly.indicators) > 0, "Should have indicators"
        
        # Check that indicators are meaningful strings
        for indicator in anomaly.indicators:
            assert isinstance(indicator, str)
            assert len(indicator) > 10, "Indicators should be descriptive"
        
        print(f"✅ Found {len(anomaly.indicators)} fabrication indicators")
    
    def test_suspicious_patterns_present(self):
        """Test that suspicious patterns are identified."""
        poisoned = get_poisoned_notes()
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, poisoned
        )
        
        assert anomaly is not None
        assert "suspicious_patterns" in anomaly.metadata
        patterns = anomaly.metadata["suspicious_patterns"]
        assert isinstance(patterns, list)
        assert len(patterns) > 0, "Should have suspicious patterns"
        
        print(f"✅ Found {len(patterns)} suspicious patterns")
    
    def test_mixed_notes_detected(self):
        """Test that mixed real/poisoned notes are still detected."""
        mixed = get_mixed_notes(real_count=2, poisoned_count=10)
        
        anomaly = self.detector._check_resolution_note_authenticity(
            self.signal, mixed
        )
        
        # Mock mode will detect
        assert anomaly is not None
        print("✅ Mixed notes processed correctly")

