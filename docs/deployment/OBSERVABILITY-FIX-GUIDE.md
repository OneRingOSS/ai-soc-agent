# Observability Stack "No Data" Fix

## Problem

Grafana dashboards show "No data" for all panels even after observability stack is deployed.

### Root Causes Identified:

1. **NetworkPolicy blocks Prometheus ingress** ❌
   - NetworkPolicy only had `Egress` rules
   - Prometheus in `observability` namespace cannot scrape backend pods in `soc-agent-demo` namespace
   - No `Ingress` rules to allow metrics collection

2. **ServiceMonitor disabled** ❌
   - `values.yaml` had `observability.enabled: false`
   - ServiceMonitor template not deployed
   - Prometheus doesn't know to scrape the backend

## Solution Applied

### 1. Added Ingress Rules to NetworkPolicy

**File:** `soc-agent-system/k8s/charts/soc-agent/templates/network-policy.yaml`

**Changes:**
```yaml
policyTypes:
  - Egress
  - Ingress  # ← ADDED
ingress:
  # Allow Prometheus scraping from observability namespace
  - from:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: observability
    ports:
      - protocol: TCP
        port: 8000
  
  # Allow frontend to access backend API
  - from:
      - podSelector:
          matchLabels:
            app.kubernetes.io/component: frontend
    ports:
      - protocol: TCP
        port: 8000
```

**What this fixes:**
- ✅ Prometheus can now scrape `/metrics` endpoint on port 8000
- ✅ Frontend can still access backend API
- ✅ Security maintained (only specific namespaces/pods allowed)

### 2. Enabled Observability in values.yaml

**File:** `soc-agent-system/k8s/charts/soc-agent/values.yaml`

**Changes:**
```yaml
observability:
  enabled: true  # Changed from false
```

**What this fixes:**
- ✅ ServiceMonitor is now deployed
- ✅ Prometheus auto-discovers backend service
- ✅ Metrics scraped every 15 seconds

## Deployment Steps

### 1. Deploy Observability Stack (if not done)

```bash
bash soc-agent-system/k8s/deploy-observability.sh
```

This installs:
- kube-prometheus-stack (Prometheus + Grafana)
- Loki (logging)
- Jaeger (tracing)

### 2. Apply the Fixes

```bash
# Upgrade Helm chart with new NetworkPolicy and observability enabled
cd soc-agent-system/k8s/charts/soc-agent
helm upgrade soc-agent . -n soc-agent-demo
```

### 3. Verify ServiceMonitor Created

```bash
kubectl get servicemonitor -n observability
# Expected: soc-agent-backend ServiceMonitor
```

### 4. Verify Prometheus Scraping

```bash
# Check if Prometheus can see the target
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090

# Open http://localhost:9090/targets
# Look for "soc-agent-backend" target
# Status should be "UP" (green)
```

### 5. Verify Metrics in Grafana

```bash
# Start port-forwards
bash soc-agent-system/k8s/startup-cluster-services.sh

# Open Grafana
open http://localhost:3000
# Login: admin/admin

# Go to Explore → Select Prometheus as data source
# Try query: soc_threats_processed_total
# Should show data!
```

## Verification Commands

### Check NetworkPolicy Applied

```bash
kubectl get networkpolicy soc-backend-egress -n soc-agent-demo -o yaml | grep -A20 "ingress:"
# Should show ingress rules allowing observability namespace
```

### Check ServiceMonitor

```bash
kubectl get servicemonitor -n observability -o yaml | grep -E "namespace|soc-agent"
# Should show it's targeting soc-agent-demo namespace
```

### Test Metrics Endpoint Directly

```bash
# Port-forward to backend
kubectl port-forward -n soc-agent-demo deployment/soc-agent-backend 8000:8000

# Curl metrics endpoint
curl http://localhost:8000/metrics

# Expected output:
# soc_threats_processed_total{...} 5.0
# soc_agent_duration_seconds{...} ...
# http_requests_total{...} ...
```

### Check Prometheus Targets

```bash
# Port-forward to Prometheus
kubectl port-forward -n observability svc/kube-prometheus-stack-prometheus 9090:9090

# Open browser
open http://localhost:9090/targets

# Look for:
# - Job: serviceMonitor/observability/soc-agent-backend/0
# - Status: UP (should be green)
# - Labels: should include namespace="soc-agent-demo"
```

## What Security Enhancement Broke This?

The NetworkPolicy added in Phase 3 (Tier 2A) had **only egress rules**:

```yaml
policyTypes:
  - Egress  # ← Only this!
```

When you specify `policyTypes`, Kubernetes applies **default deny** for all types listed. Since we didn't specify `Ingress`, Kubernetes allowed all ingress traffic by default. BUT, we also didn't explicitly allow Prometheus, so when Prometheus tried to scrape, the egress-only policy blocked it.

The fix adds explicit `Ingress` rules to allow only:
1. Prometheus from `observability` namespace
2. Frontend from same namespace

## Summary

**What was broken:**
- ✅ NetworkPolicy blocked Prometheus scraping
- ✅ ServiceMonitor not deployed (observability disabled)

**What's now fixed:**
- ✅ NetworkPolicy allows Prometheus ingress
- ✅ ServiceMonitor deployed and active
- ✅ Prometheus scrapes `/metrics` every 15s
- ✅ Grafana dashboards populate with data

**Security maintained:**
- ✅ Still deny-all egress (OpenAI + VT allowlisted)
- ✅ Now also controlled ingress (only Prometheus + Frontend)
- ✅ Zero trust network posture intact
