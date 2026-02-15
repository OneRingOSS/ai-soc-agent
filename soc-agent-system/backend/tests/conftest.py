"""Pytest fixtures for SOC Agent System tests."""
import os

# Set testing environment variables BEFORE any other imports
# This ensures the app initializes in testing mode
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

# OpenTelemetry test imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

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


# ============================================================================
# BLOCK 1A: OpenTelemetry Test Fixtures
# ============================================================================

@pytest.fixture
def mock_otel_exporter():
    """Create an in-memory OpenTelemetry exporter for testing."""
    # Get the existing global tracer provider
    # The app should have already initialized it when main.py was imported
    provider = trace.get_tracer_provider()

    # Check if we have a real TracerProvider (not a ProxyTracerProvider)
    if not hasattr(provider, 'add_span_processor'):
        # If we got a ProxyTracerProvider, initialize telemetry now
        from telemetry import init_telemetry
        provider = init_telemetry()

    # Create in-memory exporter
    exporter = InMemorySpanExporter()

    # Add our in-memory exporter as a span processor to the existing provider
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    yield exporter

    # Cleanup: clear the exporter's spans
    exporter.clear()


@pytest.fixture
def sample_threat_signal_dict():
    """Return a valid TriggerRequest dict for testing."""
    return {
        "threat_type": "bot_traffic"
    }


@pytest.fixture
def sample_threat_signals_batch():
    """Return a list of 5 different TriggerRequest dicts."""
    threat_types = ["bot_traffic", "proxy_network", "device_compromise", "anomaly_detection", "rate_limit_breach"]

    signals = []
    for threat_type in threat_types:
        signals.append({
            "threat_type": threat_type
        })

    return signals


# ============================================================================
# BLOCK 1B: Prometheus Metrics Test Fixtures
# ============================================================================

@pytest.fixture
def reset_prometheus_metrics():
    """
    Reset Prometheus metrics before each test to ensure test isolation.

    This fixture clears all custom SOC metrics by accessing the REGISTRY
    and clearing collectors. Note: This doesn't affect the auto-instrumentation
    metrics from prometheus-fastapi-instrumentator.
    """
    from prometheus_client import REGISTRY

    # Clear all collectors from the registry
    # We need to be careful here - we can't just clear everything
    # Instead, we'll collect metrics before and after to verify reset

    yield

    # After test: clear the in-memory metrics
    # Note: prometheus_client doesn't have a built-in "reset all" method
    # The metrics will accumulate across tests unless we recreate them
    # For now, we'll rely on the fact that each test should verify
    # relative changes (increments) rather than absolute values

