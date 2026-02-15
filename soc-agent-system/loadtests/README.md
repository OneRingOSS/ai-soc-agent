# SOC Agent System — Load Testing Suite

Locust-based load testing for the SOC Agent System backend. The suite generates
realistic threat traffic patterns to exercise the multi-agent analysis pipeline
and validate the observability stack (metrics, traces, logs) under load.

---

## User Classes

The locustfile defines three user classes that simulate different traffic
patterns:

| Class | Weight | Behaviour |
|---|---|---|
| **SteadyStateUser** | 5 | Sends one random threat every 2–5 s. Simulates normal SOC operations. |
| **BurstAttackUser** | 2 | Rapid-fire threats (0.1–0.5 s). Simulates a concentrated attack spike. |
| **MixedRealisticUser** | 3 | Weighted threat distribution matching real-world SOC traffic patterns. |

---

## Prerequisites

**Option A — Python (standalone)**

```bash
pip install locust
```

**Option B — Docker**

```bash
docker compose -f docker-compose.locust.yml up --scale worker=2
```

No Python install required; the `locustio/locust` image includes everything.

---

## Running the Tests

### 1. Standalone (with UI)

```bash
cd soc-agent-system/loadtests
locust -f locustfile.py --host=http://localhost:8000
```

Open <http://localhost:8089> to configure users, spawn rate, and start the test.

### 2. Docker Compose (distributed)

```bash
cd soc-agent-system/loadtests
docker compose -f docker-compose.locust.yml up --scale worker=2
```

This starts a Locust **master** (UI on port 8089) and two **worker** containers.
The workers connect to the master automatically and share the load.

> **Linux note:** `host.docker.internal` is mapped via `extra_hosts` so
> containers can reach the backend running on the host.

### 3. Headless / CI

```bash
cd soc-agent-system/loadtests
locust --headless -u 20 -r 5 -t 2m --host=http://localhost:8000 -f locustfile.py
```

| Flag | Meaning |
|---|---|
| `-u 20` | 20 concurrent users |
| `-r 5` | Spawn 5 users per second |
| `-t 2m` | Run for 2 minutes |
| `--headless` | No web UI — prints summary to stdout |

---

## Scenarios

### Steady-State

Simulates normal day-to-day SOC traffic.

```
Users : 10
Spawn rate : 2 users/s
Duration : 5 minutes
```

```bash
locust --headless -u 10 -r 2 -t 5m --host=http://localhost:8000 -f locustfile.py
```

### Spike Test

Ramps quickly to high concurrency to stress-test the pipeline.

```
Users : 50
Spawn rate : 10 users/s
Duration : ramp to 50, hold 2 min, then stop
```

```bash
locust --headless -u 50 -r 10 -t 2m --host=http://localhost:8000 -f locustfile.py
```

---

## Viewing Results

| Tool | URL | What to look for |
|---|---|---|
| **Locust UI** | <http://localhost:8089> | Request rate, response times, failure % |
| **Grafana** | <http://localhost:3000> | `soc_threats_processed_total`, `soc_agent_duration_seconds` dashboards |
| **Jaeger** | <http://localhost:16686> | Distributed traces showing parallel agent spans per threat |

> Start the observability stack **before** running load tests so metrics and
> traces are captured:
>
> ```bash
> cd soc-agent-system/observability
> docker compose up -d
> ```

---

## API Details

The load tests target a single endpoint:

```
POST /api/threats/trigger
Content-Type: application/json

{
  "threat_type": "<type>"
}
```

### Valid Threat Types (6)

| Value | Description |
|---|---|
| `bot_traffic` | Automated bot activity |
| `proxy_network` | Traffic routed through proxy/VPN networks |
| `device_compromise` | Compromised device indicators |
| `anomaly_detection` | Behavioural anomaly detected |
| `rate_limit_breach` | API rate limit exceeded |
| `geo_anomaly` | Impossible-travel or geo-location anomaly |

The backend generates a full `ThreatSignal` from the type, runs it through the
multi-agent analysis pipeline (5 specialist agents + coordinator), and returns a
`ThreatAnalysis` JSON response. Typical response time is 500–1000 ms.

### Example

```bash
curl -X POST http://localhost:8000/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"threat_type": "bot_traffic"}'
```

