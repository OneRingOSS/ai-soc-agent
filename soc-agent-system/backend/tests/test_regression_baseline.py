"""
Regression tests to ensure Block 1A changes don't break existing functionality.

These tests verify that the core threat analysis pipeline still works correctly
after adding OpenTelemetry instrumentation.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ThreatType
from tests.helpers import trigger_threat


@pytest.mark.asyncio
async def test_existing_threat_pipeline_unchanged():
    """
    Verify that the threat analysis pipeline still returns all expected fields.

    This test ensures that adding OpenTelemetry doesn't break the core API response.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Trigger a threat analysis using the correct format
        trigger_request = {"threat_type": "bot_traffic"}
        response = await trigger_threat(client, trigger_request)

        # Verify response structure hasn't changed
        assert "id" in response
        assert "signal" in response
        assert "severity" in response
        assert "status" in response
        assert "agent_analyses" in response
        assert "false_positive_score" in response
        assert "response_plan" in response
        assert "investigation_timeline" in response
        assert "requires_human_review" in response
        assert "total_processing_time_ms" in response

        # Verify signal structure
        signal = response["signal"]
        assert "threat_type" in signal
        assert "customer_name" in signal
        assert signal["threat_type"] == "bot_traffic"
        
        # Verify agent analyses structure
        agent_analyses = response["agent_analyses"]
        expected_agents = ["historical", "config", "devops", "context", "priority"]
        for agent in expected_agents:
            assert agent in agent_analyses, f"Missing agent: {agent}"
            assert "analysis" in agent_analyses[agent]
            assert "confidence" in agent_analyses[agent]
            assert "key_findings" in agent_analyses[agent]
            assert "recommendations" in agent_analyses[agent]
        
        # Verify FP score structure
        fp_score = response["false_positive_score"]
        assert "score" in fp_score
        assert "confidence" in fp_score
        assert "recommendation" in fp_score

        # Verify response plan structure
        response_plan = response["response_plan"]
        assert "primary_action" in response_plan
        assert "secondary_actions" in response_plan
        assert "escalation_path" in response_plan

        # Verify timeline structure
        timeline = response["investigation_timeline"]
        assert "events" in timeline
        assert len(timeline["events"]) > 0


@pytest.mark.asyncio
async def test_all_threat_types_still_work():
    """
    Verify that all threat types can still be analyzed successfully.

    This test ensures OpenTelemetry instrumentation works for all threat types.
    """
    # Valid threat types from ThreatType enum
    threat_types = ["bot_traffic", "proxy_network", "device_compromise", "anomaly_detection", "rate_limit_breach", "geo_anomaly"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for threat_type in threat_types:
            # Trigger analysis for each threat type
            trigger_request = {"threat_type": threat_type}
            response = await trigger_threat(client, trigger_request)

            # Verify successful analysis
            assert "signal" in response
            assert response["signal"]["threat_type"] == threat_type
            assert response["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert response["total_processing_time_ms"] > 0


@pytest.mark.asyncio
async def test_get_threats_endpoint():
    """
    Verify that GET /api/threats endpoint still works correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get all threats
        response = await client.get("/api/threats")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_threat_by_id():
    """
    Verify that GET /api/threats/{id} endpoint still works correctly.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First, create a threat
        trigger_request = {"threat_type": "bot_traffic"}
        created = await trigger_threat(client, trigger_request)
        threat_id = created["id"]

        # Then retrieve it by ID
        response = await client.get(f"/api/threats/{threat_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == threat_id
        assert data["signal"]["threat_type"] == "bot_traffic"

