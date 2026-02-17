"""Tests for FastAPI endpoints."""
import pytest
import sys
sys.path.insert(0, 'src')

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


def test_get_threats_with_data(test_client):
    """Test getting threats with data in store."""
    # Trigger a threat via the API to populate the store
    trigger_response = test_client.post("/api/threats/trigger", json={"threat_type": "bot_traffic"})
    assert trigger_response.status_code == 200

    # Now get threats
    response = test_client.get("/api/threats")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["signal"]["customer_name"] is not None


def test_get_threats_pagination(test_client):
    """Test threat pagination."""
    # Add multiple threats via API
    for i in range(5):
        trigger_response = test_client.post("/api/threats/trigger", json={"threat_type": "bot_traffic"})
        assert trigger_response.status_code == 200

    # Test limit
    response = test_client.get("/api/threats?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Test offset
    response = test_client.get("/api/threats?limit=2&offset=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_threat_by_id(test_client):
    """Test getting specific threat by ID."""
    # Trigger a threat via API
    trigger_response = test_client.post("/api/threats/trigger", json={"threat_type": "bot_traffic"})
    assert trigger_response.status_code == 200
    analysis_data = trigger_response.json()
    threat_id = analysis_data["id"]

    # Get the specific threat
    response = test_client.get(f"/api/threats/{threat_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == threat_id


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


def test_get_analytics_with_data(test_client):
    """Test analytics with data."""
    # Add threats via API
    for i in range(3):
        trigger_response = test_client.post("/api/threats/trigger", json={"threat_type": "bot_traffic"})
        assert trigger_response.status_code == 200

    response = test_client.get("/api/analytics")

    assert response.status_code == 200
    data = response.json()
    assert data["total_threats"] == 3
    assert data["customers_affected"] >= 1
    assert "threats_by_type" in data
    assert "threats_by_severity" in data

