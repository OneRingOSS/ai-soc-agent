"""
Integration tests for OpenTelemetry tracing in the SOC Agent System.

These tests start the actual backend server and verify end-to-end tracing.
"""
import pytest
import asyncio
import httpx
import time
from typing import List
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_threat_analysis_pipeline_tracing(mock_otel_exporter: InMemorySpanExporter):
    """
    Integration test: Verify complete OpenTelemetry tracing for threat analysis pipeline.
    
    This test:
    1. Starts with a clean span exporter
    2. Triggers a threat analysis via POST /api/threats/trigger
    3. Verifies all expected spans are created:
       - 1 HTTP span (FastAPI auto-instrumentation)
       - 1 analyze_threat parent span
       - 5 agent child spans (historical, config, devops, context, priority)
       - 3 analyzer child spans (fp_analyzer, response_engine, timeline_builder)
    4. Verifies parent-child relationships
    5. Verifies span attributes
    
    Expected total: ~10 spans (1 HTTP + 1 parent + 5 agents + 3 analyzers)
    """
    # Clear any existing spans
    mock_otel_exporter.clear()
    
    # Make request to trigger threat analysis
    async with httpx.AsyncClient(base_url="http://test") as client:
        # Import app here to use the test client
        from main import app
        from httpx import ASGITransport
        
        async with httpx.AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as test_client:
            # Trigger a threat analysis
            response = await test_client.post(
                "/api/threats/trigger",
                json={"threat_type": "bot_traffic"}
            )
            
            # Verify the request succeeded
            assert response.status_code == 200, f"Request failed: {response.text}"
            threat_data = response.json()
            assert "id" in threat_data
            assert threat_data["signal"]["threat_type"] == "bot_traffic"
    
    # Wait a bit for spans to be processed
    await asyncio.sleep(0.5)
    
    # Get all spans
    spans: List[ReadableSpan] = mock_otel_exporter.get_finished_spans()
    
    # Print span summary for debugging
    print(f"\n📊 Total spans collected: {len(spans)}")
    print("Span names:")
    for span in spans:
        parent_info = f" (parent: {span.parent.span_id})" if span.parent else " (root)"
        print(f"  - {span.name}{parent_info}")
    
    # Verify we have the expected number of spans
    # Minimum: 1 parent + 5 agents + 3 analyzers = 9 spans
    # May have additional HTTP spans from FastAPI instrumentation
    assert len(spans) >= 9, f"Expected at least 9 spans, got {len(spans)}"
    
    # Find the parent span
    parent_span = None
    for span in spans:
        if span.name == "analyze_threat":
            parent_span = span
            break
    
    assert parent_span is not None, "No 'analyze_threat' parent span found"
    
    # Verify parent span attributes
    assert parent_span.attributes.get("threat.type") == "bot_traffic"
    assert "customer.name" in parent_span.attributes
    assert "source.ip" in parent_span.attributes
    
    # Find all agent spans
    expected_agents = ["historical_agent", "config_agent", "devops_agent", "context_agent", "priority_agent"]
    found_agents = []
    
    for span in spans:
        if span.name in expected_agents:
            found_agents.append(span.name)
            # Verify this span is a child of the parent
            assert span.parent is not None, f"Agent span '{span.name}' has no parent"
            assert span.parent.span_id == parent_span.context.span_id, \
                f"Agent span '{span.name}' is not a child of 'analyze_threat'"
    
    assert len(found_agents) == 5, \
        f"Expected 5 agent spans, found {len(found_agents)}: {found_agents}"
    
    # Find all analyzer spans
    expected_analyzers = ["fp_analyzer", "response_engine", "timeline_builder"]
    found_analyzers = []
    
    for span in spans:
        if span.name in expected_analyzers:
            found_analyzers.append(span.name)
            # Verify this span is a child of the parent
            assert span.parent is not None, f"Analyzer span '{span.name}' has no parent"
            assert span.parent.span_id == parent_span.context.span_id, \
                f"Analyzer span '{span.name}' is not a child of 'analyze_threat'"
    
    assert len(found_analyzers) == 3, \
        f"Expected 3 analyzer spans, found {len(found_analyzers)}: {found_analyzers}"
    
    # Verify final attributes on parent span (set after analysis completes)
    assert "threat.severity" in parent_span.attributes
    assert "fp.score" in parent_span.attributes
    assert "requires_review" in parent_span.attributes
    
    print("\n✅ Integration test passed: All 9 pipeline components traced correctly!")
    print(f"   - 1 parent span (analyze_threat)")
    print(f"   - 5 agent spans: {', '.join(found_agents)}")
    print(f"   - 3 analyzer spans: {', '.join(found_analyzers)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_tracing(mock_otel_exporter: InMemorySpanExporter):
    """
    Integration test: Verify health endpoint creates HTTP spans.
    
    This is a simpler test that just verifies FastAPI auto-instrumentation works.
    """
    # Clear any existing spans
    mock_otel_exporter.clear()
    
    # Make request to health endpoint
    from main import app
    from httpx import ASGITransport
    
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    # Wait for spans to be processed
    await asyncio.sleep(0.1)
    
    # Get spans
    spans = mock_otel_exporter.get_finished_spans()
    
    # Should have at least 1 HTTP span
    assert len(spans) >= 1, f"Expected at least 1 span, got {len(spans)}"
    
    # Find HTTP GET span
    http_span = None
    for span in spans:
        if span.attributes.get("http.method") == "GET":
            http_span = span
            break
    
    assert http_span is not None, "No HTTP GET span found"
    assert http_span.attributes.get("http.route") == "/"
    
    print("\n✅ Health endpoint tracing verified!")

