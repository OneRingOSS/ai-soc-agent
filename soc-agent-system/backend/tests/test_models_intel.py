"""
Unit tests for IntelMatch model and ThreatAnalysis intel_matches field.

Stage 1 Gate: These tests must pass before proceeding to Stage 2.
"""

import pytest
from datetime import datetime
from src.models import (
    IntelMatch,
    ThreatAnalysis,
    ThreatSignal,
    ThreatSeverity,
    ThreatStatus,
    ThreatType,
)


class TestIntelMatch:
    """Test IntelMatch model creation and validation."""

    def test_intel_match_creation_with_all_fields(self):
        """Test IntelMatch model creation with all fields."""
        match = IntelMatch(
            ioc_type="hash",
            ioc_value="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            source="virustotal",
            description="28/72 AV engines flagged as 'riskware.androidos_root'",
            date_added="2024-01-15T10:30:00Z",
            confidence=0.91,
            threat_actor="APT-C-23"
        )
        
        assert match.ioc_type == "hash"
        assert match.ioc_value.startswith("a1b2c3d4")
        assert match.source == "virustotal"
        assert "28/72" in match.description
        assert match.date_added == "2024-01-15T10:30:00Z"
        assert match.confidence == 0.91
        assert match.threat_actor == "APT-C-23"

    def test_intel_match_defaults(self):
        """Test IntelMatch default values."""
        match = IntelMatch(
            ioc_type="hash",
            ioc_value="test_hash",
            source="virustotal",
            description="test description"
        )
        
        assert match.date_added == ""
        assert match.confidence == 0.8
        assert match.threat_actor is None

    def test_intel_match_confidence_validation(self):
        """Test IntelMatch confidence must be between 0.0 and 1.0."""
        # Valid confidence
        match = IntelMatch(
            ioc_type="hash",
            ioc_value="test",
            source="virustotal",
            description="test",
            confidence=0.5
        )
        assert match.confidence == 0.5
        
        # Test boundary values
        match_min = IntelMatch(
            ioc_type="hash",
            ioc_value="test",
            source="virustotal",
            description="test",
            confidence=0.0
        )
        assert match_min.confidence == 0.0
        
        match_max = IntelMatch(
            ioc_type="hash",
            ioc_value="test",
            source="virustotal",
            description="test",
            confidence=1.0
        )
        assert match_max.confidence == 1.0

    def test_intel_match_serialization(self):
        """Test IntelMatch can be serialized to dict/JSON."""
        match = IntelMatch(
            ioc_type="hash",
            ioc_value="abc123",
            source="virustotal",
            description="Malicious",
            confidence=0.95
        )
        
        data = match.model_dump()
        
        assert data["ioc_type"] == "hash"
        assert data["ioc_value"] == "abc123"
        assert data["source"] == "virustotal"
        assert data["description"] == "Malicious"
        assert data["confidence"] == 0.95
        assert data["date_added"] == ""
        assert data["threat_actor"] is None


class TestThreatAnalysisIntelMatches:
    """Test ThreatAnalysis with intel_matches field."""

    def test_threat_analysis_with_intel_matches(self):
        """Test ThreatAnalysis with intel_matches field."""
        signal = ThreatSignal(
            id="test-signal-001",
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name="test_customer",
            timestamp=datetime.utcnow(),
            metadata={"package_name": "com.test.malware"}
        )
        
        intel_match = IntelMatch(
            ioc_type="hash",
            ioc_value="test_hash",
            source="virustotal",
            description="28/72 AV engines flagged",
            confidence=0.91
        )
        
        analysis = ThreatAnalysis(
            signal=signal,
            severity=ThreatSeverity.HIGH,
            executive_summary="Test threat detected",
            intel_matches=[intel_match],
            customer_narrative="A malicious package was detected",
            total_processing_time_ms=100
        )
        
        assert len(analysis.intel_matches) == 1
        assert analysis.intel_matches[0].ioc_type == "hash"
        assert analysis.intel_matches[0].confidence == 0.91

    def test_threat_analysis_empty_intel_matches(self):
        """Test ThreatAnalysis with empty intel_matches (backward compat)."""
        signal = ThreatSignal(
            id="test-signal-002",
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name="test_customer",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        analysis = ThreatAnalysis(
            signal=signal,
            severity=ThreatSeverity.MEDIUM,
            executive_summary="Test threat",
            customer_narrative="Test narrative",
            total_processing_time_ms=50
        )
        
        # Should default to empty list
        assert analysis.intel_matches == []
        assert isinstance(analysis.intel_matches, list)

    def test_threat_analysis_multiple_intel_matches(self):
        """Test ThreatAnalysis with multiple intel_matches."""
        signal = ThreatSignal(
            id="test-signal-003",
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name="test_customer",
            timestamp=datetime.utcnow(),
            metadata={"package_name": "com.test.malware"}
        )
        
        matches = [
            IntelMatch(
                ioc_type="hash",
                ioc_value="hash1",
                source="virustotal",
                description="VT match",
                confidence=0.9
            ),
            IntelMatch(
                ioc_type="ip",
                ioc_value="192.168.1.100",
                source="alienvault",
                description="Known C2 server",
                confidence=0.85
            )
        ]
        
        analysis = ThreatAnalysis(
            signal=signal,
            severity=ThreatSeverity.CRITICAL,
            executive_summary="Multiple IOCs detected",
            intel_matches=matches,
            customer_narrative="Multiple threat indicators found",
            total_processing_time_ms=150
        )
        
        assert len(analysis.intel_matches) == 2
        assert analysis.intel_matches[0].source == "virustotal"
        assert analysis.intel_matches[1].source == "alienvault"

    def test_threat_analysis_serialization_with_intel_matches(self):
        """Test ThreatAnalysis serialization includes intel_matches."""
        signal = ThreatSignal(
            id="test-signal-004",
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name="test_customer",
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        match = IntelMatch(
            ioc_type="hash",
            ioc_value="test",
            source="virustotal",
            description="test",
            confidence=0.8
        )
        
        analysis = ThreatAnalysis(
            signal=signal,
            severity=ThreatSeverity.HIGH,
            executive_summary="Test",
            intel_matches=[match],
            customer_narrative="Test",
            total_processing_time_ms=100
        )
        
        data = analysis.model_dump()
        
        assert "intel_matches" in data
        assert len(data["intel_matches"]) == 1
        assert data["intel_matches"][0]["ioc_type"] == "hash"

