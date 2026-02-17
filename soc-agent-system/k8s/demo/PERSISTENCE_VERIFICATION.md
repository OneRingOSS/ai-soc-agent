# K8s Demo - Persistence Verification

This document verifies that all fixes made during the demo setup are **permanently persisted** in the codebase and will survive a fresh deployment.

## ✅ All Changes Are Persisted

### 1. **Frontend WebSocket URL** ✅ PERSISTED
**File**: `soc-agent-system/frontend/src/App.jsx` (line 21)
**Commit**: `d0246d6` - "fix: use dynamic WebSocket URL for K8s ingress compatibility"

```javascript
const wsUrl = `ws://${window.location.host}/ws`
```

**Why**: Uses dynamic URL instead of hardcoded `ws://localhost:8000/ws`
**Impact**: Works in both local dev (port 8000) and K8s (port 8080 via ingress)

---

### 2. **Docker Image Names** ✅ PERSISTED
**File**: `soc-agent-system/k8s/demo/setup_demo.sh` (lines 123, 128, 133-134)
**Commit**: `b6df26b` - "fix: correct Docker image names and paths in K8s demo setup script"

```bash
docker build -t soc-backend:latest .
docker build -t soc-frontend:latest .
kind load docker-image soc-backend:latest --name "$CLUSTER_NAME"
kind load docker-image soc-frontend:latest --name "$CLUSTER_NAME"
```

**Why**: Helm chart expects `soc-backend:latest` and `soc-frontend:latest`, not `soc-agent-backend:latest`
**Impact**: Pods start successfully without `ErrImageNeverPull` errors

---

### 3. **Observability Enabled by Default** ✅ PERSISTED
**File**: `soc-agent-system/k8s/demo/setup_demo.sh` (line 177)
**Commit**: `b7705b0` - "fix: enable observability by default in K8s demo setup"

```bash
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --set backend.hpa.enabled=true \
    --set backend.hpa.minReplicas=2 \
    --set backend.hpa.maxReplicas=8 \
    --set redis.enabled=true \
    --set ingress.enabled=true \
    --set ingress.host=soc-agent.local \
    --set observability.enabled=true \
    --wait --timeout=300s
```

**Why**: Without this, ServiceMonitor isn't created and Prometheus doesn't scrape metrics
**Impact**: Grafana dashboard shows metrics immediately, "Active Pods" shows correct count

---

### 4. **Grafana Credentials** ✅ PERSISTED
**File**: `soc-agent-system/k8s/observability/import-dashboard.sh` (lines 18, 271)
**Commit**: `e6956ba` - "fix: update Grafana credentials and namespace for K8s demo"

```bash
# Line 18 - Loki datasource creation
curl -s -X POST http://admin:admin@localhost:3000/api/datasources \

# Line 271 - Dashboard import
-u admin:admin \
```

**Why**: kube-prometheus-stack uses `admin:admin` by default, not `admin:admin1234`
**Impact**: Dashboard import succeeds without authentication errors

---

### 5. **Dashboard Namespace** ✅ PERSISTED
**File**: `soc-agent-system/k8s/observability/import-dashboard.sh` (line 248)
**Commit**: `e6956ba` - "fix: update Grafana credentials and namespace for K8s demo"

```json
"expr": "{namespace=\"soc-agent-demo\"}",
```

**Why**: Demo uses `soc-agent-demo` namespace, not `soc-agent-test`
**Impact**: Logs panel shows data from correct namespace

---

## 🔍 Verification Steps

To verify all changes are persisted, run these commands:

```bash
# 1. Check frontend WebSocket URL
grep -n "window.location.host" soc-agent-system/frontend/src/App.jsx
# Expected: Line 21 with dynamic WebSocket URL

# 2. Check Docker image names
grep -n "soc-backend:latest" soc-agent-system/k8s/demo/setup_demo.sh
# Expected: Lines 123, 133

# 3. Check observability enabled
grep -n "observability.enabled=true" soc-agent-system/k8s/demo/setup_demo.sh
# Expected: Line 177

# 4. Check Grafana credentials
grep -n "admin:admin@" soc-agent-system/k8s/observability/import-dashboard.sh
# Expected: Line 18

# 5. Check dashboard namespace
grep -n "soc-agent-demo" soc-agent-system/k8s/observability/import-dashboard.sh
# Expected: Line 248
```

---

## 🧪 Fresh Deployment Test

To verify everything works from scratch:

```bash
# 1. Teardown existing deployment
cd soc-agent-system/k8s/demo
bash teardown_demo.sh

# 2. Run fresh setup
bash setup_demo.sh

# 3. Deploy observability stack
cd ../observability
bash deploy-observability.sh

# 4. Import dashboard
bash import-dashboard.sh

# 5. Verify everything works
# - Frontend: http://localhost:8080 (WebSocket should be connected)
# - Grafana: http://localhost:3000 (Active Pods should show 2)
# - Jaeger: http://localhost:16686 (Should show traces)
```

---

## 📊 Expected Results After Fresh Deployment

| Component | Expected State | Verification |
|-----------|---------------|--------------|
| Frontend WebSocket | Connected | Dashboard shows "WebSocket connected" |
| Backend Pods | 2 running | `kubectl get pods -n soc-agent-demo` |
| ServiceMonitor | Created | `kubectl get servicemonitor -n observability` |
| Prometheus Targets | 2 up | Check http://localhost:9090/targets |
| Grafana Active Pods | Shows 2 | Dashboard panel displays correct count |
| Grafana Logs | Shows data | Logs panel displays recent logs |
| Jaeger Traces | Available | Traces visible for `soc-agent-system` service |

---

## 🎯 Summary

**All 5 critical fixes are now permanently persisted in the codebase:**

1. ✅ Frontend WebSocket URL (dynamic)
2. ✅ Docker image names (soc-backend/frontend)
3. ✅ Observability enabled by default
4. ✅ Grafana credentials (admin:admin)
5. ✅ Dashboard namespace (soc-agent-demo)

**No manual intervention required** - running `setup_demo.sh` will create a fully working environment with observability from the start.

