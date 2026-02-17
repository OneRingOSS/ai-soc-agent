# SOC Agent System — Observability Stack

A Docker Compose-based observability stack for the SOC Agent System, providing distributed tracing, metrics collection, log aggregation, and unified dashboards.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  HOST MACHINE                                                       │
│                                                                     │
│  ┌──────────────────────────┐                                       │
│  │  SOC Backend (FastAPI)   │                                       │
│  │  localhost:8000          │                                       │
│  │                          │                                       │
│  │  /metrics ──────────────────────────────────┐                    │
│  │  OTLP traces ───────────────────────┐       │                    │
│  │  JSON logs → logs/soc-agent.log ─┐  │       │                    │
│  └──────────────────────────────────┼──┼───────┼────────────────┘   │
│                                     │  │       │                    │
└─────────────────────────────────────┼──┼───────┼────────────────────┘
                                      │  │       │
┌─────────────────────────────────────┼──┼───────┼────────────────────┐
│  DOCKER (observability stack)       │  │       │                    │
│                                     │  │       │                    │
│  ┌───────────┐  reads log file      │  │       │                    │
│  │ Promtail  │◄─────────────────────┘  │       │                    │
│  └─────┬─────┘                         │       │                    │
│        │ pushes                         │       │                    │
│        ▼                               │       │                    │
│  ┌───────────┐                         │       │                    │
│  │   Loki    │ :3100                   │       │                    │
│  └─────┬─────┘                         │       │                    │
│        │                               │       │                    │
│  ┌───────────┐  receives OTLP          │       │                    │
│  │  Jaeger   │◄────────────────────────┘       │                    │
│  │  :16686   │ :4317                           │                    │
│  └─────┬─────┘                                 │                    │
│        │                                       │                    │
│  ┌────────────┐  scrapes /metrics              │                    │
│  │ Prometheus │◄───────────────────────────────┘                    │
│  │  :9090     │ (host.docker.internal:8000)                         │
│  └─────┬──────┘                                                     │
│        │                                                            │
│  ┌───────────┐                                                      │
│  │  Grafana  │ :3000  ◄── queries all three datasources             │
│  └───────────┘                                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**Data Flow:**
- **Traces**: Backend → OTLP (gRPC :4317) → Jaeger → Grafana
- **Metrics**: Backend `/metrics` ← Prometheus scrapes every 15s → Grafana
- **Logs**: Backend → `logs/soc-agent.log` → Promtail → Loki → Grafana

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- SOC Agent System backend running on `localhost:8000`

## Quick Start

```bash
# From the soc-agent-system/observability/ directory
cd soc-agent-system/observability

# Start all observability services
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

## Service URLs

| Service    | URL                          | Purpose                        | Credentials   |
|------------|------------------------------|--------------------------------|---------------|
| Jaeger UI  | http://localhost:16686       | Distributed trace viewer       | —             |
| Prometheus | http://localhost:9090        | Metrics queries & targets      | —             |
| Grafana    | http://localhost:3000        | Unified dashboards             | admin / admin |
| Loki API   | http://localhost:3100        | Log aggregation (API only)     | —             |

## Configuring Backend Logging

The backend logs to stdout by default. For Promtail to ingest logs into Loki, the backend must also write logs to a file.

### Option A: Tee stdout to file (recommended)

Pipe backend output to both the terminal and the log file:

```bash
# From the soc-agent-system/backend/ directory
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 2>&1 | tee ../observability/logs/soc-agent.log
```

### Option B: Add a Python file handler

Add a file handler to the backend's logging configuration:

```python
import logging

# Add to your logging setup (e.g., in src/logger.py)
file_handler = logging.FileHandler("../observability/logs/soc-agent.log")
file_handler.setFormatter(logging.Formatter('%(message)s'))  # JSON logs are already formatted
logging.getLogger().addHandler(file_handler)
```

> **Note:** The `observability/logs/` directory is mounted into the Promtail container. Promtail watches `soc-agent.log` for new lines and pushes them to Loki.

## Verification Steps

After starting the stack, verify each component is working:

### 1. Jaeger — Check Traces

1. Start the backend and send a request (e.g., `POST /api/threats/analyze`)
2. Open http://localhost:16686
3. Select service **"soc-agent-system"** from the dropdown
4. Click **"Find Traces"**
5. ✅ You should see traces with spans for `analyze_threat`, individual agents, etc.

### 2. Prometheus — Check Targets

1. Open http://localhost:9090/targets
2. ✅ The `soc-backend` target should show **State: UP**
3. Try a query: `soc_threats_processed_total` in the query box
4. ✅ You should see metric results (may be 0 if no threats processed yet)

### 3. Loki — Check Log Ingestion

1. Ensure the backend is writing logs (see [Configuring Backend Logging](#configuring-backend-logging))
2. Open Grafana at http://localhost:3000
3. Go to **Explore** → select **Loki** datasource
4. Run query: `{job="soc-agent"}`
5. ✅ You should see JSON log entries from the backend

### 4. Grafana — Check Datasources & Dashboard

1. Open http://localhost:3000 (login: admin / admin)
2. Go to **Connections → Data sources**
3. ✅ Verify three datasources are listed: Prometheus, Loki, Jaeger
4. Click **"Test"** on each — all should show a green success message
5. Go to **Dashboards** → look for the **SOC Agent System** dashboard
6. ✅ Panels should display data once the backend is running and processing threats


## Common Commands

```bash
# Start all services in the background
docker-compose up -d

# Stop all services (preserves data volumes)
docker-compose down

# Stop all services and remove data volumes
docker-compose down -v

# View logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f jaeger
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f loki
docker-compose logs -f promtail

# Restart a single service
docker-compose restart prometheus

# Check service status
docker-compose ps

# Rebuild and restart (after config changes)
docker-compose up -d --force-recreate
```

## Troubleshooting

### Port Conflicts

If a service fails to start with a "port already in use" error:

```bash
# Find what's using the port (e.g., 3000)
lsof -i :3000

# Kill the process or change the port mapping in docker-compose.yml
# For example, to map Grafana to port 3001 instead:
#   ports:
#     - "3001:3000"
```

Common port conflicts:
| Port  | Service    | Common Conflict              |
|-------|------------|------------------------------|
| 3000  | Grafana    | React dev servers, other Grafana instances |
| 9090  | Prometheus | Other Prometheus instances   |
| 16686 | Jaeger     | Other Jaeger instances       |
| 4317  | Jaeger     | OTel Collectors              |

### `host.docker.internal` Not Resolving (Linux)

On Linux, `host.docker.internal` is not available by default. Add `extra_hosts` to services that need to reach the host in `docker-compose.yml`:

```yaml
services:
  prometheus:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Alternatively, use the host's IP address directly in the Prometheus scrape config.

### No Metrics Showing in Prometheus

1. **Check the backend is running**: `curl http://localhost:8000/metrics`
2. **Check Prometheus targets**: Open http://localhost:9090/targets
   - If target is **DOWN**, the backend is not reachable from the container
   - Verify `host.docker.internal` resolves (see above)
3. **Check Prometheus config**: `docker-compose exec prometheus cat /etc/prometheus/prometheus.yml`

### No Logs Showing in Loki

1. **Check the log file exists**: `ls -la observability/logs/soc-agent.log`
2. **Check Promtail is reading**: `docker-compose logs promtail`
   - Look for "file target" entries showing the log file
3. **Check the log file is being written to**: `tail -f observability/logs/soc-agent.log`
   - If empty, see [Configuring Backend Logging](#configuring-backend-logging)
4. **Check Loki is receiving**: `curl http://localhost:3100/ready`

### No Traces Showing in Jaeger

1. **Check the backend is sending traces**: Look for `OpenTelemetry initialized` in backend logs
2. **Check Jaeger is receiving**: `docker-compose logs jaeger` — look for "span received" messages
3. **Check OTLP endpoint**: The backend should export to `http://localhost:4317`
   - Jaeger exposes port 4317 on the host via Docker port mapping
4. **Verify the service name**: In Jaeger UI, the service should appear as `soc-agent-system`

### Grafana Datasource Errors

1. **"Data source is not working"**: The target service may not be running
   - Check: `docker-compose ps` — all services should be "Up"
2. **Connection refused**: Datasource URLs use Docker service names (e.g., `http://prometheus:9090`)
   - These only work inside the Docker network — don't change them to `localhost`
3. **Re-provision datasources**: `docker-compose restart grafana`

## Directory Structure

```
observability/
├── docker-compose.yml          # All observability services
├── prometheus/
│   └── prometheus.yml          # Scrape config (targets, intervals)
├── loki/
│   └── loki-config.yml         # Loki storage and schema config
├── promtail/
│   └── promtail-config.yml     # Log file paths and label extraction
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── datasources.yml # Auto-configured: Prometheus, Loki, Jaeger
│       └── dashboards/
│           └── dashboards.yml  # Dashboard provisioning config
├── logs/
│   ├── .gitkeep                # Placeholder (log files are gitignored)
│   └── soc-agent.log           # Backend log output (created at runtime)
└── README.md                   # This file
```

## Cleanup

To completely remove the observability stack and all its data:

```bash
# Stop services and remove volumes, networks, and images
docker-compose down -v --rmi local

# Remove log files
rm -f logs/soc-agent.log
```

To stop services but keep data for next time:

```bash
docker-compose down
```