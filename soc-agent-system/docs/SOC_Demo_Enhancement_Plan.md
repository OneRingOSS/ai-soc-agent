# SOC Agent System — Interview Demo Enhancement Plan
## Endor Labs Director of Engineering — Technical Interview Loop

**Target Interviews:** Feb 17, 2026 (Gui Plessis — Platform & Reliability, Alex Wilhelm — Technical Deep Dive)
**Available Time:** ~14 hours across Saturday PM → Monday AM
**Principle:** Impact-first, fallback-ready. Every block produces a demoable outcome even if the next block fails.

---

## Table of Contents

1. [Target Architecture Overview](#1-target-architecture-overview)
2. [Current State vs Target State](#2-current-state-vs-target-state)
3. [Dependency Graph & Build Sequence](#3-dependency-graph--build-sequence)
4. [Block 1: Observability Instrumentation (App Code)](#4-block-1-observability-instrumentation-app-code)
5. [Block 2: Docker Compose Full Stack](#5-block-2-docker-compose-full-stack)
6. [Block 3: Load Testing + Live Observability Demo](#6-block-3-load-testing--live-observability-demo)
7. [Block 4: Kind + Helm Kubernetes Deployment](#7-block-4-kind--helm-kubernetes-deployment)
8. [Block 5: Security Scanning Pipeline](#8-block-5-security-scanning-pipeline)
9. [Block 6: Scaling Architecture Diagram](#9-block-6-scaling-architecture-diagram)
10. [Fallback Strategy](#10-fallback-strategy)
11. [Demo Rehearsal Checklist](#11-demo-rehearsal-checklist)
12. [AI Tool Prompts — Augment Code](#12-ai-tool-prompts--augment-code)
13. [AI Tool Prompts — Intent](#13-ai-tool-prompts--intent)

---

## 1. Target Architecture Overview

The goal is to evolve the SOC Agent System from a **local dev demo** into a **production-grade showcase** with three layers of maturity visible to the interviewers:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                              │
│  React + TailwindCSS Dashboard (localhost:5173 / nginx :80)            │
│  Grafana Dashboards (localhost:3000) ← NEW                             │
│  Locust Load Test UI (localhost:8089) ← NEW                            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        API GATEWAY LAYER                                │
│  FastAPI (localhost:8000)                                               │
│  ├── REST endpoints (existing)                                         │
│  ├── WebSocket endpoint (existing)                                     │
│  ├── /health + /ready endpoints ← NEW                                  │
│  ├── /metrics (Prometheus) ← NEW                                       │
│  └── OpenTelemetry auto-instrumentation ← NEW                          │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     ORCHESTRATION + ANALYSIS LAYER                      │
│  Coordinator Agent → 5 Analysis Agents (parallel) → FP Analyzer →      │
│  Response Engine → Timeline Builder                                     │
│  ├── Custom OTel spans per agent ← NEW                                 │
│  ├── Prometheus histograms per agent ← NEW                             │
│  └── Structured JSON logging with trace correlation ← NEW              │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     OBSERVABILITY LAYER ← ALL NEW                       │
│  ┌──────────────┐  ┌───────────┐  ┌────────┐  ┌──────┐               │
│  │ OTel Collector│→│ Jaeger    │  │Promethe│  │ Loki │               │
│  │              │  │ (traces)  │  │us      │  │(logs)│               │
│  └──────────────┘  └─────┬─────┘  └───┬────┘  └──┬───┘               │
│                          └────────────┼─────────┘                     │
│                                 ┌─────▼─────┐                          │
│                                 │  Grafana   │                          │
│                                 │ (unified)  │                          │
│                                 └───────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER ← ALL NEW                      │
│  Mode A: docker compose up (primary demo, always works)                │
│  Mode B: Kind cluster + Helm chart (K8s showcase, bonus)               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │ Dockerfile   │  │ Helm Chart   │  │ kind-config  │                │
│  │ (multi-stage)│  │ (cloud-agno) │  │ (local K8s)  │                │
│  └──────────────┘  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────────┐
│                     CI / SECURITY LAYER ← ALL NEW                       │
│  Makefile (local) or GitHub Actions                                    │
│  lint (ruff) → test (pytest) → scan-secrets (TruffleHog) →            │
│  scan-image (Trivy) → quality-gate (coverage ≥80%, 0 critical CVEs)   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

- **Cloud-agnostic:** No hyperscaler-specific services. Same Helm chart deploys to GKE, EKS, or AKS. Locally runs on Kind.
- **Open source only:** OTel, Prometheus, Grafana, Jaeger, Loki, Locust, Trivy, TruffleHog. Zero vendor lock-in.
- **Demoable in 60 seconds:** `docker compose up` gets the full stack running. No cloud accounts, no API keys, no billing.
- **Fallback-safe:** Each block is independently valuable. If K8s fails, Docker Compose still works. If observability has issues, the core SOC app still runs.

---

## 2. Current State vs Target State

| Dimension | Current State | Target State |
|---|---|---|
| **Observability** | None — stdout logging, manual timing | OTel traces, Prometheus metrics, Loki logs, Grafana dashboards |
| **Deployment** | 4 manual terminal windows | Single `docker compose up` or `./deploy.sh` for K8s |
| **Container support** | None | Multi-stage Dockerfiles, Helm chart, Kind cluster |
| **Load testing** | Manual `test_threats.py` script | Locust with realistic traffic scenarios + live dashboards |
| **Security scanning** | None | TruffleHog (secrets), Trivy (container CVEs), quality gates |
| **Health checks** | None | `/health`, `/ready` endpoints for K8s probes |
| **Logging** | Unstructured print statements | Structured JSON with OTel trace ID correlation |
| **Metrics** | In-code `processing_time_ms` field | Prometheus histograms, counters, gauges scraped externally |
| **Scaling story** | "Future: PostgreSQL/MongoDB" | Concrete diagram: current → production → enterprise scale |

---

## 3. Dependency Graph & Build Sequence

```
BLOCK 1: Observability Instrumentation ──────────────────────────┐
  (Modify existing app code — Augment Code)                      │
  ├── OTel SDK + custom spans                                    │
  ├── Prometheus metrics endpoint                                ├── PARALLEL with nothing
  ├── Structured JSON logging                                    │   (foundation — must be first)
  └── Health check endpoints                                     │
                                                                 │
BLOCK 2: Docker Compose Full Stack ──────────────────────────────┤
  (New infra files — Intent)                                     │
  ├── Dockerfiles (backend + frontend)                           ├── DEPENDS ON Block 1
  ├── docker-compose.yml (app + observability)                   │   (needs /metrics, /health
  ├── OTel Collector config                                      │    endpoints to exist)
  ├── Prometheus scrape config                                   │
  ├── Grafana provisioning (dashboards + datasources)            │
  └── Loki + Jaeger config                                       │
                                                                 │
     ┌───────────────────────────────────────────────────────────┘
     │
     ▼
BLOCK 3: Load Testing ──────────────┐    BLOCK 4: Kind + Helm ──────────┐
  (New files — either tool)         │      (New infra — Intent)         │
  ├── locustfile.py                 │      ├── Helm chart               │
  ├── Scenario scripts              ├──┐   ├── kind-config.yaml         ├──┐
  └── Demo run script               │  │   ├── deploy.sh                │  │
                                    │  │   └── values-*.yaml            │  │
  DEPENDS ON Block 2                │  │   DEPENDS ON Block 2           │  │
  (needs running stack to test)     │  │   (needs Dockerfiles)          │  │
                                    │  │                                │  │
                                    │  │   ┌────────────────────────────┘  │
     THESE TWO ARE PARALLEL ────────┘  │   │                              │
                                       │   │                              │
                                       ▼   ▼                              │
BLOCK 5: Security Scanning ────────────────────────────────────────────────┤
  (New CI files — Augment Code)                                            │
  ├── Makefile with scan targets                                           ├── DEPENDS ON Block 2
  ├── TruffleHog config                                                    │   (needs Docker images
  └── Trivy scan integration                                               │    to scan)
                                                                           │
BLOCK 6: Scaling Architecture Diagram ─────────────────────────────────────┘
  (Manual — slides/draw.io)                                     DEPENDS ON nothing
  ├── Current → Production → Enterprise                         (can do anytime,
  └── Tradeoff discussion notes                                  best done last
                                                                 when you know
                                                                 what you built)
```

### Critical Path

The critical path is: **Block 1 → Block 2 → Block 3**. If you only finish these three, you have a fully demoable observability stack with live load testing — which is the highest-impact demo for both Gui (Platform & Reliability) and Alex (Technical Deep Dive).

### What Can Run in Parallel

| Parallel Pair | Condition |
|---|---|
| Block 3 (Load Testing) ∥ Block 4 (Kind + Helm) | Both depend on Block 2 being done. Can develop simultaneously if you context-switch, or do them sequentially. |
| Block 5 (Security Scanning) ∥ Block 6 (Architecture Diagram) | Both are independent of Block 3/4. Can be done in any order. |
| Block 6 (Architecture Diagram) ∥ anything | Zero code dependencies. Can sketch during breaks or the night before the interview. |

---

## 4. Block 1: Observability Instrumentation (App Code)

**Tool:** Augment Code (modifying existing files — needs codebase context)
**Estimated Time:** 3-4 hours
**Dependency:** None (first block)
**Fallback if fails:** Core SOC app still works without instrumentation. Present architecture doc as-is.

### What to Build

#### 1a. OpenTelemetry SDK Integration
- Install: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp`
- Auto-instrument FastAPI (all HTTP endpoints get traces automatically)
- Add **custom spans** inside `analyze_threat()` in the coordinator:
  - Parent span: `analyze_threat` (covers entire pipeline)
  - Child spans: one per agent (`historical_agent.analyze`, `config_agent.analyze`, etc.) — these will show as parallel in Jaeger
  - Child spans: `fp_analyzer.analyze`, `response_engine.generate_plan`, `timeline_builder.build` — these show as sequential
- Add span attributes: `threat.type`, `threat.severity`, `customer.name`, `fp.score`
- Configure OTLP exporter pointing to OTel Collector at `localhost:4317`

#### 1b. Prometheus Metrics
- Install: `prometheus-fastapi-instrumentator` (auto HTTP metrics) + `prometheus-client` (custom metrics)
- Auto metrics: request count, latency histogram, in-progress requests (all per-endpoint)
- Custom metrics to add:
  - `soc_threats_processed_total` — Counter, labels: `severity`, `threat_type`
  - `soc_agent_duration_seconds` — Histogram, labels: `agent_name` (shows per-agent latency distribution)
  - `soc_fp_score` — Histogram, no labels (shows distribution of FP scores)
  - `soc_threat_processing_duration_seconds` — Histogram, labels: `phase` (ingestion, agent_execution, fp_analysis, response_planning, timeline, total)
  - `soc_threats_requiring_review_total` — Counter (tracks human escalation rate)
  - `soc_active_websocket_connections` — Gauge (current WS connections)

#### 1c. Structured JSON Logging
- Replace any `print()` statements with Python `logging` using `python-json-logger`
- Log format: `{"timestamp", "level", "message", "trace_id", "span_id", "threat_id", "customer_name", "component"}`
- The `trace_id` field enables correlation: see a spike in Grafana → click through to Jaeger trace → query Loki logs with same trace_id
- Configure log output to stdout (container-friendly — Loki's Docker driver picks it up)

#### 1d. Health Check Endpoints
- `GET /health` — returns `{"status": "healthy", "version": "2.0", "uptime_seconds": N}`. Always returns 200 if process is running. Used for K8s liveness probe.
- `GET /ready` — returns 200 only when the coordinator, all agents, and analyzers are initialized. Used for K8s readiness probe. Returns 503 during startup.

### Verification (Before Moving to Block 2)
- [ ] `python main.py` starts without errors
- [ ] `curl localhost:8000/health` returns 200
- [ ] `curl localhost:8000/ready` returns 200
- [ ] `curl localhost:8000/metrics` returns Prometheus text format with custom metrics
- [ ] Trigger a threat via `POST /api/threats/trigger` → check logs are JSON with trace_id
- [ ] Existing 48+ tests still pass (`./run_tests.sh fast`)

---

## 5. Block 2: Docker Compose Full Stack

**Tool:** Intent (generating new interconnected infrastructure files)
**Estimated Time:** 3-4 hours
**Dependency:** Block 1 (needs /metrics, /health, OTel exports to exist)
**Fallback if fails:** Run app locally as before + describe observability architecture verbally in interview

### What to Build

#### 2a. Dockerfiles

**Backend Dockerfile** (multi-stage):
```dockerfile
# Stage 1: Dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY backend/src/ .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (multi-stage):
```dockerfile
# Stage 1: Build
FROM node:20-slim AS builder
WORKDIR /app
COPY frontend/package*.json .
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

#### 2b. Docker Compose Services

One file: `docker-compose.yml` with the following services:

| Service | Image | Ports | Purpose |
|---|---|---|---|
| `backend` | Build from `./Dockerfile.backend` | 8000 | FastAPI app |
| `frontend` | Build from `./Dockerfile.frontend` | 80 → mapped to 3001 | React dashboard via nginx |
| `otel-collector` | `otel/opentelemetry-collector-contrib` | 4317 (gRPC), 4318 (HTTP) | Receives OTel data, routes to backends |
| `jaeger` | `jaegertracing/all-in-one` | 16686 (UI) | Trace visualization |
| `prometheus` | `prom/prometheus` | 9090 | Metrics storage, scrapes /metrics |
| `loki` | `grafana/loki` | 3100 | Log aggregation |
| `grafana` | `grafana/grafana` | 3000 | Unified dashboards |

#### 2c. Configuration Files to Generate

- `otel-collector-config.yaml` — receives OTLP from app, exports traces to Jaeger, metrics to Prometheus
- `prometheus.yml` — scrape config targeting `backend:8000/metrics` every 15s
- `grafana/provisioning/datasources/datasources.yml` — auto-configures Prometheus, Jaeger, Loki as datasources
- `grafana/provisioning/dashboards/dashboard.yml` — points to JSON dashboard files
- `grafana/dashboards/soc-system-health.json` — Dashboard 1: request rate, latency p50/p95/p99, error rate, active connections
- `grafana/dashboards/soc-agent-performance.json` — Dashboard 2: per-agent latency heatmap, confidence score distribution, parallel execution waterfall
- `grafana/dashboards/soc-business-metrics.json` — Dashboard 3: threats/minute by severity, FP rate trend, human review rate, response action distribution
- `nginx.conf` — reverse proxy config for frontend + API pass-through

#### 2d. Network & Volume Configuration
- Single Docker network: `soc-network` (all services communicate by service name)
- Named volumes: `grafana-data`, `prometheus-data` (persist dashboards across restarts)
- Environment variables via `.env` file (no hardcoded values)

### Verification (Before Moving to Block 3/4)
- [ ] `docker compose build` completes without errors
- [ ] `docker compose up -d` starts all 7 services
- [ ] `docker compose ps` shows all services healthy
- [ ] `localhost:8000/health` returns 200 (backend)
- [ ] `localhost:3001` shows React dashboard (frontend)
- [ ] `localhost:3000` shows Grafana with 3 pre-loaded dashboards
- [ ] `localhost:16686` shows Jaeger UI
- [ ] Trigger a threat → see it appear in dashboard AND see a trace in Jaeger AND see metrics in Grafana
- [ ] `docker compose down && docker compose up -d` — clean restart works

---

## 6. Block 3: Load Testing + Live Observability Demo

**Tool:** Augment Code or Intent (new standalone files — either works)
**Estimated Time:** 2 hours
**Dependency:** Block 2 (needs running Docker Compose stack)
**Fallback if fails:** Manually trigger threats via `test_threats.py` and show Grafana — less dramatic but still works

### What to Build

#### 3a. Locust Load Test File

`loadtests/locustfile.py` with three user classes:

**SteadyStateUser** (weight=5):
- Sends 1 threat every 2-5 seconds
- Random threat type from all 7 types
- Simulates normal SOC operations

**BurstAttackUser** (weight=2):
- Sends credential_stuffing threats in rapid bursts (10 per second for 30 seconds)
- Fixed source IP (simulates single attacker)
- Tests system behavior under spike load

**MixedTrafficUser** (weight=3):
- 60% low-severity (bot_traffic, rate_limit_breach)
- 25% medium-severity (data_scraping, geo_anomaly)
- 15% high/critical (credential_stuffing, account_takeover, brute_force)
- Realistic distribution matching production SOC patterns

#### 3b. Demo Script

`demo/run_demo.sh`:
```bash
#!/bin/bash
echo "=== SOC Agent System — Live Observability Demo ==="
echo ""
echo "Step 1: Verify stack is running..."
curl -s localhost:8000/health | jq .
echo ""
echo "Step 2: Open dashboards in browser..."
open http://localhost:3000   # Grafana
open http://localhost:16686  # Jaeger
open http://localhost:3001   # SOC Dashboard
echo ""
echo "Step 3: Starting load test (2 minutes)..."
echo "        Locust UI: http://localhost:8089"
locust -f loadtests/locustfile.py --host=http://localhost:8000 \
       --users 20 --spawn-rate 5 --run-time 2m --headless &
echo ""
echo "Step 4: Watch Grafana dashboards update in real-time..."
echo "        Press Ctrl+C to stop"
wait
```

#### 3c. Pre-Configured Locust Docker Service (Optional)

Add to `docker-compose.yml`:
```yaml
  locust:
    image: locustio/locust
    ports:
      - "8089:8089"
    volumes:
      - ./loadtests:/mnt/locust
    command: -f /mnt/locust/locustfile.py --host=http://backend:8000
    depends_on:
      - backend
```

### The Interview Demo Flow

This is the sequence you'll walk through live with Alex/Gui:

1. Show Grafana — flat lines, system at rest
2. Start Locust via UI (localhost:8089) — set 20 users, spawn rate 5
3. Switch to Grafana Dashboard 1 (System Health) — watch request rate climb, latency shift
4. Switch to Dashboard 2 (Agent Performance) — show per-agent latency; identify which agent is slowest at P99
5. Switch to Jaeger — find the longest trace → expand → show parallel agent execution as a waterfall
6. Switch to Dashboard 3 (Business Metrics) — show FP rate, severity distribution, review rate
7. Stop Locust — watch metrics return to baseline
8. **Narrate:** *"This is exactly how I'd operate the Endor Labs platform — instrument everything, load test before production, identify bottlenecks from traces not guesswork."*

### Verification
- [ ] `locust -f loadtests/locustfile.py --host=http://localhost:8000 --headless -u 10 -r 2 -t 30s` completes without errors
- [ ] Grafana dashboards show real-time data during load test
- [ ] Jaeger shows traces with parallel agent spans
- [ ] System doesn't crash under 20 concurrent users
- [ ] Demo script runs end-to-end in under 3 minutes

---

## 7. Block 4: Kind + Helm Kubernetes Deployment

**Tool:** Intent (new interconnected file set — Helm chart)
**Estimated Time:** 3 hours
**Dependency:** Block 2 (needs Dockerfiles)
**Fallback if fails:** Docker Compose is the primary demo. Describe K8s deployment plan verbally with the scaling architecture diagram (Block 6).

### What to Build

#### 4a. Kind Cluster Config

`kind-config.yaml`:
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - containerPort: 80
        hostPort: 8080
        protocol: TCP
      - containerPort: 443
        hostPort: 8443
        protocol: TCP
  - role: worker
  - role: worker
```

#### 4b. Helm Chart Structure

```
charts/soc-agent/
├── Chart.yaml
├── values.yaml                    # Default (local/dev) values
├── values-production.yaml         # What production would look like
├── templates/
│   ├── _helpers.tpl               # Template helpers (name, labels)
│   ├── backend-deployment.yaml    # FastAPI deployment
│   ├── backend-service.yaml       # ClusterIP service
│   ├── backend-hpa.yaml           # HorizontalPodAutoscaler
│   ├── backend-configmap.yaml     # Environment config
│   ├── frontend-deployment.yaml   # nginx + React
│   ├── frontend-service.yaml      # ClusterIP service
│   ├── ingress.yaml               # nginx ingress
│   ├── prometheus-config.yaml     # ConfigMap for scrape config
│   └── observability.yaml         # Grafana, Jaeger, Prometheus, Loki pods
└── README.md
```

Key features in the Helm chart:
- **HPA** on backend: scales 2-8 replicas based on CPU > 70%
- **Readiness probe:** `/ready` endpoint, initialDelaySeconds: 10
- **Liveness probe:** `/health` endpoint, periodSeconds: 30
- **Resource requests/limits** defined (shows production awareness)
- **ConfigMap** for all environment variables (no hardcoded values in deployment)
- `values.yaml` vs `values-production.yaml` shows how the same chart adapts

#### 4c. Deploy Script

`deploy.sh`:
```bash
#!/bin/bash
set -e
echo "=== SOC Agent System — K8s Deployment ==="

# Step 1: Create Kind cluster
kind create cluster --config kind-config.yaml --name soc-demo

# Step 2: Load local images into Kind (no registry needed)
docker build -t soc-backend:latest -f Dockerfile.backend .
docker build -t soc-frontend:latest -f Dockerfile.frontend .
kind load docker-image soc-backend:latest --name soc-demo
kind load docker-image soc-frontend:latest --name soc-demo

# Step 3: Install nginx ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s

# Step 4: Install observability stack (community Helm charts)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/prometheus --set server.persistentVolume.enabled=false
helm install grafana grafana/grafana --set persistence.enabled=false --set adminPassword=demo
helm install jaeger jaegertracing/jaeger --set allInOne.enabled=true

# Step 5: Install SOC Agent System
helm install soc-agent ./charts/soc-agent

# Step 6: Wait and verify
kubectl wait --for=condition=ready pod -l app=soc-backend --timeout=120s
echo ""
echo "=== Deployment complete ==="
echo "SOC Dashboard: http://localhost:8080"
echo "Grafana:       kubectl port-forward svc/grafana 3000:80"
echo "Jaeger:        kubectl port-forward svc/jaeger-query 16686:16686"
```

#### 4d. Teardown Script
`teardown.sh`:
```bash
kind delete cluster --name soc-demo
```

### Interview Talking Points for K8s
- *"Same Helm chart deploys to Kind locally, GKE, EKS, or AKS — I just swap values files for the target environment."*
- *"I separated infrastructure provisioning (Terraform for cloud resources) from application deployment (Helm for K8s resources). For this demo, there's no cloud to provision, so Helm is the right and only tool needed."*
- *"The HPA is configured but won't trigger on Kind — I'd demonstrate it by showing the manifest and explaining the production behavior. On a real cluster, I'd use `kubectl top pods` during the Locust test to show CPU climbing toward the scale threshold."*

### Verification
- [ ] `./deploy.sh` completes without errors
- [ ] `kubectl get pods` shows all pods Running
- [ ] `kubectl get hpa` shows the HPA configured
- [ ] `curl localhost:8080/health` returns 200 through ingress
- [ ] `kubectl logs -l app=soc-backend` shows structured JSON logs
- [ ] `./teardown.sh` cleans up completely

---

## 8. Block 5: Security Scanning Pipeline

**Tool:** Augment Code (small new files, CI/security domain)
**Estimated Time:** 1.5 hours
**Dependency:** Block 2 (needs Docker images to scan)
**Fallback if fails:** Skip entirely. Mention the tools verbally in the interview: *"In production I'd add TruffleHog and Trivy to the pipeline."*

### What to Build

#### 5a. Makefile

```makefile
.PHONY: lint test scan-secrets scan-image quality-gate all

lint:
	ruff check backend/src/ --output-format=concise

test:
	cd backend && pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

scan-secrets:
	trufflehog filesystem . --only-verified --fail

scan-image:
	trivy image soc-backend:latest --severity CRITICAL,HIGH --exit-code 1
	trivy image soc-frontend:latest --severity CRITICAL,HIGH --exit-code 1

quality-gate: lint test scan-secrets scan-image
	@echo "✅ All quality gates passed"

all: quality-gate
```

#### 5b. GitHub Actions Workflow (Optional)

`.github/workflows/ci.yml` — runs lint, test, scan-secrets, build images, scan-image on every push. Not required for the demo but shows CI maturity.

#### 5c. Interview Talking Point

Run `make scan-image` live and show the Trivy output:
> *"Even my demo app has dependency vulnerabilities — see these CVEs in the Python base image. Most of these aren't reachable in my code. This is exactly the problem Endor Labs solves: reachability analysis to separate signal from noise. Without it, I'd need to triage all of these manually."*

This is a powerful meta-moment — using the interview demo to validate Endor Labs' own value proposition.

### Verification
- [ ] `make lint` passes
- [ ] `make test` passes with ≥80% coverage
- [ ] `make scan-secrets` runs (may find 0 secrets — that's fine)
- [ ] `make scan-image` runs and produces Trivy output
- [ ] `make quality-gate` runs all steps in sequence

---

## 9. Block 6: Scaling Architecture Diagram

**Tool:** Manual (draw.io, Excalidraw, or slides)
**Estimated Time:** 1 hour
**Dependency:** None (but best done last when you know what you actually built)
**Fallback if fails:** Not applicable — this always works.

### The Diagram

Three columns showing evolution:

```
┌─────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   CURRENT (Demo)    │  │   PRODUCTION         │  │   ENTERPRISE SCALE   │
│                     │  │                      │  │                      │
│ Single Python       │  │ Multi-replica K8s    │  │ Multi-region K8s     │
│ process             │  │ (2-8 pods via HPA)   │  │ (3+ regions)         │
│                     │  │                      │  │                      │
│ In-memory storage   │  │ PostgreSQL + Redis   │  │ TimescaleDB +        │
│                     │  │                      │  │ Redis Cluster        │
│                     │  │                      │  │                      │
│ asyncio.gather      │  │ Temporal/Celery      │  │ Distributed task     │
│ (in-process)        │  │ workers (fault       │  │ queue + event        │
│                     │  │ isolation)           │  │ sourcing             │
│                     │  │                      │  │                      │
│ WebSocket direct    │  │ Redis Pub/Sub        │  │ NATS/Kafka event     │
│                     │  │ fanout               │  │ streaming            │
│                     │  │                      │  │                      │
│ ~10 threats/sec     │  │ ~100-200             │  │ ~1000+               │
│                     │  │ threats/sec          │  │ threats/sec          │
│                     │  │                      │  │                      │
│ Single OTel         │  │ OTel Collector +     │  │ OTel Collector       │
│ Collector           │  │ Managed Grafana      │  │ → vendor backend     │
│ + local Grafana     │  │ Cloud                │  │ (Datadog/Grafana     │
│                     │  │                      │  │ Cloud) + custom      │
│                     │  │                      │  │                      │
│ Statistical FP      │  │ ML model (MLflow     │  │ Per-tenant ML        │
│ scoring             │  │ tracked, shadow      │  │ models, automated    │
│                     │  │ mode, A/B test)      │  │ retraining pipeline  │
└─────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

### Tradeoff Discussion Notes (Prepare for Alex's Questions)

| Question Alex Might Ask | Your Answer |
|---|---|
| *"Why Python and not Go?"* | "For the analysis layer, Python gives access to ML/data science libraries. For the API gateway at scale, I'd consider Go — exactly the pattern Endor Labs uses. I'd extract the coordinator into a Go service that dispatches to Python agent workers." |
| *"How do you handle agent failure?"* | "Currently asyncio.gather fails fast. Production: `return_exceptions=True` + circuit breakers per agent (using `tenacity` or similar). If one agent times out, the others still return results and we degrade gracefully — flag that agent's analysis as unavailable." |
| *"What about the in-memory data store?"* | "Demo only. Production path: PostgreSQL for threat storage (JSONB for flexible schema), Redis for WebSocket pub/sub fanout and caching. I'd use Alembic for migrations. The Timeline events are time-series — TimescaleDB or ClickHouse at enterprise scale." |
| *"How would you do multi-tenancy?"* | "Row-level security in PostgreSQL with tenant_id on every table. Separate Redis keyspaces per tenant. K8s namespace isolation for compute. OTel traces tagged with tenant_id for per-customer observability." |
| *"What about the ML upgrade for FP Analyzer?"* | "Phase 1: current statistical model tracked in MLflow for baseline metrics. Phase 2: train a gradient-boosted model on labeled FP/TP data, deploy in shadow mode alongside the statistical scorer, compare accuracy. Phase 3: promote ML model when it beats statistical baseline by >5%, with automated rollback." |

---

## 10. Fallback Strategy

**Core principle:** Every step you complete leaves you with a demoable system. Here's what happens if things go wrong:

| If This Fails... | You Still Have... | Interview Impact |
|---|---|---|
| Block 1 (Observability code) partially works | Core SOC app running as before + architecture doc | Medium — describe observability plan verbally |
| Block 2 (Docker Compose) doesn't work | Block 1 code running locally in 4 terminals + explain Docker architecture | Medium — less polished but functional |
| Block 3 (Locust) doesn't work | Manual `test_threats.py` + Grafana dashboards with some data | Low — slightly less dramatic demo |
| Block 4 (Kind + Helm) doesn't work | Docker Compose as primary demo + Helm chart as artifact to show | **Zero impact** — Docker Compose is the primary demo |
| Block 5 (Security scanning) doesn't work | Mention tools verbally, show awareness | **Zero impact** — this is bonus content |
| Block 6 (Diagram) doesn't work | Draw on whiteboard during interview | **Zero impact** — always recoverable |

**Key decision point: Sunday evening.** If Blocks 1-3 are working, proceed to Block 4. If Block 1 or 2 is still shaky, skip Block 4 entirely and spend the time hardening Blocks 1-3 + doing Block 6. A **solid Docker Compose demo with live observability beats a fragile K8s demo every time.**

---

## 11. Demo Rehearsal Checklist

**Do this Monday morning before the 9:30 AM interview.**

### Pre-Interview Setup (8:30 AM — 1 hour before)
- [ ] `docker compose down -v` (clean state)
- [ ] `docker compose up -d` (fresh start)
- [ ] Wait 60 seconds for all services to initialize
- [ ] Verify: `curl localhost:8000/health` → 200
- [ ] Verify: `localhost:3000` → Grafana login (admin/admin)
- [ ] Verify: `localhost:16686` → Jaeger UI
- [ ] Verify: `localhost:3001` → SOC Dashboard
- [ ] Trigger 5 manual threats to seed dashboards with some data
- [ ] Open all browser tabs: Grafana (3 dashboards), Jaeger, SOC Dashboard, Locust
- [ ] Have architecture diagram ready (slides or draw.io open)
- [ ] Have terminal ready with `make quality-gate` prepped (Block 5)

### Dry Run (9:00 AM — 30 min before)
- [ ] Walk through the full demo flow once at normal speed
- [ ] Time it — should be under 25 minutes of presentation leaving 15+ min for Q&A with Alex (or 15 min presenting + 15 min Q&A with Gui)
- [ ] Test screen sharing — make sure Zoom shows the right window
- [ ] Test terminal font size — interviewers need to read your output

### If Something Breaks During the Interview
- If Docker Compose is down: `docker compose restart` (30 seconds)
- If Grafana dashboards are blank: trigger a few threats manually, explain the cold-start
- If Locust crashes: use `test_threats.py` instead, explain load testing was via Locust
- If Kind is broken: don't mention it. Demo Docker Compose only.
- **Never debug live on camera.** Say: *"Let me show you the architecture while this restarts"* and switch to the diagram.

---

## 12. AI Tool Prompts — Augment Code

Use these prompts in Augment Code's chat within VS Code. Each prompt targets a specific file modification. Run them sequentially within Block 1.

---

### Prompt 1A: OpenTelemetry SDK Setup

```
I need to add OpenTelemetry distributed tracing to my FastAPI application.

Context: This is a SOC Agent System with a FastAPI backend. The main entry point is in 
backend/src/main.py. The coordinator in the orchestration layer calls 5 analysis agents 
in parallel via asyncio.gather, then sequentially calls the FP Analyzer, Response Engine, 
and Timeline Builder.

Requirements:
1. Create a new file backend/src/telemetry.py that initializes the OTel SDK:
   - TracerProvider with OTLP exporter (endpoint: configurable via OTEL_EXPORTER_OTLP_ENDPOINT 
     env var, default "http://localhost:4317")
   - Service name: "soc-agent-system"
   - Resource attributes: service.version="2.0", deployment.environment=configurable
2. In main.py, add FastAPIInstrumentor to auto-instrument all HTTP endpoints
3. In the coordinator's analyze_threat() function, add:
   - A parent span "analyze_threat" with attributes: threat.type, customer.name, source.ip
   - Individual child spans for each of the 5 parallel agents (they should appear as 
     parallel children in Jaeger)
   - Individual child spans for fp_analyzer.analyze, response_engine.generate_plan, 
     timeline_builder.build (sequential children)
   - On the parent span, set final attributes: threat.severity, fp.score, requires_review
4. Use context propagation so the trace_id flows through the entire pipeline
5. Handle graceful shutdown of the TracerProvider

Required packages to add to requirements.txt:
opentelemetry-api
opentelemetry-sdk  
opentelemetry-instrumentation-fastapi
opentelemetry-exporter-otlp-proto-grpc

Do not break the existing async/await patterns or the parallel agent execution.
```

---

### Prompt 1B: Prometheus Metrics

```
I need to add Prometheus metrics to my FastAPI application that already has OpenTelemetry 
tracing (from the previous change).

Context: The app is a SOC Agent System. The coordinator processes threats through 7 phases 
with 5 parallel agents, then sequential analyzers. Current performance targets are 
500-1000ms end-to-end per threat.

Requirements:
1. Install prometheus-fastapi-instrumentator for automatic HTTP metrics on all endpoints
2. Create a new file backend/src/metrics.py with these custom Prometheus metrics:
   - soc_threats_processed_total (Counter) — labels: severity, threat_type
   - soc_agent_duration_seconds (Histogram) — labels: agent_name 
     — buckets: [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
   - soc_fp_score (Histogram) — no labels — buckets: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
   - soc_threat_processing_duration_seconds (Histogram) — labels: phase 
     — phases: ingestion, agent_execution, fp_analysis, response_planning, timeline, total
   - soc_threats_requiring_review_total (Counter) — no labels
   - soc_active_websocket_connections (Gauge) — no labels
3. Instrument the coordinator's analyze_threat() to record these metrics at each phase
4. Increment the WebSocket gauge on connect, decrement on disconnect
5. Expose metrics at GET /metrics via the instrumentator
6. Add a convenience function get_metrics_summary() that returns current values as a dict 
   (useful for the /health endpoint)

Required packages:
prometheus-fastapi-instrumentator
prometheus-client

Do not duplicate timing logic — reuse the processing_time_ms already tracked by agents 
where possible.
```

---

### Prompt 1C: Structured JSON Logging

```
I need to replace all unstructured logging/print statements in my FastAPI SOC Agent System 
with structured JSON logging that correlates with OpenTelemetry traces.

Requirements:
1. Create backend/src/logger.py with:
   - JSON formatter using python-json-logger
   - Standard fields: timestamp, level, message, logger_name, module
   - OTel correlation fields: trace_id, span_id (extracted from current OTel context)
   - App context fields: threat_id, customer_name, component (passed via logging extra)
2. Replace all print() statements in the codebase with proper logger calls
3. Key log points to ensure exist:
   - INFO: "Threat received" (on API ingestion, with threat_type, customer_name)
   - INFO: "Agent completed" (per agent, with agent_name, confidence, duration_ms)
   - INFO: "FP analysis completed" (with fp_score, recommendation)
   - INFO: "Response plan generated" (with primary_action, sla_minutes)
   - INFO: "Threat analysis completed" (with total_duration_ms, severity, requires_review)
   - WARN: "Agent execution slow" (if any agent exceeds 500ms)
   - ERROR: Any exception in the pipeline (with full stack trace)
4. Configure root logger to output to stdout in JSON format (container-friendly)
5. Set log level via LOG_LEVEL env var (default: INFO)

Required packages:
python-json-logger

These structured logs will be collected by Loki via Docker's log driver and queryable 
in Grafana by trace_id.
```

---

### Prompt 1D: Health Check Endpoints

```
Add health check endpoints to my FastAPI SOC Agent System for Kubernetes readiness 
and liveness probes.

Requirements:
1. GET /health (liveness probe):
   - Always returns 200 if the process is running
   - Response: {"status": "healthy", "version": "2.0", "uptime_seconds": <float>}
   - Should be fast (<5ms) — no heavy checks

2. GET /ready (readiness probe):
   - Returns 200 only when all components are initialized and ready to accept traffic
   - Checks: coordinator initialized, all 5 agents available, analyzers loaded
   - Response (healthy): {"status": "ready", "components": {"coordinator": true, 
     "agents": {"historical": true, "config": true, ...}, "analyzers": {"fp": true, 
     "response": true, "timeline": true}}}
   - Response (not ready): 503 with {"status": "not_ready", "components": {...}} 
     showing which component is false
   - Should complete within 100ms

3. Track application start time for uptime calculation
4. These endpoints should NOT be instrumented with OTel tracing (they're infrastructure, 
   not business logic — exclude from FastAPIInstrumentor)
```

---

### Prompt 1E: Security Scanning Makefile

```
Create a Makefile for my SOC Agent System project that provides development workflow 
commands and security scanning quality gates.

Project structure:
- backend/src/ — Python FastAPI code
- backend/tests/ — pytest test suite (48+ tests)
- frontend/ — React app
- Dockerfile.backend and Dockerfile.frontend exist
- Docker images are named soc-backend:latest and soc-frontend:latest

Requirements:
1. make lint — run ruff on backend/src/
2. make test — run pytest with coverage report, fail if coverage < 80%
3. make scan-secrets — run trufflehog on the filesystem, fail on verified secrets
4. make scan-image — run trivy on both Docker images, fail on CRITICAL severity
5. make quality-gate — run all of the above in sequence, stop on first failure
6. make build — docker compose build
7. make up — docker compose up -d
8. make down — docker compose down -v
9. make demo — build, up, wait for health check, open browser tabs
10. make clean — down + remove images + prune

Include a header comment explaining the available targets.
Tools required: ruff, pytest, trufflehog, trivy, docker, jq, curl.
```

---

## 13. AI Tool Prompts — Intent

Use these specs in Intent's workspace. Each spec generates a self-contained set of related files.

---

### Spec 2A: Docker Compose Observability Stack

```
SPEC: Docker Compose Full Stack for SOC Agent System

GOAL: Create a single docker-compose.yml that runs the SOC Agent System application 
alongside a complete observability stack. Everything must run locally with `docker compose up` 
— no cloud dependencies, no API keys, no external services.

EXISTING CONTEXT:
- Backend: Python FastAPI app on port 8000 with these endpoints:
  - GET /health, GET /ready (health checks)
  - GET /metrics (Prometheus format)
  - POST /api/threats/trigger, GET /api/threats, GET /api/threats/{id}
  - WebSocket /ws
  - OTLP traces exported to gRPC port 4317
  - Structured JSON logs to stdout
- Frontend: React + TailwindCSS app, built with Vite, served by nginx on port 80
- Both have Dockerfiles: Dockerfile.backend and Dockerfile.frontend

FILES TO GENERATE:

1. docker-compose.yml with these services:
   - backend: builds from ./Dockerfile.backend, port 8000, depends on otel-collector, 
     env vars for OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317, 
     OTEL_SERVICE_NAME=soc-agent-system, LOG_LEVEL=INFO
   - frontend: builds from ./Dockerfile.frontend, port 3001:80, depends on backend
   - otel-collector: image otel/opentelemetry-collector-contrib:latest, ports 4317 4318, 
     config from ./infra/otel-collector-config.yaml
   - jaeger: image jaegertracing/all-in-one:latest, port 16686 (UI), receives from 
     otel-collector
   - prometheus: image prom/prometheus:latest, port 9090, config from 
     ./infra/prometheus.yml, scrapes backend:8000/metrics
   - loki: image grafana/loki:latest, port 3100, minimal config
   - grafana: image grafana/grafana:latest, port 3000, provisioning from ./infra/grafana/, 
     anonymous auth enabled (no login for demo), datasources auto-configured
   Network: soc-network (all services on same bridge network)
   Volumes: grafana-data, prometheus-data (named volumes)

2. infra/otel-collector-config.yaml:
   - Receivers: otlp (grpc:4317, http:4318)
   - Processors: batch (timeout 1s, send_batch_size 1024)
   - Exporters: jaeger (endpoint jaeger:14250), prometheus (endpoint 0.0.0.0:8889), 
     logging (loglevel: debug)
   - Service pipelines: traces → otlp receiver → batch → jaeger exporter; 
     metrics → otlp receiver → batch → prometheus exporter

3. infra/prometheus.yml:
   - Global scrape_interval: 15s
   - Scrape configs: 
     - job_name: soc-backend, target: backend:8000, metrics_path: /metrics
     - job_name: otel-collector, target: otel-collector:8889

4. infra/grafana/provisioning/datasources/datasources.yml:
   - Prometheus: url http://prometheus:9090, default true
   - Jaeger: url http://jaeger:16686
   - Loki: url http://loki:3100

5. infra/grafana/provisioning/dashboards/dashboard-provider.yml:
   - Provider pointing to /var/lib/grafana/dashboards/

6. infra/grafana/dashboards/soc-system-health.json:
   Grafana dashboard with panels:
   - Request Rate (requests/sec from prometheus http metrics)
   - Request Latency P50/P95/P99 (histogram quantiles)
   - Error Rate (4xx + 5xx / total)
   - Active WebSocket Connections (soc_active_websocket_connections gauge)
   - Threats Processed per Minute (rate of soc_threats_processed_total)
   Dashboard should auto-refresh every 5 seconds.

7. infra/grafana/dashboards/soc-agent-performance.json:
   Grafana dashboard with panels:
   - Per-Agent Latency Heatmap (soc_agent_duration_seconds by agent_name)
   - Agent Latency P95 Comparison (bar chart of 5 agents)
   - End-to-End Processing Time (soc_threat_processing_duration_seconds with phase=total)
   - Phase Duration Breakdown (stacked bar: ingestion, agent_execution, fp_analysis, 
     response_planning, timeline)
   Dashboard should auto-refresh every 5 seconds.

8. infra/grafana/dashboards/soc-business-metrics.json:
   Grafana dashboard with panels:
   - Threats by Severity (pie chart from soc_threats_processed_total by severity)
   - FP Score Distribution (histogram from soc_fp_score)
   - Human Review Rate (rate of soc_threats_requiring_review_total / soc_threats_processed_total)
   - Threats by Type (bar chart from soc_threats_processed_total by threat_type)
   Dashboard should auto-refresh every 5 seconds.

9. infra/grafana/grafana.ini (or environment variables):
   - Anonymous auth enabled (auth.anonymous enabled=true, org_role=Admin)
   - No login screen for demo purposes
   - Default dashboard: soc-system-health

10. nginx.conf for frontend:
    - Serve static React files from /usr/share/nginx/html
    - Proxy /api/* to backend:8000
    - Proxy /ws to backend:8000 with WebSocket upgrade headers
    - Health check location /nginx-health

CONSTRAINTS:
- All services must be on the same Docker network
- No cloud dependencies — everything runs locally  
- Grafana dashboards must be pre-provisioned (visible on first load, no manual import)
- All configuration via files, not manual UI clicks
- Use specific image tags where possible for reproducibility

VERIFICATION:
After generating, I should be able to run:
  docker compose build && docker compose up -d
Then verify:
  curl localhost:8000/health → 200
  curl localhost:3001 → React app
  curl localhost:3000 → Grafana with 3 dashboards loaded
  curl localhost:16686 → Jaeger UI
```

---

### Spec 2B: Helm Chart for Kubernetes Deployment

```
SPEC: Helm Chart for SOC Agent System — Cloud-Agnostic K8s Deployment

GOAL: Create a Helm chart that deploys the SOC Agent System to any Kubernetes cluster 
(Kind locally, or GKE/EKS/AKS in production). The chart should include the application 
services and reference community Helm charts for the observability stack.

EXISTING CONTEXT:
- Docker images: soc-backend:latest (FastAPI on port 8000), soc-frontend:latest (nginx on port 80)
- Backend has: /health (liveness), /ready (readiness), /metrics (Prometheus)
- Backend env vars: OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME, LOG_LEVEL
- Target: runs on Kind cluster with 1 control plane + 2 worker nodes
- Images are loaded into Kind via `kind load docker-image` (no registry)

FILES TO GENERATE:

1. charts/soc-agent/Chart.yaml:
   - name: soc-agent, version: 1.0.0, appVersion: 2.0.0
   - description: SOC Agent System - Multi-agent threat analysis platform

2. charts/soc-agent/values.yaml (local/dev defaults):
   - backend.replicaCount: 2
   - backend.image.repository: soc-backend, tag: latest, pullPolicy: Never (Kind)
   - backend.resources.requests: cpu 100m, memory 256Mi
   - backend.resources.limits: cpu 500m, memory 512Mi  
   - backend.hpa.enabled: true, minReplicas: 2, maxReplicas: 8, targetCPU: 70
   - backend.env.OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
   - backend.env.LOG_LEVEL: INFO
   - frontend.replicaCount: 1
   - frontend.image.repository: soc-frontend, tag: latest, pullPolicy: Never
   - ingress.enabled: true, className: nginx

3. charts/soc-agent/values-production.yaml (override example):
   - backend.replicaCount: 4
   - backend.image.pullPolicy: Always
   - backend.resources.requests: cpu 500m, memory 1Gi
   - backend.resources.limits: cpu 2, memory 2Gi
   - backend.hpa.maxReplicas: 20
   - ingress.tls.enabled: true

4. charts/soc-agent/templates/_helpers.tpl:
   - Standard Helm helpers: name, fullname, labels, selectorLabels

5. charts/soc-agent/templates/backend-deployment.yaml:
   - Deployment with configurable replicas
   - Liveness probe: httpGet /health, initialDelaySeconds 10, periodSeconds 30
   - Readiness probe: httpGet /ready, initialDelaySeconds 5, periodSeconds 10
   - Resource requests and limits from values
   - Environment variables from ConfigMap
   - Pod anti-affinity (prefer spread across nodes)

6. charts/soc-agent/templates/backend-service.yaml:
   - ClusterIP service, port 8000
   - Selector labels matching deployment

7. charts/soc-agent/templates/backend-hpa.yaml:
   - HorizontalPodAutoscaler v2
   - Conditional on .Values.backend.hpa.enabled
   - Target CPU utilization from values

8. charts/soc-agent/templates/backend-configmap.yaml:
   - All environment variables from .Values.backend.env

9. charts/soc-agent/templates/frontend-deployment.yaml:
   - Single replica nginx deployment
   - Liveness probe on /nginx-health

10. charts/soc-agent/templates/frontend-service.yaml:
    - ClusterIP service, port 80

11. charts/soc-agent/templates/ingress.yaml:
    - nginx Ingress class
    - Route / to frontend, /api/* and /ws to backend
    - Conditional TLS from values

12. kind-config.yaml:
    - 3 nodes: 1 control-plane, 2 workers
    - Port mappings: 80→8080, 443→8443 on control plane
    - Node labels for ingress-ready

13. deploy.sh (executable):
    - Creates Kind cluster from kind-config.yaml
    - Builds and loads Docker images into Kind
    - Installs nginx ingress controller
    - Installs SOC Agent chart via helm install
    - Waits for pods to be ready
    - Prints access URLs with port-forward commands

14. teardown.sh (executable):
    - Deletes Kind cluster
    - Prints confirmation

15. charts/soc-agent/README.md:
    - Quick start instructions
    - Available values documentation
    - Cloud deployment notes (swap pullPolicy, add image registry, enable TLS)

CONSTRAINTS:
- No hardcoded values in templates — everything via values.yaml
- All label selectors must be consistent (use _helpers.tpl)
- Chart must pass `helm lint`
- Cloud-agnostic — no GCP/AWS/Azure specific resources
- Images use pullPolicy: Never for Kind (overridden to Always in production values)
```

---

### Spec 2C: Locust Load Testing Suite

```
SPEC: Locust Load Testing Suite for SOC Agent System

GOAL: Create a load testing suite that generates realistic threat traffic patterns 
to demonstrate the observability stack under load. The tests should be runnable both 
standalone and as a Docker Compose service.

EXISTING CONTEXT:
- Backend API: POST /api/threats/trigger accepts ThreatSignal JSON:
  {
    "threat_type": "credential_stuffing",  // one of 7 types
    "customer_name": "Acme Corp",
    "customer_id": "cust-001",
    "source_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "request_count": 1500,
    "time_window_minutes": 5,
    "detected_at": "2026-02-14T10:00:00Z",
    "raw_data": {}
  }
- Threat types: bot_traffic, credential_stuffing, account_takeover, data_scraping, 
  geo_anomaly, rate_limit_breach, brute_force
- Expected response time: 500-1000ms per threat

FILES TO GENERATE:

1. loadtests/locustfile.py:
   Three user classes with different behavior patterns:

   SteadyStateUser (weight=5):
   - Wait time: 2-5 seconds between requests
   - Random threat type from all 7 types
   - Random customer from pool of 10 demo customers
   - Random source IPs
   - Simulates normal SOC operations

   BurstAttackUser (weight=2):
   - Wait time: 0.1-0.5 seconds (rapid fire)
   - Only credential_stuffing and brute_force types
   - Fixed source IP per user instance (simulates single attacker)
   - High request_count values (5000-50000)
   - Simulates attack spike

   MixedRealisticUser (weight=3):
   - Wait time: 1-3 seconds
   - Weighted distribution: 40% bot_traffic, 20% rate_limit_breach, 
     15% data_scraping, 10% geo_anomaly, 10% credential_stuffing, 
     3% account_takeover, 2% brute_force
   - Matches real-world SOC traffic patterns

   Include helper functions:
   - generate_threat_signal(threat_type) — creates realistic ThreatSignal
   - random_customer() — picks from pool of demo customers
   - random_ip() — generates random but realistic IPs
   - Demo customer pool with names like "Acme Corp", "GlobalBank", "TechStart Inc", etc.

2. loadtests/scenarios/steady_state.py:
   - Configuration for steady-state test: 10 users, spawn rate 2, duration 5 minutes

3. loadtests/scenarios/spike_test.py:
   - Configuration for spike: ramp to 50 users over 30s, hold 2 min, ramp down

4. loadtests/docker-compose.locust.yml:
   - Locust master + 2 workers for distributed load generation
   - Connects to soc-network
   - Master UI on port 8089
   - Volumes mount ./loadtests

5. loadtests/README.md:
   - How to run standalone: locust -f locustfile.py --host=http://localhost:8000
   - How to run via Docker: docker compose -f docker-compose.locust.yml up
   - How to run headless for CI: locust --headless -u 20 -r 5 -t 2m
   - Description of each user class and what it simulates

6. loadtests/verify_loadtest.sh (executable):
   Automated verification script that runs BEFORE handoff to user:

   Step 1: Environment Check
   - Verify backend is running: curl -f http://localhost:8000/health
   - Verify observability stack is up: curl -f http://localhost:9090/-/healthy (Prometheus)
   - Verify Grafana is accessible: curl -f http://localhost:3000/api/health
   - Exit with error if any service is down

   Step 2: API Integration Test
   - Send a single test threat via curl to /api/threats/trigger
   - Verify response is 200 OK
   - Verify response contains expected fields (threat_id, analysis, etc.)
   - Print the response JSON for inspection

   Step 3: Threat Type Validation
   - For each of the 7 threat types, send one test request
   - Verify all return 200 OK (no 400/422 validation errors)
   - Print summary: "✓ All 7 threat types validated"

   Step 4: Locust Dry Run
   - Run: locust -f locustfile.py --host=http://localhost:8000 --headless -u 5 -r 1 -t 30s
   - Capture output and check for:
     * 0% failure rate (all requests succeeded)
     * Average response time < 2000ms
     * No Python exceptions in output
   - Print summary: "✓ Locust dry run: X requests, Y% success, Zms avg response"

   Step 5: Observability Verification
   - Query Prometheus: curl 'http://localhost:9090/api/v1/query?query=soc_threats_processed_total'
   - Verify metric value increased after test
   - Query Jaeger: curl 'http://localhost:16686/api/traces?service=soc-agent-system&limit=1'
   - Verify at least 1 trace exists
   - Print summary: "✓ Metrics and traces are being collected"

   Step 6: Final Report
   - Print green checkmarks for all passed steps
   - Print red X for any failures with remediation hints
   - Exit code 0 if all passed, 1 if any failed

   Example output:
   ```
   ========================================
   LOCUST LOAD TEST VERIFICATION
   ========================================

   [1/6] Environment Check...
   ✓ Backend health: OK (uptime: 123s)
   ✓ Prometheus: OK
   ✓ Grafana: OK

   [2/6] API Integration Test...
   ✓ POST /api/threats/trigger: 200 OK
   ✓ Response contains: threat_id, analysis, fp_score

   [3/6] Threat Type Validation...
   ✓ bot_traffic: 200 OK
   ✓ credential_stuffing: 200 OK
   ✓ account_takeover: 200 OK
   ✓ data_scraping: 200 OK
   ✓ geo_anomaly: 200 OK
   ✓ rate_limit_breach: 200 OK
   ✓ brute_force: 200 OK

   [4/6] Locust Dry Run (5 users, 30s)...
   ✓ Requests: 47 total, 0 failed (100% success)
   ✓ Avg response time: 856ms
   ✓ No exceptions detected

   [5/6] Observability Verification...
   ✓ Prometheus metric soc_threats_processed_total: 54 (increased)
   ✓ Jaeger traces found: 47 traces

   [6/6] Final Report...
   ========================================
   ✅ ALL CHECKS PASSED
   ========================================

   Load testing suite is ready for demo!

   Next steps:
   1. Run full load test: locust -f loadtests/locustfile.py --host=http://localhost:8000
   2. Open Locust UI: http://localhost:8089
   3. Start with 20 users, spawn rate 5
   4. Watch Grafana dashboards update in real-time
   ```

7. demo/run_demo.sh (executable):
   Interactive demo orchestration script:

   ```bash
   #!/bin/bash
   set -e

   echo "=== SOC Agent System — Live Observability Demo ==="
   echo ""
   echo "This demo will:"
   echo "  1. Verify all services are running"
   echo "  2. Open dashboards in your browser"
   echo "  3. Run a 2-minute load test"
   echo "  4. Show real-time observability data"
   echo ""
   read -p "Press Enter to start..."

   echo ""
   echo "[Step 1/4] Verifying stack health..."
   curl -sf http://localhost:8000/health | jq -r '"✓ Backend: \(.status) (uptime: \(.uptime_seconds)s)"'
   curl -sf http://localhost:9090/-/healthy && echo "✓ Prometheus: healthy"
   curl -sf http://localhost:3000/api/health | jq -r '"✓ Grafana: \(.database)"'

   echo ""
   echo "[Step 2/4] Opening dashboards..."
   echo "  → Grafana (metrics): http://localhost:3000"
   echo "  → Jaeger (traces): http://localhost:16686"
   echo "  → SOC Dashboard: http://localhost:5173"
   sleep 2
   open http://localhost:3000/d/soc-dashboard/soc-agent-system || true
   open http://localhost:16686 || true
   open http://localhost:5173 || true

   echo ""
   echo "[Step 3/4] Starting load test..."
   echo "  → Locust UI: http://localhost:8089"
   echo "  → Users: 20, Spawn rate: 5/sec, Duration: 2 minutes"
   echo ""
   echo "💡 DEMO TIP: Switch between Grafana tabs to show:"
   echo "   - Threat processing rate climbing"
   echo "   - Per-agent latency distribution"
   echo "   - FP score heatmap"
   echo "   - Recent logs with clickable trace IDs"
   echo ""

   locust -f loadtests/locustfile.py --host=http://localhost:8000 \
          --headless --users 20 --spawn-rate 5 --run-time 2m \
          --html=loadtest-report.html &

   LOCUST_PID=$!

   echo ""
   echo "[Step 4/4] Load test running... (watch the dashboards!)"
   echo ""
   echo "🎤 NARRATION SCRIPT:"
   echo "   'Notice how the threat processing rate is climbing...'"
   echo "   'Each spike in Jaeger represents a distributed trace across 5 agents...'"
   echo "   'The P99 latency stays under 1 second even at 20 concurrent users...'"
   echo "   'Click any trace_id in the logs to jump directly to Jaeger...'"
   echo "   'This is exactly how I'd monitor Endor Labs platform in production.'"
   echo ""

   wait $LOCUST_PID

   echo ""
   echo "✅ Demo complete! Load test report: loadtest-report.html"
   echo ""
   echo "To run again: ./demo/run_demo.sh"
   ```

CONSTRAINTS:
- All threat signals must pass Pydantic validation (match the ThreatSignal model exactly)
- Customer IDs must be unique per customer name
- Timestamps should use current time (not hardcoded)
- Load test should not crash the backend at 20 concurrent users
- Locust file should work both standalone and in Docker
- verify_loadtest.sh must exit with code 0 only if ALL checks pass
- verify_loadtest.sh should be run automatically by Intent before marking the task complete

VERIFICATION CHECKLIST (Intent should run this before handoff):
- [ ] Run verify_loadtest.sh and confirm all 6 steps pass
- [ ] Check that all 7 threat types return 200 OK (not 422 validation errors)
- [ ] Verify Locust dry run shows 0% failure rate
- [ ] Confirm Prometheus metrics are incrementing
- [ ] Confirm Jaeger traces are being created
- [ ] Test demo/run_demo.sh opens all 3 browser tabs
- [ ] Verify loadtest-report.html is generated after demo run
```

---

*Last updated: February 15, 2026*
*Prepared for Endor Labs Director of Engineering Interview Loop*
