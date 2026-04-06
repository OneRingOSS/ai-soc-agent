# Observability Stack Access

**Status:** ✅ Running  
**Namespace:** `observability`  
**Last Updated:** April 5, 2026

---

## 🚀 Quick Start

### Access the Observability Stack

```bash
# Run the access script (sets up all port forwards)
bash soc-agent-system/k8s/access-observability.sh
```

**Or manually start port forwards:**
```bash
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 &
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 &
kubectl port-forward -n observability svc/loki 3100:3100 &
kubectl port-forward -n observability svc/jaeger 16686:16686 &
```

---

## 📊 Access URLs

### Grafana (Dashboards & Visualization)
- **URL:** http://localhost:3000
- **Username:** `admin`
- **Password:** `prom-operator`
- **Purpose:** Pre-built Kubernetes dashboards, custom dashboards, log exploration

### Prometheus (Metrics)
- **URL:** http://localhost:9090
- **Purpose:** Query metrics, view targets, alerts

### Loki (Logs)
- **URL:** http://localhost:3100
- **Purpose:** Log aggregation API (query via Grafana)

### Jaeger (Distributed Tracing)
- **URL:** http://localhost:16686
- **Purpose:** Distributed tracing, request flow visualization

---

## 📈 Pre-Configured Grafana Dashboards

Once logged into Grafana (http://localhost:3000):

### Kubernetes Dashboards
1. **Compute Resources / Cluster**
   - Navigate: Dashboards → Kubernetes → Compute Resources → Cluster
   - Shows: CPU, memory, network usage cluster-wide

2. **Compute Resources / Namespace (Pods)**
   - Navigate: Dashboards → Kubernetes → Compute Resources → Namespace (Pods)
   - Filter by namespace: `soc-agent-demo`
   - Shows: Pod-level resource usage

3. **Persistent Volumes**
   - Navigate: Dashboards → Kubernetes → Persistent Volumes
   - Shows: Volume usage, I/O

### Log Exploration
1. **Loki Logs**
   - Navigate: Explore → Data source: Loki
   - Query: `{namespace="soc-agent-demo"}`
   - Shows: Real-time logs from SOC agent pods

### Tracing
1. **Jaeger UI**
   - Open: http://localhost:16686
   - Service: `soc-agent-backend`
   - Shows: Request traces, latency

---

## 🔍 Useful Queries

### Prometheus Queries

**Pod CPU Usage:**
```promql
rate(container_cpu_usage_seconds_total{namespace="soc-agent-demo"}[5m])
```

**Pod Memory Usage:**
```promql
container_memory_working_set_bytes{namespace="soc-agent-demo"}
```

**Request Rate:**
```promql
rate(http_requests_total{namespace="soc-agent-demo"}[5m])
```

### Loki Queries

**All logs from soc-agent-demo:**
```logql
{namespace="soc-agent-demo"}
```

**Error logs only:**
```logql
{namespace="soc-agent-demo"} |= "error"
```

**Backend logs:**
```logql
{namespace="soc-agent-demo", app="soc-backend"}
```

---

## 🛠️ Troubleshooting

### Port Already in Use

```bash
# Kill existing port forwards
pkill -f "kubectl port-forward.*observability"

# Or kill specific port
lsof -ti:3000 | xargs kill -9
```

### Port Forward Died

```bash
# Check if port forwards are running
ps aux | grep "kubectl port-forward" | grep observability

# Restart all
bash soc-agent-system/k8s/access-observability.sh
```

### Observability Stack Not Running

```bash
# Check pods in observability namespace
kubectl get pods -n observability

# If not installed, install with:
# (This requires the kube-prometheus-stack Helm chart)
```

---

## 📊 Current Status

**Port Forwards Active:**
```bash
✅ Grafana:    http://localhost:3000  (PID: 98149)
✅ Prometheus: http://localhost:9090  (PID: 98171)
✅ Loki:       http://localhost:3100  (PID: 98172)
✅ Jaeger:     http://localhost:16686 (PID: 98173)
```

**All services accessible!** 🎉

---

## 🎯 For Demo

### Show Metrics Dashboard
1. Open Grafana: http://localhost:3000
2. Login: `admin` / `prom-operator`
3. Navigate: Dashboards → Kubernetes → Compute Resources → Namespace (Pods)
4. Select namespace: `soc-agent-demo`
5. Show: Real-time resource usage of SOC agent

### Show Logs
1. In Grafana: Explore → Loki
2. Query: `{namespace="soc-agent-demo", app="soc-backend"}`
3. Show: Live backend logs

### Show Traces
1. Open Jaeger: http://localhost:16686
2. Service: `soc-agent-backend`
3. Show: Request flow through agents

---

## 📝 Notes

- Port forwards run in background and persist until killed
- Grafana credentials are default (change for production)
- All data is stored in-cluster (ephemeral for demo)
- For production: Configure persistent storage for Prometheus/Loki

---

**Observability stack is ready to use!** 🚀
