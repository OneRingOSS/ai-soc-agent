"""
Tests for Prometheus metrics integration (Block 1B).

These tests verify that:
1. The /metrics endpoint returns Prometheus text format
2. Custom SOC metrics are recorded correctly
3. Auto-instrumentation HTTP metrics work
4. Metrics don't interfere with OTel tracing or threat responses
"""
import pytest
from httpx import AsyncClient
from tests.helpers import get_metrics, trigger_threat


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(async_client: AsyncClient):
    """Test that /metrics endpoint returns valid Prometheus text format."""
    response = await async_client.get("/metrics")
    
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    
    metrics_text = response.text
    assert "# HELP" in metrics_text
    assert "# TYPE" in metrics_text
    assert "soc_threats_processed_total" in metrics_text
    assert "soc_agent_duration_seconds" in metrics_text
    assert "soc_fp_score" in metrics_text


@pytest.mark.asyncio
async def test_threat_counter_increments(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that soc_threats_processed_total counter increments when threats are processed."""
    # Get initial metrics
    initial_metrics = await get_metrics(async_client)
    
    # Count initial bot_traffic threats
    initial_count = 0
    for line in initial_metrics.split('\n'):
        if 'soc_threats_processed_total{' in line and 'bot_traffic' in line:
            parts = line.split()
            if len(parts) >= 2:
                initial_count = float(parts[-1])
                break
    
    # Trigger a threat
    await trigger_threat(async_client, sample_threat_signal_dict)
    
    # Get metrics after
    final_metrics = await get_metrics(async_client)
    
    # Count final bot_traffic threats
    final_count = 0
    for line in final_metrics.split('\n'):
        if 'soc_threats_processed_total{' in line and 'bot_traffic' in line:
            parts = line.split()
            if len(parts) >= 2:
                final_count = float(parts[-1])
                break
    
    # Assert counter increased by 1
    assert final_count == initial_count + 1


@pytest.mark.asyncio
async def test_threat_counter_labels_by_severity(async_client: AsyncClient, sample_threat_signals_batch):
    """Test that threat counter tracks different threat types with labels."""
    # Get initial count
    initial_metrics = await get_metrics(async_client)
    initial_total = 0
    for line in initial_metrics.split('\n'):
        if line.startswith('soc_threats_processed_total{'):
            parts = line.split()
            if len(parts) >= 2:
                initial_total += float(parts[-1])
    
    # Trigger 5 different threats
    for signal in sample_threat_signals_batch:
        await trigger_threat(async_client, signal)
    
    # Get final metrics
    final_metrics = await get_metrics(async_client)
    
    # Count total threats across all labels
    final_total = 0
    threat_types_seen = set()
    for line in final_metrics.split('\n'):
        if line.startswith('soc_threats_processed_total{'):
            parts = line.split()
            if len(parts) >= 2:
                final_total += float(parts[-1])
                # Extract threat_type from labels
                if 'threat_type=' in line:
                    threat_types_seen.add(line.split('threat_type="')[1].split('"')[0])
    
    # Assert we processed 5 more threats
    assert final_total == initial_total + 5
    # Assert we saw multiple threat types
    assert len(threat_types_seen) >= 5


@pytest.mark.asyncio
async def test_agent_duration_histogram_records(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that agent duration histogram records values for all agents."""
    # Trigger a threat
    await trigger_threat(async_client, sample_threat_signal_dict)
    
    # Get metrics
    metrics_text = await get_metrics(async_client)
    
    # Check that all 5 agents have recorded durations
    expected_agents = ["historical_agent", "config_agent", "devops_agent", "context_agent", "priority_agent"]
    
    for agent_name in expected_agents:
        # Look for histogram count line for this agent
        found = False
        for line in metrics_text.split('\n'):
            if f'soc_agent_duration_seconds_count{{agent_name="{agent_name}"}}' in line:
                parts = line.split()
                if len(parts) >= 2:
                    count = float(parts[-1])
                    assert count >= 1.0, f"Agent {agent_name} should have at least 1 observation"
                    found = True
                    break
        
        assert found, f"Agent {agent_name} duration metric not found"


@pytest.mark.asyncio
async def test_fp_score_histogram_records(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that FP score histogram records values in valid range."""
    # Trigger a threat
    await trigger_threat(async_client, sample_threat_signal_dict)
    
    # Get metrics
    metrics_text = await get_metrics(async_client)
    
    # Find FP score histogram count and sum
    fp_count = None
    fp_sum = None
    
    for line in metrics_text.split('\n'):
        if line.startswith('soc_fp_score_count '):
            parts = line.split()
            if len(parts) >= 2:
                fp_count = float(parts[-1])
        elif line.startswith('soc_fp_score_sum '):
            parts = line.split()
            if len(parts) >= 2:
                fp_sum = float(parts[-1])
    
    assert fp_count is not None and fp_count >= 1.0, "FP score should have at least 1 observation"
    assert fp_sum is not None, "FP score sum should exist"

    # Calculate average FP score
    avg_fp_score = fp_sum / fp_count
    assert 0.0 <= avg_fp_score <= 1.0, f"Average FP score {avg_fp_score} should be between 0 and 1"


@pytest.mark.asyncio
async def test_processing_duration_by_phase(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that processing duration histogram records phase timings."""
    # Trigger a threat
    await trigger_threat(async_client, sample_threat_signal_dict)

    # Get metrics
    metrics_text = await get_metrics(async_client)

    # Look for total phase duration
    total_count = None
    total_sum = None

    for line in metrics_text.split('\n'):
        if 'soc_threat_processing_duration_seconds_count{phase="total"}' in line:
            parts = line.split()
            if len(parts) >= 2:
                total_count = float(parts[-1])
        elif 'soc_threat_processing_duration_seconds_sum{phase="total"}' in line:
            parts = line.split()
            if len(parts) >= 2:
                total_sum = float(parts[-1])

    assert total_count is not None and total_count >= 1.0, "Total phase should have at least 1 observation"
    assert total_sum is not None and total_sum > 0.0, "Total processing duration should be > 0"


@pytest.mark.asyncio
async def test_websocket_gauge_tracks_connections(async_client: AsyncClient):
    """Test that WebSocket connection gauge is present."""
    # Get metrics
    metrics_text = await get_metrics(async_client)

    # Look for WebSocket gauge
    ws_connections = None
    for line in metrics_text.split('\n'):
        if line.startswith('soc_active_websocket_connections '):
            parts = line.split()
            if len(parts) >= 2:
                ws_connections = float(parts[-1])
                break

    assert ws_connections is not None, "WebSocket connections gauge should exist"
    assert ws_connections >= 0, "WebSocket connections should be >= 0"


@pytest.mark.asyncio
async def test_http_auto_metrics_from_instrumentator(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that HTTP auto-instrumentation metrics are recorded."""
    # Make some HTTP requests
    await async_client.get("/health")
    await trigger_threat(async_client, sample_threat_signal_dict)

    # Get metrics
    metrics_text = await get_metrics(async_client)

    # Check for auto-instrumentation metrics
    assert "http_requests_total" in metrics_text or "http_request_duration_seconds" in metrics_text, \
        "HTTP auto-instrumentation metrics should be present"

    # Check for specific endpoints
    assert "/health" in metrics_text or "/api/threats/trigger" in metrics_text, \
        "HTTP metrics should track specific endpoints"


@pytest.mark.asyncio
async def test_metrics_do_not_break_otel_tracing(
    async_client: AsyncClient,
    sample_threat_signal_dict,
    mock_otel_exporter
):
    """Test that Prometheus metrics don't interfere with OpenTelemetry tracing."""
    # Clear any existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response = await trigger_threat(async_client, sample_threat_signal_dict)

    # Verify OTel spans are still created
    from tests.helpers import wait_for_spans
    assert wait_for_spans(mock_otel_exporter, expected_count=9, timeout=5.0), \
        "Should have 9 OTel spans (1 parent + 5 agents + 3 analyzers)"

    # Verify Prometheus metrics are recorded
    metrics_text = await get_metrics(async_client)
    assert "soc_threats_processed_total" in metrics_text, "Prometheus metrics should be recorded"

    # Both systems should work independently
    spans = mock_otel_exporter.get_finished_spans()
    assert len(spans) >= 9, f"Expected at least 9 spans, got {len(spans)}"


@pytest.mark.asyncio
async def test_metrics_do_not_break_threat_response(async_client: AsyncClient, sample_threat_signal_dict):
    """Test that metrics recording doesn't modify threat response structure."""
    # Trigger a threat
    response = await trigger_threat(async_client, sample_threat_signal_dict)

    # Verify response structure matches expected baseline
    assert "id" in response, "Response should have 'id' field"
    assert "signal" in response, "Response should have 'signal' field"
    assert "severity" in response, "Response should have 'severity' field"
    assert "false_positive_score" in response, "Response should have 'false_positive_score' field"
    assert "agent_analyses" in response, "Response should have 'agent_analyses' field"
    assert "response_plan" in response, "Response should have 'response_plan' field"
    assert "investigation_timeline" in response, "Response should have 'investigation_timeline' field"

    # Verify agent analyses structure
    assert len(response["agent_analyses"]) == 5, "Should have 5 agent analyses"

    # Verify metrics are still recorded
    metrics_text = await get_metrics(async_client)
    assert "soc_threats_processed_total" in metrics_text, "Metrics should be recorded without breaking response"

