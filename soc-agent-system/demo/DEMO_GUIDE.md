# SOC Agent System — Demo Guide

Quick reference for running the interview demo.

---

## 🚀 Quick Start

### 1. Start All Services

```bash
# Terminal 1: Start observability stack
cd soc-agent-system/observability
docker compose up -d

# Terminal 2: Start backend
cd soc-agent-system/backend
source venv/bin/activate
./run_with_logging.sh

# Terminal 3: Start frontend (optional)
cd soc-agent-system/frontend
npm run dev
```

### 2. Run the Demo

```bash
cd soc-agent-system/backend
source venv/bin/activate
cd ../demo
./run_demo.sh
```

---

## 📊 Demo Flow

### Step 1: Health Check
- ✅ Backend (localhost:8000)
- ✅ Prometheus (localhost:9090)
- ✅ Grafana (localhost:3000)

### Step 2: Open Dashboards
- **Grafana**: http://localhost:3000 (login: admin/admin)
- **Jaeger**: http://localhost:16686
- **SOC Dashboard**: http://localhost:5173

### Step 2.5: Optional Real API Test
- **Interactive prompt**: "Run real API test? (y/N)"
- **If yes**: Processes 1 threat with real OpenAI API
- **Expected time**: 8-15 seconds
- **Cost**: ~$0.01
- **Shows**: Actual LLM integration and response time
- **Auto-opens**: Jaeger trace for the specific threat ID
- **API key**: Auto-loaded from `backend/.env` if available

### Step 3: Load Test (Mock Mode)
- **Interactive prompt**: "Run mock load test? (y/N)" (if you ran real API test)
- **Users**: 20 concurrent
- **Spawn rate**: 5 users/sec
- **Duration**: 2 minutes
- **Mode**: Mock responses (fast, free)
- **Expected**: ~117ms avg response time, 0% failures
- **Optional**: Can skip if you only want to show real API integration

### Step 4: Report
- **HTML Report**: `demo/loadtest-report.html`
- **CSV Stats**: `demo/loadtest-TIMESTAMP_stats.csv`

---

## 🎤 Narration Script

### Opening
> "This is our SOC Agent System with full observability. We just ran a 2-minute load test with 20 concurrent users generating all 6 threat types: bot traffic, proxy networks, device compromises, anomaly detections, rate limit breaches, and geo anomalies."

### Mock vs Real API
> "**Important**: This demo uses mock responses for speed and cost efficiency. In production with real OpenAI API calls, we'd expect 8-15 second response times per threat due to LLM processing. The architecture supports this through async processing and proper timeout handling."

### Grafana
> "In Grafana, you can see the threat processing rate, agent execution latency, and false positive score distribution — all updating in real-time from Prometheus metrics."

### Jaeger
> "In Jaeger, each threat analysis creates a distributed trace showing the full pipeline: ingestion → 5 parallel agents → FP analysis → response planning → timeline generation."

### SOC Dashboard
> "The SOC Dashboard shows the live threat feed with severity classification, MITRE ATT&CK mapping, and response plans."

### Closing
> "The system is fully integrated with OpenAI's API — I can demonstrate a real example if you'd like to see actual LLM-generated analysis."

---

## 📈 Expected Results

### Mock Mode (Current Demo)
- **Total Requests**: ~1,800-2,000
- **Failures**: 0 (100% success rate)
- **Avg Response Time**: ~117ms
- **P95**: ~130ms
- **P99**: ~160ms
- **Throughput**: ~15 req/s

### Real OpenAI API (Single Test)
- **Response Time**: 8-15 seconds
- **Cost**: ~$0.01 per threat
- **API Calls**: 5 agents + 3 analyzers = 8 calls
- **Shows**: Actual LLM-generated analysis

---

## 🔧 Troubleshooting

### Backend won't start
```bash
cd backend
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install locust
pip install "setuptools>=58.0.0,<70.0.0"
```

### Locust not found
```bash
cd backend
source venv/bin/activate
pip install locust
```

### Real API test fails
- Check `OPENAI_API_KEY` is set correctly
- Verify API key has credits
- Check for rate limits
- Ensure network connectivity

---

## 🎯 Interview Tips

1. **Choose your demo flow**:
   - **Real API only**: Press 'y' for real API, then 'N' for load test (shows actual LLM, faster demo)
   - **Both**: Press 'y' for real API, then 'y' for load test (shows everything, ~3 min total)
   - **Mock only**: Press 'N' for real API (shows scale and performance, ~2 min)

2. **Jaeger navigation**: After real API test, Jaeger automatically opens with the threat trace

3. **Be transparent** - Explain mock vs real performance differences

4. **Show the code** - Be ready to walk through the architecture

5. **Highlight observability** - Metrics, traces, logs all working together

---

## 📝 Key Talking Points

- ✅ **Multi-agent architecture** - 5 specialized agents + 3 analyzers
- ✅ **Full observability** - Metrics (Prometheus), Traces (Jaeger), Logs (Loki)
- ✅ **Production-ready** - 83 tests passing, proper error handling
- ✅ **Scalable** - Async processing, handles high throughput
- ✅ **Real LLM integration** - OpenAI API fully integrated
- ✅ **Performance** - 117ms mock, 8-15s real (explained)

