# SOC Agent System - Observability Stack

Complete observability solution for the AI SOC Agent System, implementing the three pillars of observability: **Metrics**, **Traces**, and **Logs**.

## 📊 Overview

This observability stack provides comprehensive monitoring and debugging capabilities for the SOC agent system through:

- **Metrics** (Prometheus): Performance metrics, threat counters, agent durations
- **Traces** (Jaeger): Distributed tracing across multi-agent threat analysis pipeline
- **Logs** (Loki + Promtail): Structured JSON logs with trace correlation

All components are integrated with **Grafana** for unified visualization and correlation.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOC Agent Backend                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ OpenTelemetry│  │  Prometheus  │  │ JSON Logging │          │
│  │   (Traces)   │  │  (Metrics)   │  │   (Logs)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
    ┌─────────┐        ┌──────────┐      ┌──────────┐
    │ Jaeger  │        │Prometheus│      │ Promtail │
    │ :4317   │        │  :9090   │      │  :9080   │
    └────┬────┘        └────┬─────┘      └────┬─────┘
         │                  │                  │
         │                  │                  ▼
         │                  │            ┌──────────┐
         │                  │            │   Loki   │
         │                  │            │  :3100   │
         │                  │            └────┬─────┘
         │                  │                 │
         └──────────────────┴─────────────────┘
                            │
                            ▼
                      ┌──────────┐
                      │ Grafana  │
                      │  :3000   │
                      └──────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- SOC Agent backend running on `localhost:8000`

### Starting the Stack

```bash
cd soc-agent-system/observability
docker compose up -d
```

### Accessing the UIs

| Service    | URL                          | Credentials    |
|------------|------------------------------|----------------|
| Grafana    | http://localhost:3000        | admin / admin  |
| Prometheus | http://localhost:9090        | None           |
| Jaeger     | http://localhost:16686       | None           |
| Loki       | http://localhost:3100        | None (API)     |

### Running the Backend with Logging

To enable file-based logging for Promtail:

```bash
cd soc-agent-system/backend
./run_with_logging.sh
```

This script runs the backend and writes logs to both console and `observability/logs/soc-agent.log`.

## 📈 Components

### 1. Jaeger (Distributed Tracing)

**Purpose**: Visualize distributed traces across the multi-agent threat analysis pipeline.

**Configuration**: `observability/jaeger/` (uses default all-in-one image)

**Key Features**:
- OTLP receiver on port 4317
- UI on port 16686
- Trace-to-logs correlation enabled
- Trace-to-metrics correlation enabled

**Expected Spans per Threat**:
- 1 parent span: `analyze_threat`
- 5 agent spans: historical, config, devops, context, priority
- 3 analyzer spans: fp_analyzer, response_engine, timeline_builder
- **Total**: 9 spans per threat

**Span Attributes**:
- `threat.type`: Type of threat detected
- `customer.name`: Customer identifier
- `source.ip`: Source IP address
- `threat.severity`: Severity level (low/medium/high/critical)
- `fp.score`: False positive probability (0.0-1.0)
- `requires_review`: Boolean flag for human review

### 2. Prometheus (Metrics)

**Purpose**: Collect and store time-series metrics from the SOC agent system.

**Configuration**: `observability/prometheus/prometheus.yml`

**Scrape Configuration**:
- Target: `host.docker.internal:8000/metrics`
- Interval: 15 seconds
- Retention: 15 days

**Custom SOC Metrics**:

| Metric Name | Type | Description |
|-------------|------|-------------|
| `soc_threats_processed_total` | Counter | Total threats processed (labels: severity, threat_type, customer) |
| `soc_agent_duration_seconds` | Histogram | Agent execution time (labels: agent_name) |
| `soc_fp_score` | Histogram | False positive scores distribution |
| `soc_threat_processing_duration_seconds` | Histogram | End-to-end processing time (labels: phase) |
| `soc_active_websocket_connections` | Gauge | Current WebSocket connections |
| `soc_threats_requiring_review` | Gauge | Threats flagged for human review |

**Auto-Instrumented Metrics**:
- HTTP request duration, count, size (via prometheus-fastapi-instrumentator)
- Process metrics (CPU, memory, file descriptors)

### 3. Loki (Log Aggregation)

**Purpose**: Centralized log storage and querying for structured JSON logs.

**Configuration**: `observability/loki/loki-config.yml`

**Key Settings**:
- Storage: Filesystem-based (chunks and rules in `/loki`)
- Replication factor: 1 (single instance)
- Retention: 7 days (`reject_old_samples_max_age: 168h`)
- Ingestion rate: 10 MB/s (burst: 20 MB/s)

**Important Configuration**:
```yaml
common:
  ring:
    instance_addr: 0.0.0.0  # Must be in ring section for Docker
```

**API Endpoints**:
- Query: `http://localhost:3100/loki/api/v1/query`
- Query Range: `http://localhost:3100/loki/api/v1/query_range`
- Labels: `http://localhost:3100/loki/api/v1/labels`

### 4. Promtail (Log Collection)

**Purpose**: Tail log files and ship them to Loki with structured field extraction.

**Configuration**: `observability/promtail/promtail-config.yml`

**Log Source**: `observability/logs/soc-agent.log` (mounted as `/var/log/soc-agent/*.log`)

**Pipeline Stages**:

1. **JSON Parsing**: Extract fields from JSON log lines
   - `timestamp`, `level`, `logger_name`, `module`
   - `trace_id`, `span_id` (for correlation)
   - `message`

2. **Timestamp Parsing**: Use extracted timestamp as log entry time
   - Format: `2006-01-02T15:04:05Z` (UTC with 'Z' suffix)
   - Fallback formats for microseconds/milliseconds

3. **Label Promotion**: Promote fields to Loki labels
   - `level`, `logger_name`, `module`
   - **`trace_id`, `span_id`** (enables trace-to-logs correlation)

4. **Output**: Set log line to the `message` field only

**Example Log Entry**:
```json
{
  "timestamp": "2026-02-15T16:33:48Z",
  "level": "INFO",
  "logger_name": "agents.coordinator",
  "module": "coordinator",
  "trace_id": "cd77def4eb3639642212838e06333d23",
  "span_id": "8caa8c1757859725",
  "message": "✓ Response Plan: challenge (normal)"
}
```

### 5. Grafana (Visualization)

**Purpose**: Unified dashboard for metrics, traces, and logs with correlation.

**Configuration**:
- Datasources: `observability/grafana/provisioning/datasources/datasources.yml`
- Dashboards: `observability/grafana/provisioning/dashboards/`
- Dashboard JSON: `observability/grafana/dashboards/soc-dashboard.json`

**Pre-configured Datasources**:
1. **Prometheus** (default) - Metrics
2. **Loki** - Logs with trace correlation
3. **Jaeger** - Traces with logs/metrics correlation

**Pre-built Dashboard**: "SOC Agent System Overview"

Access at: http://localhost:3000/d/soc-dashboard/soc-agent-system

## 📊 SOC Agent System Dashboard

The pre-built dashboard includes the following panels:

### Metrics Panels

1. **Threat Processing Rate**
   - Query: `rate(soc_threats_processed_total[5m])`
   - Grouped by: severity, threat_type
   - Type: Time series graph

2. **Agent Duration Percentiles**
   - Queries: p50, p95, p99 of `soc_agent_duration_seconds`
   - Grouped by: agent_name
   - Type: Time series graph

3. **Active WebSocket Connections**
   - Query: `soc_active_websocket_connections`
   - Type: Stat panel (gauge)

4. **Threats Requiring Review**
   - Query: `soc_threats_requiring_review`
   - Type: Stat panel

5. **FP Score Distribution**
   - Query: `soc_fp_score_bucket`
   - Type: Heatmap

6. **Processing Duration by Phase**
   - Query: `soc_threat_processing_duration_seconds`
   - Grouped by: phase
   - Type: Time series graph

### Logs Panel

7. **Recent Logs with Trace Correlation**
   - Query: `{job="soc-agent"}`
   - Features:
     - Clickable `trace_id` to jump to Jaeger
     - JSON field extraction
     - Real-time log streaming
   - Type: Logs panel

## 🔗 Trace-to-Logs Correlation

The observability stack provides **bidirectional correlation** between traces and logs.

### Forward Correlation: Logs → Traces

**How it works**:
1. Promtail extracts `trace_id` from JSON logs and promotes it to a **label**
2. Grafana's Loki datasource has `derivedFields` configured with `matcherType: "label"`
3. When viewing logs in Grafana, the `trace_id` becomes a clickable link
4. Clicking opens the corresponding trace in Jaeger

**Configuration** (`datasources.yml`):
```yaml
- name: Loki
  jsonData:
    derivedFields:
      - datasourceUid: jaeger-uid
        matcherType: "label"
        matcherRegex: "trace_id"
        name: "TraceID"
        url: "${__value.raw}"
        urlDisplayLabel: "View in Jaeger"
```

### Reverse Correlation: Traces → Logs

**How it works**:
1. When viewing a trace in Jaeger, each span has a "Logs" button
2. Clicking opens Grafana Explore with Loki logs filtered by `trace_id`
3. Time range is automatically set to ±1 hour around the span

**Configuration** (`datasources.yml`):
```yaml
- name: Jaeger
  jsonData:
    tracesToLogsV2:
      datasourceUid: loki-uid
      spanStartTimeShift: "-1h"
      spanEndTimeShift: "1h"
      filterByTraceID: true
```

## 🧪 Testing the Stack

### 1. Verify All Services are Running

```bash
cd soc-agent-system/observability
docker compose ps
```

All services should show "Up" status.

### 2. Test Metrics Collection

```bash
# Check backend metrics endpoint
curl http://localhost:8000/metrics | grep soc_

# Check Prometheus is scraping
curl -s 'http://localhost:9090/api/v1/query?query=up{job="soc-agent"}' | jq '.data.result[0].value'
```

Expected: `[<timestamp>, "1"]` (backend is up)

### 3. Generate Test Threats

```bash
# Generate a test threat
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"threat_type": "bot_traffic", "customer_name": "Test Corp"}'
```

### 4. Verify Traces in Jaeger

1. Open http://localhost:16686
2. Select service: `soc-agent-system`
3. Click "Find Traces"
4. You should see traces with 9 spans each

### 5. Verify Logs in Loki

```bash
# Query Loki API
curl -s 'http://localhost:3100/loki/api/v1/query_range?query={job="soc-agent"}&limit=5' | jq '.data.result | length'
```

Expected: Number > 0 (logs are being ingested)

### 6. Test Trace-to-Logs Correlation

1. Open Grafana: http://localhost:3000
2. Go to the "SOC Agent System Overview" dashboard
3. In the "Recent Logs" panel, find a log entry with a `trace_id`
4. Click on the `trace_id` value
5. Verify it opens Jaeger showing the corresponding trace

## 🔧 Troubleshooting

### Issue: Logs Not Appearing in Loki

**Symptoms**: Grafana logs panel is empty, Loki query returns no results.

**Common Causes**:

1. **Timestamp Timezone Issue**
   - **Problem**: Log timestamps in local time without timezone info
   - **Solution**: Ensure `logger.py` uses UTC with 'Z' suffix:
     ```python
     def formatTime(self, record, datefmt=None):
         dt = datetime.utcfromtimestamp(record.created)
         s = dt.isoformat()
         return s + 'Z'  # Add 'Z' suffix for UTC
     ```
   - **Verify**: Check log file has timestamps like `2026-02-15T16:33:48Z`

2. **Loki Ingester Not Ready**
   - **Problem**: `instance_addr` in wrong location in config
   - **Solution**: Ensure `loki-config.yml` has:
     ```yaml
     common:
       ring:
         instance_addr: 0.0.0.0  # Must be here, not in common section
     ```
   - **Verify**: `docker compose logs loki | grep "ready"`

3. **Promtail Not Tailing File**
   - **Problem**: Log file doesn't exist or wrong path
   - **Solution**: Ensure backend is running with `run_with_logging.sh`
   - **Verify**: `docker compose logs promtail | grep "file target"`

### Issue: Trace ID Not Clickable in Grafana

**Symptoms**: `trace_id` appears in logs but is not a clickable link.

**Solution**: Ensure Loki datasource uses `matcherType: "label"`:

```yaml
derivedFields:
  - datasourceUid: jaeger-uid
    matcherType: "label"  # Important: trace_id is a label, not in log line
    matcherRegex: "trace_id"
```

**Why**: Promtail promotes `trace_id` to a label, so Grafana must match against labels, not log line content.

### Issue: WebSocket Connections Panel Shows 0

**Symptoms**: Metric exists in Prometheus but Grafana panel shows 0.

**Solutions**:
1. Refresh the dashboard (Ctrl+R)
2. Check time range (should be "Last 15 minutes" or wider)
3. Restart Grafana to reload provisioned dashboards:
   ```bash
   docker compose restart grafana
   ```

### Issue: No Traces in Jaeger

**Symptoms**: Jaeger UI shows no traces for `soc-agent-system` service.

**Solutions**:
1. Check backend is sending traces:
   ```bash
   curl http://localhost:8000/metrics | grep otel
   ```
2. Verify OTLP endpoint is reachable:
   ```bash
   curl http://localhost:4317
   ```
3. Check Jaeger logs:
   ```bash
   docker compose logs jaeger | grep -i error
   ```

### Issue: Prometheus Not Scraping Backend

**Symptoms**: `up{job="soc-agent"}` returns 0 or no data.

**Solutions**:
1. Verify backend is accessible from Docker:
   ```bash
   docker compose exec prometheus wget -O- http://host.docker.internal:8000/metrics
   ```
2. Check Prometheus targets: http://localhost:9090/targets
3. Ensure backend is running on port 8000

## 📁 Configuration Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates all 5 observability services |
| `prometheus/prometheus.yml` | Prometheus scrape config and retention |
| `loki/loki-config.yml` | Loki storage, retention, and ingestion limits |
| `promtail/promtail-config.yml` | Log tailing, parsing, and label extraction |
| `grafana/provisioning/datasources/datasources.yml` | Auto-provision datasources with correlation |
| `grafana/provisioning/dashboards/dashboards.yml` | Auto-provision dashboard directory |
| `grafana/dashboards/soc-dashboard.json` | Pre-built SOC metrics dashboard |

## 🔐 Security Considerations

1. **Default Credentials**: Change Grafana admin password after first login
2. **Network Exposure**: All services are exposed on localhost only
3. **Data Retention**: Logs retained for 7 days, metrics for 15 days
4. **Access Control**: No authentication on Prometheus/Jaeger (use reverse proxy in production)

## 🚀 Production Deployment

For production use, consider:

1. **Persistent Storage**: Use Docker volumes or external storage for Loki/Prometheus data
2. **High Availability**: Run multiple replicas of Loki, Prometheus
3. **Authentication**: Enable auth on all services (Grafana, Prometheus, Jaeger)
4. **TLS**: Use HTTPS for all web UIs
5. **Resource Limits**: Set CPU/memory limits in docker-compose.yml
6. **Backup**: Regular backups of Grafana dashboards and Prometheus data
7. **Alerting**: Configure Prometheus Alertmanager for critical metrics

## 📚 Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [LogQL (Loki Query Language)](https://grafana.com/docs/loki/latest/logql/)
- [Jaeger Tracing](https://www.jaegertracing.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)

## 🏷️ Tags

- Block 2: Observability Stack
- Git tag: `block-2-observability-stack`
- Related commits: See git log for observability fixes


