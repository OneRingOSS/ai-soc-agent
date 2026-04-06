# Observability Stack Deployment Guide

## Problem

The Grafana dashboard shows "No data" for all panels because the observability stack (Prometheus, Grafana, Loki, Jaeger) was never deployed to the cluster.

The `startup-cluster-services.sh` script only starts port-forwards but doesn't deploy the monitoring infrastructure.

## Solution

Use the `deploy-observability.sh` script to install the complete observability stack.

## Deployment

```bash
# One-time deployment (per cluster)
bash soc-agent-system/k8s/deploy-observability.sh
```

This installs:
1. **kube-prometheus-stack** (Prometheus + Grafana)
   - Grafana accessible at http://localhost:3000 (admin/admin)
   - Prometheus accessible at http://localhost:9090
   - ServiceMonitor auto-discovery enabled

2. **Loki** (Log aggregation)
   - Accessible at http://localhost:3100
   - Filesystem storage
   - Single replica for dev/demo

3. **Jaeger** (Distributed tracing)
   - Accessible at http://localhost:16686
   - All-in-one deployment
   - In-memory storage

## After Deployment

Start port-forwards to access services:

```bash
bash soc-agent-system/k8s/startup-cluster-services.sh
```

This creates port-forwards for:
- Grafana (3000)
- Prometheus (9090)
- Loki (3100)
- Jaeger (16686)

## Accessing Dashboards

Once deployed and port-forwards are running:

- **Grafana:** http://localhost:3000
  - Username: `admin`
  - Password: `admin`
  
- **Prometheus:** http://localhost:9090
  
- **Jaeger:** http://localhost:16686

- **Loki:** http://localhost:3100

## Verification

```bash
# Check if observability namespace exists
kubectl get namespace observability

# Check if pods are running
kubectl get pods -n observability

# Expected pods:
# - kube-prometheus-stack-grafana-*
# - kube-prometheus-stack-prometheus-*
# - loki-*
# - jaeger-*
```

## Integration with Post-Cluster-Restart Script

The `post-cluster-restart.sh` script should be updated to call `deploy-observability.sh` if the observability namespace doesn't exist.

## Notes

- The observability stack is deployed in the `observability` namespace
- Grafana dashboards will populate with metrics from the SOC agent backend
- Port-forwards need to be restarted after cluster/pod restarts
- The `startup-cluster-services.sh` script automates port-forward setup
