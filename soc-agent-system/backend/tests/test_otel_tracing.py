"""
Block 1A Tests: OpenTelemetry Tracing

Tests to verify OpenTelemetry instrumentation is working correctly.
All tests use InMemorySpanExporter (no real OTel Collector needed).
"""
import pytest
from httpx import AsyncClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from telemetry import init_telemetry, get_tracer
from tests.helpers import trigger_threat, wait_for_spans


@pytest.mark.asyncio
async def test_telemetry_module_initializes():
    """Test 1: Verify telemetry module initializes correctly."""
    # Initialize telemetry
    provider = init_telemetry()

    # Verify it returns a TracerProvider
    assert provider is not None
    assert isinstance(provider, TracerProvider)

    # Verify the service name resource attribute
    resource = provider.resource
    assert resource.attributes.get("service.name") == "soc-agent-system"


@pytest.mark.asyncio
async def test_fastapi_auto_instrumentation(async_client: AsyncClient, mock_otel_exporter: InMemorySpanExporter):
    """Test 2: Verify FastAPI auto-instrumentation works."""
    # Clear any existing spans
    mock_otel_exporter.clear()

    # Send GET / request (health check endpoint)
    response = await async_client.get("/")
    assert response.status_code == 200

    # Wait for spans to be exported
    wait_for_spans(mock_otel_exporter, expected_count=1, timeout=2.0)

    # Get exported spans
    spans = mock_otel_exporter.get_finished_spans()
    assert len(spans) >= 1, f"Expected at least 1 span, got {len(spans)}"

    # Find the HTTP span
    http_span = None
    for span in spans:
        if span.attributes.get("http.method") == "GET":
            http_span = span
            break

    assert http_span is not None, f"No HTTP span found. Spans: {[s.name for s in spans]}"
    assert http_span.attributes.get("http.method") == "GET"
    # Note: The health endpoint is at "/" not "/health"
    assert "/" in (http_span.attributes.get("http.route", "") or http_span.attributes.get("http.target", ""))


@pytest.mark.asyncio
async def test_threat_analysis_creates_parent_span(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signal_dict
):
    """Test 3: Verify threat analysis creates a parent span with attributes."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response_data = await trigger_threat(async_client, sample_threat_signal_dict)
    assert "id" in response_data

    # Wait for spans (at least the parent span)
    wait_for_spans(mock_otel_exporter, expected_count=1, timeout=5.0)

    # Get all spans
    spans = mock_otel_exporter.get_finished_spans()

    # Find the "analyze_threat" parent span
    parent_span = None
    for span in spans:
        if span.name == "analyze_threat":
            parent_span = span
            break

    assert parent_span is not None, f"No 'analyze_threat' span found. Spans: {[s.name for s in spans]}"

    # Verify it has the expected attributes
    assert "threat.type" in parent_span.attributes, f"Missing threat.type. Attributes: {parent_span.attributes}"
    assert "customer.name" in parent_span.attributes, f"Missing customer.name. Attributes: {parent_span.attributes}"
    assert "source.ip" in parent_span.attributes, f"Missing source.ip. Attributes: {parent_span.attributes}"

    # Verify values match the input
    assert parent_span.attributes["threat.type"] == sample_threat_signal_dict["threat_type"]


@pytest.mark.asyncio
async def test_parallel_agent_spans_are_children(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signal_dict
):
    """Test 4: Verify all 5 agent spans are children of the parent span."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response_data = await trigger_threat(async_client, sample_threat_signal_dict)
    assert "id" in response_data

    # Wait for spans (1 parent + 5 agents = at least 6)
    wait_for_spans(mock_otel_exporter, expected_count=6, timeout=5.0)

    # Get all spans
    spans = mock_otel_exporter.get_finished_spans()

    # Find the parent span
    parent_span = None
    for span in spans:
        if span.name == "analyze_threat":
            parent_span = span
            break

    assert parent_span is not None, f"No 'analyze_threat' parent span found. Spans: {[s.name for s in spans]}"

    # Find all agent spans
    # Agent spans are named with "_agent" suffix (e.g., "historical_agent", "config_agent", etc.)
    expected_agents = ["historical_agent", "config_agent", "devops_agent", "context_agent", "priority_agent"]
    found_agents = []

    for span in spans:
        if span.name in expected_agents:
            found_agents.append(span.name)
            # Verify this span is a child of the parent
            assert span.parent is not None, f"Agent span '{span.name}' has no parent"
            assert span.parent.span_id == parent_span.context.span_id, \
                f"Agent span '{span.name}' parent mismatch"

    # Verify all 5 agents were found
    assert len(found_agents) == 5, \
        f"Expected 5 agent spans, found {len(found_agents)}: {found_agents}. All spans: {[s.name for s in spans]}"





@pytest.mark.asyncio
async def test_sequential_analyzer_spans_exist(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signal_dict
):
    """Test 5: Verify all 3 analyzer spans exist as children of parent."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response_data = await trigger_threat(async_client, sample_threat_signal_dict)
    assert "id" in response_data

    # Wait for spans (1 parent + 5 agents + 3 analyzers = at least 9)
    wait_for_spans(mock_otel_exporter, expected_count=9, timeout=5.0)

    # Get all spans
    spans = mock_otel_exporter.get_finished_spans()

    # Find the parent span
    parent_span = None
    for span in spans:
        if span.name == "analyze_threat":
            parent_span = span
            break

    assert parent_span is not None, f"No 'analyze_threat' parent span found"

    # Find analyzer spans
    expected_analyzers = ["fp_analyzer", "response_engine", "timeline_builder"]
    found_analyzers = []

    for span in spans:
        if span.name in expected_analyzers:
            found_analyzers.append(span.name)
            # Verify this span is a child of the parent
            assert span.parent is not None, f"Analyzer span '{span.name}' has no parent"
            assert span.parent.span_id == parent_span.context.span_id, \
                f"Analyzer span '{span.name}' parent mismatch"

    # Verify all 3 analyzers were found
    assert len(found_analyzers) == 3, \
        f"Expected 3 analyzer spans, found {len(found_analyzers)}: {found_analyzers}. All spans: {[s.name for s in spans]}"


@pytest.mark.asyncio
async def test_span_has_final_attributes(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signal_dict
):
    """Test 6: Verify parent span has final attributes set."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response_data = await trigger_threat(async_client, sample_threat_signal_dict)
    assert "id" in response_data

    # Wait for spans
    wait_for_spans(mock_otel_exporter, expected_count=1, timeout=5.0)

    # Get all spans
    spans = mock_otel_exporter.get_finished_spans()

    # Find the parent span
    parent_span = None
    for span in spans:
        if span.name == "analyze_threat":
            parent_span = span
            break

    assert parent_span is not None, f"No 'analyze_threat' parent span found"

    # Verify final attributes are set
    assert "threat.severity" in parent_span.attributes, \
        f"Missing threat.severity. Attributes: {parent_span.attributes}"
    assert "fp.score" in parent_span.attributes, \
        f"Missing fp.score. Attributes: {parent_span.attributes}"
    assert "requires_review" in parent_span.attributes, \
        f"Missing requires_review. Attributes: {parent_span.attributes}"

    # Verify fp.score is a float between 0 and 1
    fp_score = parent_span.attributes["fp.score"]
    assert isinstance(fp_score, (int, float)), f"fp.score should be numeric, got {type(fp_score)}"
    assert 0 <= fp_score <= 1, f"fp.score should be between 0 and 1, got {fp_score}"

    # Verify requires_review is a boolean
    requires_review = parent_span.attributes["requires_review"]
    assert isinstance(requires_review, bool), f"requires_review should be bool, got {type(requires_review)}"


@pytest.mark.asyncio
async def test_otel_does_not_break_threat_response(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signal_dict
):
    """Test 7: Verify OTel instrumentation doesn't alter API response structure."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger a threat
    response_data = await trigger_threat(async_client, sample_threat_signal_dict)

    # Verify response structure (same checks as regression test)
    assert "id" in response_data
    assert "signal" in response_data
    assert "severity" in response_data
    assert "status" in response_data
    assert "agent_analyses" in response_data
    assert "false_positive_score" in response_data
    assert "response_plan" in response_data
    assert "investigation_timeline" in response_data
    assert "requires_human_review" in response_data
    assert "total_processing_time_ms" in response_data

    # Verify signal structure
    signal = response_data["signal"]
    assert "threat_type" in signal
    assert "customer_name" in signal

    # Verify severity is valid
    assert response_data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@pytest.mark.asyncio
async def test_multiple_concurrent_threats_have_separate_traces(
    async_client: AsyncClient,
    mock_otel_exporter: InMemorySpanExporter,
    sample_threat_signals_batch
):
    """Test 8: Verify each threat gets its own trace_id (no context leaking)."""
    # Clear existing spans
    mock_otel_exporter.clear()

    # Trigger 3 threats sequentially
    for i in range(3):
        signal_dict = sample_threat_signals_batch[i]
        response_data = await trigger_threat(async_client, signal_dict)
        assert "id" in response_data

    # Wait for spans (at least 3 parent spans)
    wait_for_spans(mock_otel_exporter, expected_count=3, timeout=10.0)

    # Get all spans
    spans = mock_otel_exporter.get_finished_spans()

    # Find all "analyze_threat" parent spans
    parent_spans = [span for span in spans if span.name == "analyze_threat"]

    assert len(parent_spans) >= 3, \
        f"Expected at least 3 'analyze_threat' spans, found {len(parent_spans)}"

    # Collect all trace IDs
    trace_ids = [span.context.trace_id for span in parent_spans]

    # Verify each has a different trace_id
    unique_trace_ids = set(trace_ids)
    assert len(unique_trace_ids) == len(parent_spans), \
        f"Expected {len(parent_spans)} unique trace IDs, got {len(unique_trace_ids)}. " \
        f"Trace IDs: {trace_ids}"
