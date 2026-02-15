# AI-Powered SOC Agent System

> **Production-grade multi-agent threat analysis platform with ML-based false positive detection, automated response orchestration, and comprehensive investigation tracking.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2-blue.svg)](https://reactjs.org/)
[![Tests](https://img.shields.io/badge/Tests-43%20Passing-success.svg)](./backend/tests/)

---

## 🎯 Overview

The **SOC Agent System** is an intelligent security operations platform that leverages multiple specialized AI agents to analyze security threats in real-time. The system provides automated threat detection, false positive scoring, response recommendations, and forensic timeline reconstruction.

### Key Features

✅ **Multi-Agent Architecture** - 5 specialized agents working in parallel for comprehensive threat analysis
✅ **False Positive Detection** - ML-based scoring system to reduce alert fatigue
✅ **Automated Response Planning** - Context-aware action recommendations with SLA tracking
✅ **Investigation Timeline** - Chronological event reconstruction for forensic analysis
✅ **Real-time Dashboard** - WebSocket-powered live threat monitoring with cross-pod broadcasting
✅ **MITRE ATT&CK Mapping** - Automatic threat classification and technique identification
✅ **Production-Ready** - Redis-backed storage, OpenTelemetry tracing, Prometheus metrics, health checks
✅ **Kubernetes-Native** - Multi-pod deployment with HPA, shared state via Redis Pub/Sub
✅ **Full Observability** - Distributed tracing (Jaeger), metrics (Prometheus), logs (Loki) with correlation

---

## 🏗️ Architecture

### Production-Ready Multi-Pod Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                  │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Dashboard  │  │ Threat List  │  │   Filters    │  │   Details    │       │
│  │              │  │ (Real-time)  │  │  (Multi-dim) │  │  (Tabbed)    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                                  │
│  React Components + TailwindCSS + WebSocket Client                              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ WebSocket / REST API
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY LAYER (Multi-Pod)                            │
│                                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐ │
│  │   FastAPI Pod A      │  │   FastAPI Pod B      │  │   FastAPI Pod C      │ │
│  │                      │  │                      │  │                      │ │
│  │  /health  /ready     │  │  /health  /ready     │  │  /health  /ready     │ │
│  │  /metrics            │  │  /metrics            │  │  /metrics            │ │
│  │                      │  │                      │  │                      │ │
│  │  WebSocket Clients:  │  │  WebSocket Clients:  │  │  WebSocket Clients:  │ │
│  │  • User A, D         │  │  • User B, E         │  │  • User C            │ │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘ │
│                                                                                  │
│  Kubernetes Service (Load Balancer) + HorizontalPodAutoscaler                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ Redis Pub/Sub
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SHARED STATE LAYER                                  │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                            Redis (Pub/Sub)                                 │ │
│  │                                                                            │ │
│  │  • threats:events channel (broadcasts to all pods)                        │ │
│  │  • threat:{id} hashes (persistent storage)                                │ │
│  │  • threats:by_created sorted set (ordering)                               │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ All pods process threats
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AGENT PROCESSING LAYER                                 │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                         COORDINATOR AGENT                                  │ │
│  │                      (Enhanced Orchestration)                              │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                         │
│        ┌───────────────────────────────┼───────────────────────────────┐        │
│        │                               │                               │        │
│        ▼                               ▼                               ▼        │
│  ┌─────────────┐              ┌─────────────┐              ┌─────────────┐    │
│  │  5 AGENTS   │              │FP ANALYZER  │              │  RESPONSE   │    │
│  │             │              │             │              │   ENGINE    │    │
│  │ • Historical│              │ • Pattern   │              │             │    │
│  │ • Config    │              │   matching  │              │ • Block IP  │    │
│  │ • DevOps    │              │ • Confidence│              │ • Rate Limit│    │
│  │ • Context   │              │   scoring   │              │ • Whitelist │    │
│  │ • Priority  │              │ • FP history│              │ • Escalate  │    │
│  └─────────────┘              └─────────────┘              └─────────────┘    │
│        │                               │                               │        │
│        └───────────────────────────────┼───────────────────────────────┘        │
│                                        ▼                                         │
│                            ┌───────────────────────┐                            │
│                            │   TIMELINE BUILDER    │                            │
│                            │                       │                            │
│                            │ • Event correlation   │                            │
│                            │ • Chronological view  │                            │
│                            │ • Evidence chain      │                            │
│                            └───────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ Export telemetry
                                        │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          OBSERVABILITY STACK                                     │
│                                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Jaeger     │  │  Prometheus  │  │     Loki     │  │   Grafana    │       │
│  │   (Traces)   │  │   (Metrics)  │  │    (Logs)    │  │ (Dashboards) │       │
│  │              │  │              │  │              │  │              │       │
│  │ :16686       │  │ :9090        │  │ :3100        │  │ :3000        │       │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                                                  │
│  • Distributed tracing with OpenTelemetry                                       │
│  • Custom metrics (threats_total, analysis_duration, websocket_connections)     │
│  • Structured JSON logs with trace_id correlation                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Key Architecture Features:**

🔹 **Horizontal Scalability** - Multiple backend pods with load balancing
🔹 **Shared State** - Redis-backed storage with Pub/Sub for cross-pod communication
🔹 **Real-time Broadcasting** - All WebSocket clients receive all threats regardless of pod
🔹 **Health Checks** - Kubernetes liveness (`/health`) and readiness (`/ready`) probes
🔹 **Auto-scaling** - HorizontalPodAutoscaler based on CPU/memory metrics
🔹 **Full Observability** - Traces, metrics, and logs with bidirectional correlation

### Specialized Agents

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| **Historical Agent** | Pattern recognition | Analyzes past incidents, identifies similar threats, calculates FP rates |
| **Config Agent** | Policy compliance | Validates against customer configurations, rate limits, security policies |
| **DevOps Agent** | Infrastructure correlation | Correlates with deployments, infrastructure changes, platform events |
| **Context Agent** | Business intelligence | Monitors external news, threat intel feeds, industry alerts |
| **Priority Agent** | Threat classification | Assigns severity, maps to MITRE ATT&CK, determines review requirements |

### Enhanced Analyzers

| Analyzer | Purpose | Output |
|----------|---------|--------|
| **False Positive Analyzer** | ML-based FP detection | Score (0-1), confidence, indicators, recommendation |
| **Response Action Engine** | Automated remediation | Primary/secondary actions, escalation path, SLA times |
| **Timeline Builder** | Forensic reconstruction | Chronological events, phase breakdown, audit trail |

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9 - 3.12** (⚠️ Python 3.13+ not yet supported due to pydantic-core compatibility)
- **Node.js 18+**
- **OpenAI API Key** (optional - system works in mock mode without it)

> **Note**: If you have Python 3.13 installed, use Python 3.9, 3.11, or 3.12 instead. Check your version with `python3 --version`.

### Installation

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd soc-agent-system
```

#### 2. Backend Setup

```bash
cd backend

# Check your Python version (must be 3.9-3.12)
python3 --version

# If you have Python 3.13, use a specific version instead:
# python3.12 -m venv venv  # or python3.11 or python3.9

# Create virtual environment with Python 3.9-3.12
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version in virtual environment
python --version  # Should show 3.9.x - 3.12.x

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment (optional)
cp .env.example .env
# Edit .env and add your OpenAI API key (or leave commented for mock mode)

# Run tests
PYTHONPATH=src pytest tests/ -v

# Start backend server
cd src
PYTHONPATH=. uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **⚠️ Troubleshooting**: If you get a `pydantic-core` build error, you're likely using Python 3.13+. Delete the `venv` folder and recreate it with Python 3.9-3.12.

Backend will be available at: **http://localhost:8000**

#### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:5173**

#### 4. Observability Stack (Optional)

For production-grade monitoring with distributed tracing, metrics, and logs:

```bash
cd observability

# Start the full observability stack
docker-compose up -d

# Verify all services are running
docker-compose ps

# Access the dashboards
# Grafana:    http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# Jaeger:     http://localhost:16686
# Loki:       http://localhost:3100
```

**What You Get:**
- 📊 **Grafana Dashboard** - Pre-configured SOC metrics visualization
- 🔍 **Jaeger Tracing** - Distributed traces showing agent execution (9 spans per threat)
- 📈 **Prometheus Metrics** - Custom metrics (threats_total, analysis_duration, etc.)
- 📝 **Loki Logs** - Structured JSON logs with trace_id correlation

**Trace-to-Logs Correlation:**
1. Open Jaeger at http://localhost:16686
2. Find a trace for "analyze_threat"
3. Click "Logs for this span" → Opens Loki with correlated logs
4. Or vice versa: Click trace_id in Loki → Opens Jaeger trace

See **[Observability Stack README](./observability/README.md)** for detailed setup and usage.

---

## 📊 Usage

### Dashboard Features

1. **Real-time Threat Monitoring** - Threats appear automatically via WebSocket
2. **Metric Cards** - Click "Requires Review" to filter threats needing human attention
3. **Threat Details** - Expand any threat to see:
   - False Positive Score with indicators
   - Response Plan with recommended actions
   - Investigation Timeline with chronological events
   - Agent Analyses from all 5 specialized agents
   - MITRE ATT&CK mapping
4. **Manual Triggers** - Use the "🚨 Trigger Critical Threat" button for testing

### API Endpoints

**Core Endpoints:**
- `GET /` - Root health check
- `GET /api/threats` - List all threats (with optional filters)
- `GET /api/threats/{id}` - Get specific threat details
- `POST /api/threats/trigger` - Manually trigger threat analysis
- `WS /ws` - WebSocket for real-time updates (Redis Pub/Sub)

**Kubernetes Health Checks:**
- `GET /health` - Liveness probe (always returns healthy if process alive)
- `GET /ready` - Readiness probe (checks coordinator, agents, analyzers, Redis)

**Observability:**
- `GET /metrics` - Prometheus metrics endpoint (OpenMetrics format)

---

## 🧪 Testing

```bash
cd backend

# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run specific test file
PYTHONPATH=src pytest tests/test_coordinator.py -v

# Run with coverage
PYTHONPATH=src pytest tests/ --cov=src --cov-report=html
```

**Test Coverage**: 43 tests covering all agents, analyzers, and core functionality

---

## 🔥 Load Testing & Demo

For production-grade load testing and interview demonstrations:

```bash
# Run automated verification (14 checks)
./loadtests/verify_loadtest.sh

# Run interactive demo with observability
./demo/run_demo.sh
```

See **[Load Testing Suite](./loadtests/README.md)** for detailed usage, scenarios, and distributed testing options.

---

## 📁 Project Structure

```
soc-agent-system/
├── backend/
│   ├── src/
│   │   ├── agents/           # 5 specialized agents + coordinator
│   │   ├── analyzers/        # FP analyzer, response engine, timeline builder
│   │   ├── models.py         # Pydantic data models
│   │   ├── mock_data.py      # Mock data store
│   │   ├── threat_generator.py
│   │   └── main.py           # FastAPI application
│   ├── tests/                # 43 comprehensive tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── App.jsx           # Main application
│   │   └── App.css           # Styling
│   └── package.json
└── docs/
    ├── SOC_System_Architecture.md    # Complete architecture documentation
    ├── soc-architecture.md           # Mermaid diagrams
    └── SOC_Enhancement_Guide.md      # Enhancement specifications
```

---

## 📖 Documentation

- **[Complete Architecture Documentation](./docs/SOC_System_Architecture.md)** - Comprehensive system architecture, data flow, and component details
- **[Architecture Diagrams](./docs/soc-architecture.md)** - Visual Mermaid diagrams for all system components
- **[Enhancement Guide](./docs/SOC_Enhancement_Guide.md)** - Production-grade feature specifications

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# OpenAI API Configuration (optional - system works in mock mode without it)
OPENAI_API_KEY=your-api-key-here

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### Mock Mode vs Live Mode

- **Mock Mode** (default): No OpenAI API key required, uses simulated AI responses (~100ms per threat)
- **Live Mode**: Requires OpenAI API key, uses real GPT-4o-mini analysis (~10s per threat)

---

## 🎨 Technology Stack

### Backend
- **FastAPI 0.109** - Modern async web framework
- **Pydantic 2.5** - Data validation and serialization
- **OpenAI SDK 1.10** - LLM integration
- **Redis 5.0** - Distributed storage and Pub/Sub
- **Uvicorn** - ASGI server
- **Pytest** - Testing framework (83 tests)

### Frontend
- **React 19.2** - UI framework
- **Vite 7.2** - Build tool with hot reload
- **Chart.js 4.4** - Data visualization
- **Axios** - HTTP client
- **WebSocket API** - Real-time updates

### Observability
- **OpenTelemetry SDK** - Distributed tracing instrumentation
- **Jaeger** - Trace visualization and analysis
- **Prometheus** - Metrics collection and alerting
- **Loki** - Log aggregation and querying
- **Grafana** - Unified dashboards for metrics, traces, and logs
- **python-json-logger** - Structured JSON logging

### Infrastructure
- **Docker** - Multi-stage containerization
- **Kubernetes** - Orchestration with HPA and health checks
- **Helm** - Package management (coming in Block 4)
- **Kind** - Local Kubernetes testing

---

## 🤝 Contributing

This is a demonstration project for technical interviews showcasing production-ready architecture patterns.

**Already Implemented:**
- ✅ Redis-backed distributed storage
- ✅ Prometheus metrics and Grafana dashboards
- ✅ Structured logging with Loki integration
- ✅ OpenTelemetry distributed tracing
- ✅ Kubernetes deployment with health checks
- ✅ Docker multi-stage builds
- ✅ Comprehensive test coverage (83 tests)

**Future Enhancements:**
1. **Authentication** - Add JWT-based auth for API endpoints
2. **Rate Limiting** - Implement API rate limiting with Redis
3. **Database** - Add PostgreSQL for long-term threat storage
4. **RBAC** - Role-based access control for multi-tenant support
5. **Alerting** - Integrate with PagerDuty/Slack for critical threats

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

Built with modern AI/ML technologies to demonstrate production-grade SOC automation capabilities.

**For questions or feedback, please open an issue.**

