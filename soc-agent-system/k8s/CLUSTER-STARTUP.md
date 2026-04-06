# SOC Agent Cluster Startup Guide

**Purpose:** Automatic setup after cluster restart or fresh Helm deployment  
**Time:** 2-3 minutes

---

## 🚀 Quick Start (After Cluster Restart)

Run this one command to start everything:

```bash
bash soc-agent-system/k8s/startup-cluster-services.sh
```

**What it does:**
1. ✅ Waits for all SOC agent pods to be ready
2. ✅ Verifies DEMO_MODE is enabled (for VT enrichment)
3. ✅ Sets up observability port-forwards (Grafana, Prometheus, Loki, Jaeger)
4. ✅ Shows summary of all services

**Expected output:**
```
✅ Pods ready
✅ DEMO_MODE: true (VT enrichment enabled)
✅ Observability port-forwards started
📊 Grafana:    http://localhost:3000
📈 Prometheus: http://localhost:9090
📝 Loki:       http://localhost:3100
🔍 Jaeger:     http://localhost:16686
```

---

## 📋 What's Configured by Default

### 1. DEMO_MODE (VirusTotal Enrichment)

**Configuration:** `soc-agent-system/k8s/charts/soc-agent/values.yaml`

```yaml
backend:
  env:
    DEMO_MODE: "true"  # ✅ Already set
```

**What it does:**
- Seeds 3 malware packages in Redis on startup
- VT enrichment pulls from cache (no API key needed)
- Threats show VirusTotal findings automatically

**Cached packages:**
- `com.kingroot.kinguser` (KingRoot malware)
- `com.noshufou.android.su` (Superuser exploit)
- `com.koushikdutta.superuser` (SuperSU tool)

### 2. FORCE_MOCK_MODE (OpenAI Mock)

**Configuration:** Already in `values.yaml`

```yaml
backend:
  env:
    FORCE_MOCK_MODE: "true"  # ✅ Already set
```

**What it does:**
- Skips OpenAI API calls (no API key needed)
- Uses mock LLM responses
- Demo works without external dependencies

---

## 🔄 Full Startup Sequence

### After Fresh Cluster Creation

```bash
# 1. Create kind cluster (if needed)
kind create cluster --name soc-agent-cluster

# 2. Install Helm chart
cd soc-agent-system/k8s/charts/soc-agent
helm install soc-agent . -n soc-agent-demo --create-namespace

# 3. Run startup script (waits for pods + starts port-forwards)
bash ../../startup-cluster-services.sh
```

### After Cluster Restart

```bash
# Just run the startup script
bash soc-agent-system/k8s/startup-cluster-services.sh
```

### After Helm Upgrade

```bash
# Upgrade Helm release
helm upgrade soc-agent . -n soc-agent-demo

# Run startup script
bash ../../startup-cluster-services.sh
```

---

## 🛠️ Manual Steps (If Script Fails)

### 1. Check Pod Status

```bash
kubectl get pods -n soc-agent-demo
```

**Expected:**
```
NAME                                 READY   STATUS    RESTARTS   AGE
soc-agent-backend-xxx                1/1     Running   0          2m
soc-agent-frontend-xxx               1/1     Running   0          2m
soc-agent-redis-xxx                  1/1     Running   0          2m
```

### 2. Verify DEMO_MODE

```bash
kubectl get configmap soc-agent-backend-config -n soc-agent-demo -o yaml | grep DEMO_MODE
```

**Expected:** `DEMO_MODE: "true"`

**If not set:**
```bash
# values.yaml should already have it - upgrade Helm
cd soc-agent-system/k8s/charts/soc-agent
helm upgrade soc-agent . -n soc-agent-demo
```

### 3. Manually Start Port-Forwards

```bash
# Grafana
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80 &

# Prometheus
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090 &

# Loki
kubectl port-forward -n observability svc/loki 3100:3100 &

# Jaeger
kubectl port-forward -n observability svc/jaeger 16686:16686 &
```

### 4. Verify VT Cache

```bash
kubectl exec -n soc-agent-demo deployment/soc-agent-redis -- redis-cli KEYS "vt:pkg:*"
```

**Expected:** 3 keys (com.kingroot.kinguser, com.noshufou.android.su, com.koushikdutta.superuser)

**If empty:**
- Backend logs should show: "Seeding demo intel data (DEMO_MODE=true)..."
- Restart backend: `kubectl rollout restart deployment/soc-agent-backend -n soc-agent-demo`

---

## 🎯 What Works Automatically

After running the startup script, these features work out of the box:

✅ **VirusTotal Enrichment** - Cached malware data displayed in threats  
✅ **OpenAI Mock Mode** - No API key needed  
✅ **Grafana Dashboards** - Accessible at http://localhost:3000  
✅ **Prometheus Metrics** - Accessible at http://localhost:9090  
✅ **Loki Logs** - Accessible at http://localhost:3100  
✅ **Jaeger Traces** - Accessible at http://localhost:16686  

---

## ⚠️ Common Issues

### Issue 1: "DEMO_MODE not set" warning

**Fix:**
```bash
cd soc-agent-system/k8s/charts/soc-agent
helm upgrade soc-agent . -n soc-agent-demo
kubectl rollout restart deployment/soc-agent-backend -n soc-agent-demo
```

### Issue 2: Port-forwards die

**Fix:**
```bash
bash soc-agent-system/k8s/startup-cluster-services.sh
```

### Issue 3: Pods not ready after 2 minutes

**Debug:**
```bash
kubectl describe pod -n soc-agent-demo -l app=soc-backend
kubectl logs -n soc-agent-demo -l app=soc-backend --tail=50
```

---

## 📝 Summary

**Default Configuration (No Manual Changes Needed):**
- ✅ `DEMO_MODE: "true"` in values.yaml
- ✅ `FORCE_MOCK_MODE: "true"` in values.yaml
- ✅ Startup script handles port-forwards

**After Cluster Restart:**
```bash
# One command does everything:
bash soc-agent-system/k8s/startup-cluster-services.sh
```

**That's it!** Everything works automatically. 🎉
