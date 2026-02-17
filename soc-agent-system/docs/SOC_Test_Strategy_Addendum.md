# SOC Agent System — Test-Driven Build Strategy
## Addendum to Demo Enhancement Plan

**Purpose:** Ensure every block in the critical path has automated tests that validate correctness and prevent regressions. Each Augment Code prompt now includes a paired test prompt that runs BEFORE proceeding to the next block.

---

## Table of Contents

1. [Testing Philosophy](#1-testing-philosophy)
2. [Test Infrastructure Setup (Run First)](#2-test-infrastructure-setup-run-first)
3. [Block 1A Tests: OpenTelemetry Tracing](#3-block-1a-tests-opentelemetry-tracing)
4. [Block 1B Tests: Prometheus Metrics](#4-block-1b-tests-prometheus-metrics)
5. [Block 1C Tests: Structured JSON Logging](#5-block-1c-tests-structured-json-logging)
6. [Block 1D Tests: Health Check Endpoints](#6-block-1d-tests-health-check-endpoints)
7. [Block 1 Regression Gate](#7-block-1-regression-gate)
8. [Block 2 Tests: Docker Compose Integration](#8-block-2-tests-docker-compose-integration)
9. [Block 3 Tests: Load Testing Validation](#9-block-3-tests-load-testing-validation)
10. [Block 4 Tests: Kubernetes Deployment](#10-block-4-tests-kubernetes-deployment)
11. [Continuous Validation Workflow](#11-continuous-validation-workflow)
12. [Augment Code Prompts — Updated with Test Requirements](#12-augment-code-prompts--updated-with-test-requirements)

---

## 1. Testing Philosophy

### The Core Problem

AI coding agents (Augment, Cursor, etc.) make two predictable categories of mistakes:

1. **Silent breakage:** Modifying file A breaks existing behavior in file B, but the agent doesn't know because it has no feedback signal.
2. **Interface drift:** The agent generates code that looks correct in isolation but doesn't match the actual function signatures, return types, or async patterns of your existing code.

### The Fix: Test-Gate-Proceed Pattern

Every block follows this cycle:

```
┌─────────────────────────────────────────────────────────┐
│  1. RUN EXISTING TESTS (baseline — must pass)           │
│                    ↓                                    │
│  2. GENERATE CODE (Augment prompt for feature)          │
│                    ↓                                    │
│  3. GENERATE TESTS (Augment prompt for tests)           │
│                    ↓                                    │
│  4. RUN ALL TESTS (new + existing — must ALL pass)      │
│                    ↓                                    │
│  5. MANUAL SMOKE TEST (one curl/browser check)          │
│                    ↓                                    │
│  6. GIT COMMIT (checkpoint — can always revert here)    │
│                    ↓                                    │
│  7. PROCEED TO NEXT BLOCK                               │
└─────────────────────────────────────────────────────────┘
```

**Rule:** Never start Block N+1 until Block N's tests are green AND existing tests still pass.

**Git discipline:** Commit after every successful block. Tag each with `block-1a-otel`, `block-1b-metrics`, etc. If a later block breaks things, you can `git checkout block-1b-metrics` and you're back to a known-good state in seconds.

### Test Pyramid for This Project

```
         ╱╲
        ╱  ╲         E2E Tests (Block 2+)
       ╱ 5  ╲        docker compose up → trigger threat → verify in Grafana/Jaeger
      ╱──────╲
     ╱        ╲       Integration Tests (Block 1 combined)
    ╱   10     ╲      FastAPI TestClient → full pipeline → verify traces/metrics/logs
   ╱────────────╲
  ╱              ╲    Unit Tests (per sub-block)
 ╱     30+        ╲   Individual functions: telemetry init, metric recording, log format
╱──────────────────╲
     Existing: 48+ tests (must never break)
```

---

## 2. Test Infrastructure Setup (Run First)

### Augment Code Prompt: Test Infrastructure

```
I need to set up test infrastructure for the observability features I'm about to add 
to my FastAPI SOC Agent System. This creates the foundation that all subsequent test 
prompts will use.

EXISTING CONTEXT:
- Test suite: backend/tests/ with 48+ tests using pytest and pytest-asyncio
- Test runner: ./run_tests.sh
- The application uses FastAPI with async/await throughout
- The coordinator calls 5 agents via asyncio.gather, then 3 sequential analyzers

CREATE the following:

1. backend/tests/conftest.py — Add these NEW fixtures (don't overwrite existing fixtures):

   a) `test_client` fixture:
      - Uses FastAPI's TestClient with the actual app instance
      - Sets environment variables before app import:
        OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 (won't actually connect in tests)
        TESTING=true
        LOG_LEVEL=DEBUG

   b) `mock_otel_exporter` fixture:
      - Creates an InMemorySpanExporter from opentelemetry.sdk.trace.export.in_memory
      - Configures a TracerProvider with SimpleSpanProcessor + the in-memory exporter
      - Sets it as the global tracer provider for the test
      - Yields the exporter (tests can call exporter.get_finished_spans())
      - Tears down: resets global tracer provider after test

   c) `sample_threat_signal` fixture:
      - Returns a valid ThreatSignal dict that passes Pydantic validation:
        {
          "threat_type": "credential_stuffing",
          "customer_name": "TestCorp",
          "customer_id": "test-001",
          "source_ip": "192.168.1.100",
          "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
          "request_count": 1500,
          "time_window_minutes": 5,
          "detected_at": "<current ISO timestamp>",
          "raw_data": {"test": true}
        }

   d) `sample_threat_signals_batch` fixture:
      - Returns a list of 5 different ThreatSignal dicts, one for each threat type:
        credential_stuffing, bot_traffic, account_takeover, data_scraping, brute_force
      - Each with different customer names, IPs, and request counts

   e) `reset_prometheus_metrics` fixture (autouse=False):
      - Resets all Prometheus collector registries before each test that uses it
      - This prevents metric state leaking between tests
      - Uses prometheus_client.REGISTRY.unregister() or CollectorRegistry approach

2. backend/tests/helpers.py — Test utility functions:

   a) `trigger_threat(client, signal_dict)` → sends POST /api/threats/trigger, 
      asserts 200, returns response JSON

   b) `get_metrics(client)` → sends GET /metrics, asserts 200, returns response text

   c) `parse_prometheus_metric(metrics_text, metric_name)` → extracts a specific 
      metric value from Prometheus text format output. Returns float value.
      Should handle both counter and histogram types.

   d) `get_health(client)` → sends GET /health, returns response JSON

   e) `get_ready(client)` → sends GET /ready, returns response JSON

   f) `assert_json_log_format(log_line)` → parses a log line as JSON, asserts it 
      contains: timestamp, level, message, trace_id, span_id. Returns parsed dict.

   g) `wait_for_spans(exporter, count, timeout=5)` → polls the InMemorySpanExporter 
      until it has at least `count` finished spans, or times out. Returns spans list.

3. backend/tests/test_regression_baseline.py — Regression safety net:

   a) `test_existing_threat_pipeline_unchanged`:
      - Trigger a threat via TestClient POST /api/threats/trigger
      - Verify response has all expected fields: id, signal, agent_analyses, 
        false_positive_score, response_plan, investigation_timeline, severity,
        mitre_tactics, mitre_techniques, requires_human_review, status
      - Verify agent_analyses has all 5 agents: historical, config, devops, 
        context, priority
      - Verify false_positive_score has: score, confidence, recommendation
      - Verify response_plan has: primary_action, secondary_actions, escalation_path
      - Verify investigation_timeline has: events (non-empty list), duration_ms
      - THIS TEST MUST PASS BEFORE AND AFTER EVERY BLOCK

   b) `test_all_threat_types_still_work`:
      - Loop through all 7 threat types, trigger each one
      - Verify each returns 200 with a valid EnhancedThreatAnalysis
      - Ensures no threat type handling was broken by our changes

   c) `test_get_threats_endpoint`:
      - Trigger 3 threats, then GET /api/threats
      - Verify returns list with at least 3 items

   d) `test_get_threat_by_id`:
      - Trigger a threat, get its ID, then GET /api/threats/{id}
      - Verify returns the same threat

REQUIRED PACKAGES to add to requirements.txt (test dependencies):
pytest
pytest-asyncio
httpx (for FastAPI TestClient async support)
opentelemetry-sdk (already added — needed for InMemorySpanExporter)

IMPORTANT:
- Do NOT modify any existing test files
- The conftest.py should ADD fixtures, not replace existing ones
- All new tests must be async-compatible (use @pytest.mark.asyncio where needed)
- Run ./run_tests.sh after creating these to verify nothing is broken
```

### Gate Check
```bash
# After running this prompt:
cd backend
pytest tests/test_regression_baseline.py -v   # New regression tests pass
pytest tests/ -v                               # ALL existing 48+ tests still pass
git add -A && git commit -m "test: add test infrastructure and regression baseline"
git tag test-infra
```

---

## 3. Block 1A Tests: OpenTelemetry Tracing

### Augment Code Prompt: 1A-Tests (Run AFTER Prompt 1A from main plan)

```
I've just added OpenTelemetry tracing to my SOC Agent System. I need tests to verify 
the instrumentation is correct before I proceed to adding Prometheus metrics.

CONTEXT:
- telemetry.py was created with OTel SDK initialization
- The coordinator's analyze_threat() now has custom spans
- conftest.py has a mock_otel_exporter fixture with InMemorySpanExporter
- helpers.py has wait_for_spans() and trigger_threat() utilities

CREATE backend/tests/test_otel_tracing.py:

1. test_telemetry_module_initializes:
   - Import telemetry module
   - Verify init_telemetry() can be called without errors
   - Verify it returns a TracerProvider (not None)
   - Verify the service name resource attribute is "soc-agent-system"

2. test_fastapi_auto_instrumentation:
   - Use test_client to send GET /health
   - Check mock_otel_exporter has at least 1 span
   - Verify the span has http.method = "GET" and http.route = "/health"
   - This confirms FastAPIInstrumentor is working

3. test_threat_analysis_creates_parent_span:
   - Trigger a threat using sample_threat_signal via test_client
   - Wait for spans using wait_for_spans(exporter, count=1)
   - Find the span named "analyze_threat"
   - Assert it exists
   - Assert it has attributes: threat.type, customer.name, source.ip

4. test_parallel_agent_spans_are_children:
   - Trigger a threat via test_client
   - Wait for spans (expect at least 6: 1 parent + 5 agents)
   - Find the "analyze_threat" parent span
   - Find all 5 agent spans by name pattern (*_agent.analyze or similar)
   - Assert each agent span's parent_id matches the parent span's span_id
   - Assert all 5 agent spans exist (historical, config, devops, context, priority)

5. test_sequential_analyzer_spans_exist:
   - Trigger a threat via test_client
   - Wait for spans (expect at least 9: parent + 5 agents + 3 analyzers)
   - Verify spans exist for: fp_analyzer, response_engine, timeline_builder
   - Verify these are children of the parent "analyze_threat" span

6. test_span_has_final_attributes:
   - Trigger a threat via test_client
   - Find the "analyze_threat" parent span
   - Assert it has final attributes set: threat.severity, fp.score, requires_review
   - Assert fp.score is a float between 0 and 1
   - Assert requires_review is a boolean

7. test_otel_does_not_break_threat_response:
   - Trigger a threat via test_client
   - Assert response status is 200
   - Assert response JSON has all expected fields (same checks as regression test)
   - This ensures OTel instrumentation didn't alter the API response structure

8. test_multiple_concurrent_threats_have_separate_traces:
   - Trigger 3 threats sequentially via test_client
   - Wait for spans
   - Find all "analyze_threat" parent spans
   - Assert each has a different trace_id
   - This verifies trace context isn't leaking between requests

IMPORTANT:
- Use the mock_otel_exporter fixture — do NOT require a real OTel Collector running
- All tests must be runnable with just `pytest` (no external services needed)
- If a span name doesn't match exactly, the test should print what spans WERE found 
  (helps debug naming mismatches from Augment's code generation)
```

### Gate Check
```bash
pytest tests/test_otel_tracing.py -v           # New OTel tests pass
pytest tests/test_regression_baseline.py -v    # Regression still passes
pytest tests/ -v                               # ALL tests pass
git add -A && git commit -m "feat: add OTel tracing with tests"
git tag block-1a-otel
```

---

## 4. Block 1B Tests: Prometheus Metrics

### Augment Code Prompt: 1B-Tests (Run AFTER Prompt 1B from main plan)

```
I've just added Prometheus metrics to my SOC Agent System (which already has OTel tracing). 
I need tests to verify all custom metrics are being recorded correctly.

CONTEXT:
- metrics.py was created with custom Prometheus metrics
- The /metrics endpoint now serves Prometheus format
- helpers.py has get_metrics() and parse_prometheus_metric() utilities
- conftest.py has reset_prometheus_metrics fixture

CREATE backend/tests/test_prometheus_metrics.py:

1. test_metrics_endpoint_returns_prometheus_format:
   - GET /metrics via test_client
   - Assert status 200
   - Assert content type contains "text/plain" or "text/plain; version=0.0.4"
   - Assert response body contains "# HELP" and "# TYPE" lines

2. test_threat_counter_increments:
   - Use reset_prometheus_metrics fixture
   - Get metrics → parse soc_threats_processed_total → note initial value (likely 0)
   - Trigger a credential_stuffing threat
   - Get metrics again → parse soc_threats_processed_total with labels 
     severity and threat_type="credential_stuffing"
   - Assert the counter increased by 1

3. test_threat_counter_labels_by_severity:
   - Reset metrics
   - Trigger 5 threats with sample_threat_signals_batch (different types)
   - Get metrics
   - Assert soc_threats_processed_total exists with multiple severity label values
   - Assert total count across all labels equals 5

4. test_agent_duration_histogram_records:
   - Reset metrics
   - Trigger a threat
   - Get metrics
   - Assert soc_agent_duration_seconds metric exists
   - Assert it has observations for at least the 5 agent names:
     historical, config, devops, context, priority
   - Assert _count for each agent is >= 1

5. test_fp_score_histogram_records:
   - Reset metrics
   - Trigger a threat
   - Get metrics
   - Assert soc_fp_score metric exists
   - Assert _count >= 1
   - Assert the _sum / _count gives a value between 0 and 1

6. test_processing_duration_by_phase:
   - Reset metrics
   - Trigger a threat
   - Get metrics
   - Assert soc_threat_processing_duration_seconds exists with phase labels
   - Verify at least these phases recorded: agent_execution, fp_analysis, total
   - Assert total duration > 0

7. test_review_counter_increments_when_needed:
   - Reset metrics
   - Trigger multiple threats with different signals
   - Get metrics
   - Assert soc_threats_requiring_review_total exists
   - Value should be >= 0 (some threats may not require review)

8. test_http_auto_metrics_from_instrumentator:
   - Reset metrics
   - Send GET /api/threats, POST /api/threats/trigger, GET /health
   - Get metrics
   - Assert http_request_duration_seconds (or similar auto-metric) exists
   - Assert it has entries for different endpoints/methods

9. test_metrics_do_not_break_otel_tracing:
   - Trigger a threat
   - Verify OTel spans are still created (use mock_otel_exporter)
   - Verify Prometheus metrics are recorded
   - Both systems should work independently without interfering

10. test_metrics_do_not_break_threat_response:
    - Trigger a threat
    - Assert response JSON structure matches regression baseline
    - This catches if metrics recording accidentally modifies response data

IMPORTANT:
- Use reset_prometheus_metrics fixture to isolate test state
- parse_prometheus_metric helper must handle histogram format 
  (lines with _bucket, _count, _sum suffixes and {le="..."} labels)
- Tests must not require Prometheus server running — we're testing the 
  /metrics endpoint output directly via TestClient
```

### Gate Check
```bash
pytest tests/test_prometheus_metrics.py -v     # New metrics tests pass
pytest tests/test_otel_tracing.py -v           # OTel tests still pass
pytest tests/test_regression_baseline.py -v    # Regression still passes
pytest tests/ -v                               # ALL tests pass
git add -A && git commit -m "feat: add Prometheus metrics with tests"
git tag block-1b-metrics
```

---

## 5. Block 1C Tests: Structured JSON Logging

### Augment Code Prompt: 1C-Tests (Run AFTER Prompt 1C from main plan)

```
I've just replaced all print statements with structured JSON logging in my SOC Agent 
System. I need tests to verify log format correctness and OTel trace correlation.

CONTEXT:
- logger.py was created with JSON formatter and trace_id injection
- All print() statements replaced with proper logger calls
- OTel tracing is active (from Block 1A) — trace_id should appear in logs
- helpers.py has assert_json_log_format() utility

CREATE backend/tests/test_structured_logging.py:

1. test_log_output_is_valid_json:
   - Capture log output using caplog fixture or by capturing stdout
   - Trigger a threat via test_client
   - Assert at least one log line is valid JSON (json.loads succeeds)
   - Assert it does NOT contain any bare print-style unformatted lines

2. test_log_has_required_fields:
   - Capture logs during threat processing
   - Parse each JSON log line
   - Assert every log entry has: timestamp, level, message
   - Assert timestamp is ISO 8601 format

3. test_log_has_otel_trace_correlation:
   - Trigger a threat via test_client
   - Capture logs
   - Find log entries related to threat processing (e.g., "Threat received", 
     "Agent completed")
   - Assert they have trace_id and span_id fields
   - Assert trace_id is a 32-character hex string (OTel format)
   - Assert trace_id is NOT "0" * 32 (which would mean no active trace context)

4. test_log_trace_id_matches_otel_span:
   - Use mock_otel_exporter fixture
   - Trigger a threat
   - Get the trace_id from the OTel parent span
   - Get the trace_id from the log entries
   - Assert they match — this proves logs are correlated with traces

5. test_key_log_events_exist:
   - Trigger a threat
   - Capture logs
   - Assert these log messages (or patterns) exist:
     - "Threat received" or similar (on ingestion)
     - At least 5 "Agent completed" entries (one per agent)
     - "FP analysis completed" or similar
     - "Threat analysis completed" or similar
   - This ensures we haven't lost any logging during the migration from print()

6. test_log_contains_contextual_fields:
   - Trigger a threat with customer_name="TestCorp"
   - Capture logs
   - Find the "Threat received" log entry
   - Assert it contains customer_name="TestCorp" and threat_type in the JSON

7. test_slow_agent_warning_log:
   - This may require mocking an agent to be slow (>500ms)
   - If not feasible, just verify that the logging code path exists by checking 
     that the logger.warning call is present in the source
   - Alternatively: trigger a threat and check that NO warning appears for 
     normal-speed agents (validates the threshold logic)

8. test_logging_does_not_break_response:
   - Trigger a threat
   - Assert response structure matches regression baseline
   - Logging changes must not alter API behavior

IMPORTANT:
- Use pytest's caplog fixture set to DEBUG level, or capture sys.stdout
- If using caplog, configure it to capture the root logger at DEBUG level:
  caplog.set_level(logging.DEBUG)
- JSON log lines may be mixed with uvicorn access logs — filter for JSON-parseable 
  lines only when asserting
```

### Gate Check
```bash
pytest tests/test_structured_logging.py -v     # New logging tests pass
pytest tests/test_prometheus_metrics.py -v     # Metrics tests still pass
pytest tests/test_otel_tracing.py -v           # OTel tests still pass
pytest tests/test_regression_baseline.py -v    # Regression still passes
pytest tests/ -v                               # ALL tests pass
git add -A && git commit -m "feat: add structured JSON logging with tests"
git tag block-1c-logging
```

---

## 6. Block 1D Tests: Health Check Endpoints

### Augment Code Prompt: 1D-Tests (Run AFTER Prompt 1D from main plan)

```
I've just added /health and /ready endpoints to my FastAPI SOC Agent System for 
Kubernetes probes. I need tests to verify their behavior.

CONTEXT:
- GET /health returns liveness status (always 200 if process running)
- GET /ready returns readiness status (200 only when all components initialized)
- These endpoints are excluded from OTel instrumentation

CREATE backend/tests/test_health_endpoints.py:

1. test_health_returns_200:
   - GET /health via test_client
   - Assert status 200

2. test_health_response_format:
   - GET /health
   - Parse JSON response
   - Assert has fields: status, version, uptime_seconds
   - Assert status == "healthy"
   - Assert version == "2.0"
   - Assert uptime_seconds is a positive number

3. test_health_uptime_increases:
   - GET /health → record uptime_seconds
   - Sleep 1 second (or use time.sleep(0.1) for speed)
   - GET /health again → record uptime_seconds
   - Assert second value > first value

4. test_ready_returns_200_when_initialized:
   - GET /ready via test_client (app is initialized in test setup)
   - Assert status 200

5. test_ready_response_format:
   - GET /ready
   - Parse JSON response
   - Assert has fields: status, components
   - Assert status == "ready"
   - Assert components has: coordinator (boolean)
   - Assert components has agents dict with 5 agents all true
   - Assert components has analyzers dict with fp, response, timeline all true

6. test_health_is_fast:
   - Time the GET /health request
   - Assert it completes in < 50ms
   - Health checks must be lightweight

7. test_ready_is_fast:
   - Time the GET /ready request
   - Assert it completes in < 200ms

8. test_health_not_traced_by_otel:
   - Use mock_otel_exporter fixture
   - Clear any existing spans
   - GET /health
   - Assert no new spans were created for this request
   - This confirms we excluded health checks from OTel instrumentation

9. test_health_not_in_prometheus_metrics:
   - GET /health several times
   - GET /metrics
   - Assert /health is NOT appearing in HTTP metrics (or is filtered)
   - Health check spam should not pollute metrics dashboards

10. test_full_block1_integration:
    - This is the FINAL integration test for all of Block 1
    - Trigger a threat via POST /api/threats/trigger
    - Assert response is valid (regression check)
    - GET /health → assert 200 with correct format
    - GET /ready → assert 200 with all components true
    - GET /metrics → assert Prometheus metrics contain data from the threat
    - Use mock_otel_exporter → assert traces were created for the threat
    - Capture logs → assert JSON format with trace_id
    - ALL OBSERVABILITY SYSTEMS WORKING TOGETHER

IMPORTANT:
- test_full_block1_integration is the most critical test — it validates that 
  OTel + Prometheus + Logging + Health Checks all work together without interfering
- If this test passes, Block 1 is solid and you can confidently proceed to Block 2
```

### Gate Check — FULL BLOCK 1 GATE
```bash
pytest tests/test_health_endpoints.py -v       # New health tests pass
pytest tests/test_structured_logging.py -v     # Logging tests still pass
pytest tests/test_prometheus_metrics.py -v     # Metrics tests still pass
pytest tests/test_otel_tracing.py -v           # OTel tests still pass
pytest tests/test_regression_baseline.py -v    # Regression still passes
pytest tests/ -v --tb=short                    # ALL tests pass — print summary

# If ALL green:
git add -A && git commit -m "feat: add health endpoints with tests — Block 1 complete"
git tag block-1-complete

echo "✅ BLOCK 1 COMPLETE — safe to proceed to Block 2 (Docker Compose)"
```

---

## 7. Block 1 Regression Gate

This is the full command you run before proceeding to Block 2. **Do not proceed if any test fails.**

```bash
#!/bin/bash
# save as: run_block1_gate.sh
set -e

echo "========================================="
echo "  BLOCK 1 REGRESSION GATE"
echo "========================================="

echo ""
echo "--- Step 1: Original 48+ tests ---"
pytest tests/ -v --ignore=tests/test_otel_tracing.py \
                  --ignore=tests/test_prometheus_metrics.py \
                  --ignore=tests/test_structured_logging.py \
                  --ignore=tests/test_health_endpoints.py \
                  --ignore=tests/test_regression_baseline.py
echo "✅ Original tests pass"

echo ""
echo "--- Step 2: Regression baseline ---"
pytest tests/test_regression_baseline.py -v
echo "✅ Regression baseline passes"

echo ""
echo "--- Step 3: OTel tracing ---"
pytest tests/test_otel_tracing.py -v
echo "✅ OTel tracing tests pass"

echo ""
echo "--- Step 4: Prometheus metrics ---"
pytest tests/test_prometheus_metrics.py -v
echo "✅ Prometheus metrics tests pass"

echo ""
echo "--- Step 5: Structured logging ---"
pytest tests/test_structured_logging.py -v
echo "✅ Structured logging tests pass"

echo ""
echo "--- Step 6: Health endpoints ---"
pytest tests/test_health_endpoints.py -v
echo "✅ Health endpoint tests pass"

echo ""
echo "--- Step 7: Full coverage report ---"
pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

echo ""
echo "========================================="
echo "  ✅ ALL GATES PASSED — BLOCK 1 COMPLETE"
echo "  Safe to proceed to Block 2"
echo "========================================="
```

---

## 8. Block 2 Tests: Docker Compose Integration

These are E2E tests that run AFTER `docker compose up`. They verify the full stack works together.

### Script: `tests/e2e/test_docker_compose.sh`

```bash
#!/bin/bash
# E2E tests for Docker Compose stack
# Run AFTER: docker compose up -d
set -e

BASE_URL="http://localhost:8000"
GRAFANA_URL="http://localhost:3000"
JAEGER_URL="http://localhost:16686"
FRONTEND_URL="http://localhost:3001"

echo "========================================="
echo "  BLOCK 2 E2E TESTS"
echo "========================================="

echo ""
echo "--- Test 1: Backend health ---"
HEALTH=$(curl -sf $BASE_URL/health)
echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null
echo "✅ Backend healthy"

echo ""
echo "--- Test 2: Backend readiness ---"
READY=$(curl -sf $BASE_URL/ready)
echo "$READY" | jq -e '.status == "ready"' > /dev/null
echo "✅ Backend ready"

echo ""
echo "--- Test 3: Prometheus metrics endpoint ---"
METRICS=$(curl -sf $BASE_URL/metrics)
echo "$METRICS" | grep -q "# HELP"
echo "✅ Prometheus metrics served"

echo ""
echo "--- Test 4: Frontend accessible ---"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" $FRONTEND_URL)
[ "$HTTP_CODE" = "200" ]
echo "✅ Frontend accessible"

echo ""
echo "--- Test 5: Grafana accessible with dashboards ---"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" $GRAFANA_URL/api/health)
[ "$HTTP_CODE" = "200" ]
# Check dashboards are provisioned
DASHBOARDS=$(curl -sf "$GRAFANA_URL/api/search?type=dash-db")
DASH_COUNT=$(echo "$DASHBOARDS" | jq 'length')
[ "$DASH_COUNT" -ge 3 ]
echo "✅ Grafana up with $DASH_COUNT dashboards"

echo ""
echo "--- Test 6: Jaeger accessible ---"
HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" $JAEGER_URL)
[ "$HTTP_CODE" = "200" ]
echo "✅ Jaeger accessible"

echo ""
echo "--- Test 7: Trigger threat → verify full pipeline ---"
THREAT_RESPONSE=$(curl -sf -X POST $BASE_URL/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "threat_type": "credential_stuffing",
    "customer_name": "E2E-TestCorp",
    "customer_id": "e2e-001",
    "source_ip": "10.0.0.1",
    "request_count": 1000,
    "time_window_minutes": 5,
    "detected_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "raw_data": {}
  }')
THREAT_ID=$(echo "$THREAT_RESPONSE" | jq -r '.id')
echo "  Threat created: $THREAT_ID"

# Verify response structure
echo "$THREAT_RESPONSE" | jq -e '.agent_analyses | length == 5' > /dev/null
echo "$THREAT_RESPONSE" | jq -e '.false_positive_score.score' > /dev/null
echo "$THREAT_RESPONSE" | jq -e '.response_plan.primary_action' > /dev/null
echo "$THREAT_RESPONSE" | jq -e '.investigation_timeline.events | length > 0' > /dev/null
echo "✅ Threat pipeline complete with all components"

echo ""
echo "--- Test 8: Verify metrics recorded for threat ---"
sleep 2  # Wait for metrics scrape
METRICS_AFTER=$(curl -sf $BASE_URL/metrics)
echo "$METRICS_AFTER" | grep -q "soc_threats_processed_total"
echo "✅ Threat metrics recorded"

echo ""
echo "--- Test 9: Verify traces in Jaeger ---"
sleep 3  # Wait for trace export + collection
TRACES=$(curl -sf "$JAEGER_URL/api/traces?service=soc-agent-system&limit=1")
TRACE_COUNT=$(echo "$TRACES" | jq '.data | length')
[ "$TRACE_COUNT" -ge 1 ]
echo "✅ Traces visible in Jaeger ($TRACE_COUNT found)"

echo ""
echo "--- Test 10: Verify threat retrievable via API ---"
GET_RESPONSE=$(curl -sf "$BASE_URL/api/threats/$THREAT_ID")
echo "$GET_RESPONSE" | jq -e ".id == \"$THREAT_ID\"" > /dev/null
echo "✅ Threat retrievable by ID"

echo ""
echo "========================================="
echo "  ✅ ALL BLOCK 2 E2E TESTS PASSED"
echo "  Stack is fully operational"
echo "========================================="
```

### Gate Check
```bash
docker compose build                          # Build succeeds
docker compose up -d                          # Stack starts
sleep 15                                       # Wait for initialization
chmod +x tests/e2e/test_docker_compose.sh
./tests/e2e/test_docker_compose.sh            # All 10 E2E tests pass
git add -A && git commit -m "feat: Docker Compose full stack with E2E tests — Block 2 complete"
git tag block-2-complete
```

---

## 9. Block 3 Tests: Load Testing Validation

### Script: `tests/e2e/test_load_testing.sh`

```bash
#!/bin/bash
# Validates Locust load test works and observability captures the traffic
# Run AFTER: docker compose up -d (Block 2 must be passing)
set -e

echo "========================================="
echo "  BLOCK 3 LOAD TESTING VALIDATION"
echo "========================================="

echo ""
echo "--- Pre-check: Stack healthy ---"
curl -sf http://localhost:8000/health | jq -e '.status == "healthy"' > /dev/null
echo "✅ Stack healthy"

echo ""
echo "--- Test 1: Locust file is valid Python ---"
python -c "import loadtests.locustfile; print('Module imports OK')"
echo "✅ Locust file parses correctly"

echo ""
echo "--- Test 2: Short headless load test (30 seconds) ---"
METRICS_BEFORE=$(curl -sf http://localhost:8000/metrics)
BEFORE_COUNT=$(echo "$METRICS_BEFORE" | grep 'soc_threats_processed_total' | grep -v '#' | awk '{sum += $2} END {print sum+0}')
echo "  Threats before: $BEFORE_COUNT"

locust -f loadtests/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 5 \
  --spawn-rate 2 \
  --run-time 30s \
  --only-summary 2>&1 | tail -5

METRICS_AFTER=$(curl -sf http://localhost:8000/metrics)
AFTER_COUNT=$(echo "$METRICS_AFTER" | grep 'soc_threats_processed_total' | grep -v '#' | awk '{sum += $2} END {print sum+0}')
echo "  Threats after: $AFTER_COUNT"

DIFF=$((AFTER_COUNT - BEFORE_COUNT))
[ "$DIFF" -ge 5 ]
echo "✅ Load test generated $DIFF threats"

echo ""
echo "--- Test 3: Verify Grafana has data from load test ---"
# Query Prometheus via Grafana's data source proxy
QUERY_RESULT=$(curl -sf "http://localhost:9090/api/v1/query?query=soc_threats_processed_total")
RESULT_STATUS=$(echo "$QUERY_RESULT" | jq -r '.status')
[ "$RESULT_STATUS" = "success" ]
echo "✅ Prometheus has threat metrics from load test"

echo ""
echo "--- Test 4: Verify Jaeger has traces from load test ---"
sleep 5
TRACES=$(curl -sf "http://localhost:16686/api/traces?service=soc-agent-system&limit=5")
TRACE_COUNT=$(echo "$TRACES" | jq '.data | length')
[ "$TRACE_COUNT" -ge 3 ]
echo "✅ Jaeger has $TRACE_COUNT traces from load test"

echo ""
echo "--- Test 5: No errors during load test ---"
ERROR_METRICS=$(curl -sf http://localhost:8000/metrics | grep 'http_request_duration.*status="5' || echo "none")
if [ "$ERROR_METRICS" = "none" ]; then
    echo "✅ No 5xx errors during load test"
else
    echo "⚠️  Some 5xx errors detected — check manually"
    echo "$ERROR_METRICS"
fi

echo ""
echo "========================================="
echo "  ✅ ALL BLOCK 3 TESTS PASSED"
echo "  Load testing + observability validated"
echo "========================================="
```

### Gate Check
```bash
chmod +x tests/e2e/test_load_testing.sh
./tests/e2e/test_load_testing.sh              # All load test validations pass
git add -A && git commit -m "feat: Locust load testing with validation — Block 3 complete"
git tag block-3-complete
```

---

## 10. Block 4 Tests: Kubernetes Deployment

### Script: `tests/e2e/test_k8s_deployment.sh`

```bash
#!/bin/bash
# Validates Kind + Helm deployment works end-to-end
# Run AFTER: ./deploy.sh
set -e

echo "========================================="
echo "  BLOCK 4 K8S DEPLOYMENT TESTS"
echo "========================================="

echo ""
echo "--- Test 1: All pods are Running ---"
NOT_RUNNING=$(kubectl get pods --no-headers | grep -v "Running" | grep -v "Completed" || true)
if [ -z "$NOT_RUNNING" ]; then
    echo "✅ All pods running"
else
    echo "❌ Some pods not running:"
    echo "$NOT_RUNNING"
    exit 1
fi

echo ""
echo "--- Test 2: Backend pods have readiness ---"
READY_PODS=$(kubectl get pods -l app=soc-backend -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}')
echo "$READY_PODS" | grep -v "False" > /dev/null
echo "✅ Backend pods ready"

echo ""
echo "--- Test 3: HPA configured ---"
HPA=$(kubectl get hpa soc-backend -o jsonpath='{.spec.maxReplicas}' 2>/dev/null || echo "0")
[ "$HPA" -ge 2 ]
echo "✅ HPA configured (max replicas: $HPA)"

echo ""
echo "--- Test 4: Health check through ingress ---"
HEALTH=$(curl -sf http://localhost:8080/health || echo "FAIL")
echo "$HEALTH" | jq -e '.status == "healthy"' > /dev/null 2>&1
echo "✅ Health check through ingress works"

echo ""
echo "--- Test 5: Trigger threat through ingress ---"
RESPONSE=$(curl -sf -X POST http://localhost:8080/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "threat_type": "bot_traffic",
    "customer_name": "K8s-TestCorp",
    "customer_id": "k8s-001",
    "source_ip": "10.0.0.1",
    "request_count": 500,
    "time_window_minutes": 5,
    "detected_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "raw_data": {}
  }')
echo "$RESPONSE" | jq -e '.id' > /dev/null
echo "✅ Threat pipeline works through K8s"

echo ""
echo "--- Test 6: Logs are structured JSON ---"
LOG_LINE=$(kubectl logs -l app=soc-backend --tail=5 | head -1)
echo "$LOG_LINE" | python -c "import sys, json; json.load(sys.stdin)" 2>/dev/null
echo "✅ Pod logs are structured JSON"

echo ""
echo "========================================="
echo "  ✅ ALL BLOCK 4 K8S TESTS PASSED"
echo "========================================="
```

---

## 11. Continuous Validation Workflow

### The Exact Sequence You Follow

```
╔══════════════════════════════════════════════════════════════════════╗
║  SATURDAY PM                                                        ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Step 1: Run existing 48+ tests → must pass (baseline)               ║
║  Step 2: Run Prompt "Test Infrastructure" → run tests → commit       ║
║  Step 3: Run Prompt 1A (OTel code) → run Prompt 1A-Tests → commit   ║
║  Step 4: Run Prompt 1B (Metrics code) → run Prompt 1B-Tests → commit║
║  Step 5: Run Prompt 1C (Logging code) → run Prompt 1C-Tests → commit║
║  Step 6: Run Prompt 1D (Health code) → run Prompt 1D-Tests → commit ║
║  Step 7: Run run_block1_gate.sh → ALL green? → tag block-1-complete  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  SUNDAY AM                                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Step 8: Run Intent Spec 2A (Docker Compose) → generate files        ║
║  Step 9: docker compose build && docker compose up -d                ║
║  Step 10: Run test_docker_compose.sh → ALL green? → commit           ║
║                                                                      ║
║  DECISION POINT: If Block 2 E2E passes → proceed                    ║
║                  If Block 2 E2E fails → debug Docker, skip Block 4   ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  SUNDAY PM                                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Step 11: Run Intent Spec 2C (Locust) → generate files               ║
║  Step 12: Run test_load_testing.sh → ALL green? → commit             ║
║                                                                      ║
║  Step 13 (if time): Run Intent Spec 2B (Helm) → generate files       ║
║  Step 14 (if time): ./deploy.sh → test_k8s_deployment.sh → commit    ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  MONDAY AM (before 9:30)                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Step 15: Security scanning (Makefile) — no tests needed              ║
║  Step 16: Architecture diagram — no tests needed                     ║
║  Step 17: FULL DRY RUN of demo — use test scripts as smoke tests     ║
║  Step 18: Prep all browser tabs + terminals for interview             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### If Augment Generates Broken Code

Here's the debugging protocol when a test fails after an Augment prompt:

```
Test fails after Prompt N
        │
        ▼
Read the test failure message carefully
        │
        ├── ImportError / ModuleNotFoundError
        │   → Augment used wrong module name or forgot to add to requirements.txt
        │   → Fix: Tell Augment "The import for X failed. The correct module is Y. Fix it."
        │
        ├── AttributeError (object has no attribute 'xyz')
        │   → Augment assumed wrong function/method name from existing code
        │   → Fix: Tell Augment "The actual method name is X, not Y. Here's the 
        │     signature: <paste from existing code>. Update the implementation."
        │
        ├── AssertionError in test (expected value doesn't match)
        │   → Either the code or the test has wrong expectations
        │   → Fix: Check which is correct manually. Paste error to Augment:
        │     "Test expected X but got Y. The test expectation is correct. Fix the code."
        │     OR: "The code returns Y which is correct. Fix the test to expect Y."
        │
        ├── Existing tests broke (regression!)
        │   → Augment modified something it shouldn't have
        │   → Fix: git diff HEAD~1 to see what changed. Revert the specific 
        │     file that broke. Tell Augment: "Your change to <file> broke 
        │     <test>. Do not modify <file>. Find another approach."
        │
        └── RuntimeError / async issues
            → Common with OTel + async: event loop conflicts, context propagation
            → Fix: Tell Augment the exact error. Often needs
              "Use tracer.start_as_current_span as context manager, not decorator"
              or "Use opentelemetry.context.attach/detach for async propagation"
```

---

*This addendum should be used alongside the main SOC_Demo_Enhancement_Plan.md. 
Every Augment Code prompt in Section 12 of that document should be followed by the 
corresponding test prompt from this document before proceeding.*

*Last updated: February 14, 2026*
