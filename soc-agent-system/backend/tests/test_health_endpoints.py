"""Tests for health check endpoints (/health and /ready)."""
import pytest
import time
from fastapi.testclient import TestClient

from main import app
from health import set_coordinator, _startup_time, get_uptime_seconds
from agents.coordinator import create_coordinator


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint_returns_200(test_client):
    """Test that /health always returns 200 if process is running."""
    response = test_client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["version"] == "2.0"
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0


def test_health_endpoint_is_fast(test_client):
    """Test that /health responds quickly (<50ms)."""
    start = time.time()
    response = test_client.get("/health")
    elapsed_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert elapsed_ms < 50, f"Health check took {elapsed_ms}ms, should be <50ms"


def test_health_uptime_increases(test_client):
    """Test that uptime increases over time."""
    response1 = test_client.get("/health")
    uptime1 = response1.json()["uptime_seconds"]
    
    time.sleep(0.1)  # Wait 100ms
    
    response2 = test_client.get("/health")
    uptime2 = response2.json()["uptime_seconds"]
    
    assert uptime2 > uptime1, "Uptime should increase over time"


def test_ready_endpoint_returns_200_when_coordinator_set(test_client):
    """Test that /ready returns 200 when coordinator is initialized."""
    # Initialize a mock coordinator
    coordinator = create_coordinator(use_mock=True)
    set_coordinator(coordinator)
    
    response = test_client.get("/ready")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "ready"
    assert "components" in data
    
    # Check coordinator
    assert data["components"]["coordinator"] is True
    
    # Check all 5 agents
    assert data["components"]["agents"]["historical"] is True
    assert data["components"]["agents"]["config"] is True
    assert data["components"]["agents"]["devops"] is True
    assert data["components"]["agents"]["context"] is True
    assert data["components"]["agents"]["priority"] is True
    
    # Check all 3 analyzers
    assert data["components"]["analyzers"]["fp"] is True
    assert data["components"]["analyzers"]["response"] is True
    assert data["components"]["analyzers"]["timeline"] is True


def test_ready_endpoint_completes_quickly(test_client):
    """Test that /ready completes within 100ms."""
    # Initialize coordinator
    coordinator = create_coordinator(use_mock=True)
    set_coordinator(coordinator)
    
    start = time.time()
    response = test_client.get("/ready")
    elapsed_ms = (time.time() - start) * 1000
    
    assert response.status_code == 200
    assert elapsed_ms < 100, f"Readiness check took {elapsed_ms}ms, should be <100ms"


def test_ready_endpoint_structure(test_client):
    """Test that /ready response has correct structure."""
    coordinator = create_coordinator(use_mock=True)
    set_coordinator(coordinator)
    
    response = test_client.get("/ready")
    data = response.json()
    
    # Verify structure
    assert "status" in data
    assert "components" in data
    assert "coordinator" in data["components"]
    assert "agents" in data["components"]
    assert "analyzers" in data["components"]
    
    # Verify agents structure
    expected_agents = ["historical", "config", "devops", "context", "priority"]
    for agent in expected_agents:
        assert agent in data["components"]["agents"]
        assert isinstance(data["components"]["agents"][agent], bool)
    
    # Verify analyzers structure
    expected_analyzers = ["fp", "response", "timeline"]
    for analyzer in expected_analyzers:
        assert analyzer in data["components"]["analyzers"]
        assert isinstance(data["components"]["analyzers"][analyzer], bool)


def test_health_and_ready_do_not_break_existing_endpoints(test_client):
    """Test that health endpoints don't interfere with existing API."""
    # Initialize coordinator for /ready
    coordinator = create_coordinator(use_mock=True)
    set_coordinator(coordinator)
    
    # Test health endpoints
    health_response = test_client.get("/health")
    assert health_response.status_code == 200
    
    ready_response = test_client.get("/ready")
    assert ready_response.status_code == 200
    
    # Test existing endpoints still work
    root_response = test_client.get("/")
    assert root_response.status_code == 200
    
    threats_response = test_client.get("/api/threats")
    assert threats_response.status_code == 200
    
    analytics_response = test_client.get("/api/analytics")
    assert analytics_response.status_code == 200


def test_root_endpoint_updated(test_client):
    """Test that root endpoint now includes health endpoint info."""
    response = test_client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["service"] == "SOC Agent System"
    assert data["version"] == "2.0"
    assert "endpoints" in data
    assert data["endpoints"]["health"] == "/health"
    assert data["endpoints"]["ready"] == "/ready"
    assert data["endpoints"]["metrics"] == "/metrics"

