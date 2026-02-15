"""Tests for FastAPI endpoints."""
import pytest
import sys
sys.path.insert(0, 'src')

from main import threat_store
from models import ThreatAnalysis, ThreatType


def test_health_check(test_client):
    """Test root endpoint."""
    response = test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "SOC Agent System"
    assert data["version"] == "2.0"
    assert "timestamp" in data
    assert "endpoints" in data


def test_get_threats_empty(test_client):
    """Test getting threats when store is empty."""
    response = test_client.get("/api/threats")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_threats_with_data(test_client, sample_threat_signal, sample_agent_analysis):
    """Test getting threats with data in store."""
    # Add a threat to the store
    from models import ThreatAnalysis, ThreatSeverity
    
    analysis = ThreatAnalysis(
        signal=sample_threat_signal,
        severity=ThreatSeverity.MEDIUM,
        executive_summary="Test summary",
        mitre_tactics=[],
        mitre_techniques=[],
        customer_narrative="Test narrative",
        agent_analyses={"test": sample_agent_analysis},
        total_processing_time_ms=100,
        requires_human_review=False
    )
    threat_store.append(analysis)
    
    response = test_client.get("/api/threats")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["signal"]["customer_name"] == "Test Corp"


def test_get_threats_pagination(test_client, sample_threat_signal, sample_agent_analysis):
    """Test threat pagination."""
    from models import ThreatAnalysis, ThreatSeverity
    
    # Add multiple threats
    for i in range(5):
        analysis = ThreatAnalysis(
            signal=sample_threat_signal,
            severity=ThreatSeverity.MEDIUM,
            executive_summary=f"Test summary {i}",
            mitre_tactics=[],
            mitre_techniques=[],
            customer_narrative="Test narrative",
            agent_analyses={"test": sample_agent_analysis},
            total_processing_time_ms=100,
            requires_human_review=False
        )
        threat_store.append(analysis)
    
    # Test limit
    response = test_client.get("/api/threats?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Test offset
    response = test_client.get("/api/threats?limit=2&offset=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_threat_by_id(test_client, sample_threat_signal, sample_agent_analysis):
    """Test getting specific threat by ID."""
    from models import ThreatAnalysis, ThreatSeverity
    
    analysis = ThreatAnalysis(
        signal=sample_threat_signal,
        severity=ThreatSeverity.MEDIUM,
        executive_summary="Test summary",
        mitre_tactics=[],
        mitre_techniques=[],
        customer_narrative="Test narrative",
        agent_analyses={"test": sample_agent_analysis},
        total_processing_time_ms=100,
        requires_human_review=False
    )
    threat_store.append(analysis)
    
    response = test_client.get(f"/api/threats/{analysis.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis.id


def test_get_threat_not_found(test_client):
    """Test getting non-existent threat."""
    response = test_client.get("/api/threats/nonexistent-id")
    
    assert response.status_code == 404


def test_get_analytics_empty(test_client):
    """Test analytics with empty store."""
    response = test_client.get("/api/analytics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_threats"] == 0
    assert data["customers_affected"] == 0


def test_get_analytics_with_data(test_client, sample_threat_signal, sample_agent_analysis):
    """Test analytics with data."""
    from models import ThreatAnalysis, ThreatSeverity
    
    # Add threats
    for severity in [ThreatSeverity.LOW, ThreatSeverity.HIGH, ThreatSeverity.HIGH]:
        analysis = ThreatAnalysis(
            signal=sample_threat_signal,
            severity=severity,
            executive_summary="Test",
            mitre_tactics=[],
            mitre_techniques=[],
            customer_narrative="Test",
            agent_analyses={"test": sample_agent_analysis},
            total_processing_time_ms=100,
            requires_human_review=(severity == ThreatSeverity.HIGH)
        )
        threat_store.append(analysis)
    
    response = test_client.get("/api/analytics")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_threats"] == 3
    assert data["customers_affected"] >= 1
    assert data["threats_requiring_review"] == 2
    assert "threats_by_type" in data
    assert "threats_by_severity" in data

