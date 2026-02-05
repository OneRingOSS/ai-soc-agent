"""Pytest fixtures for SOC Agent System tests."""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

# Import from src
import sys
sys.path.insert(0, 'src')

from main import app, threat_store, websocket_clients
from models import ThreatSignal, ThreatType, ThreatSeverity, AgentAnalysis
from threat_generator import ThreatGenerator
from mock_data import MockDataStore
from agents.coordinator import CoordinatorAgent


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def threat_generator_seeded():
    """Create a seeded threat generator for deterministic tests."""
    return ThreatGenerator(seed=42)


@pytest.fixture
def mock_data_store():
    """Create a mock data store."""
    return MockDataStore()


@pytest.fixture
def sample_threat_signal():
    """Create a sample threat signal for testing."""
    return ThreatSignal(
        id="test-signal-001",
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="Test Corp",
        timestamp=datetime.utcnow(),
        metadata={
            "source_ip": "192.168.1.100",
            "request_count": 1000,
            "detection_confidence": 0.95
        }
    )


@pytest.fixture
def sample_agent_analysis():
    """Create a sample agent analysis for testing."""
    return AgentAnalysis(
        agent_name="Test Agent",
        analysis="Test analysis result",
        confidence=0.85,
        key_findings=["Finding 1", "Finding 2"],
        recommendations=["Recommendation 1"],
        processing_time_ms=150
    )


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''
    {
        "analysis": "Mock LLM analysis",
        "confidence": 0.85,
        "key_findings": ["Mock finding 1", "Mock finding 2"],
        "recommendations": ["Mock recommendation 1"]
    }
    '''
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def coordinator_mock_mode():
    """Create a coordinator in mock mode."""
    return CoordinatorAgent(use_mock=True)


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def clear_threat_store():
    """Clear threat store before each test."""
    threat_store.clear()
    websocket_clients.clear()
    yield
    threat_store.clear()
    websocket_clients.clear()

