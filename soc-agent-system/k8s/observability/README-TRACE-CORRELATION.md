# Trace Correlation Between Grafana Logs and Jaeger

## Issue

The clickable trace_id links that worked in the Docker Compose Grafana setup don't work in the K8s Grafana deployment due to differences in how Grafana versions handle field links in logs panels.

## Workaround

### Option 1: Manual Navigation

1. **Open Grafana Dashboard**: http://localhost:3000/d/soc-agent-k8s/soc-agent-system-k8s
2. **Scroll to "Recent Logs" panel** at the bottom
3. **Click PAUSE** (⏸) to stop log streaming
4. **Click on any log line** to expand it
5. **Look for the `trace_id` field** in the expanded JSON
6. **Copy the trace_id value** (e.g., `6b253ae9819ff97d83d9a23d518317de`)
7. **Open Jaeger**: http://localhost:16686
8. **Paste the trace_id** in the "Trace ID" search box
9. **Click "Find Traces"**

### Option 2: Use Helper Script

We've created a helper script that demonstrates the correlation:

```bash
cd soc-agent-system/k8s/observability
./test-trace-correlation.sh
```

This script will:
- Trigger a threat analysis request
- Wait for the trace to be exported
- Fetch the most recent trace ID from Jaeger
- Open the trace in Jaeger automatically
- Show you the trace_id to look for in Grafana logs

### Option 3: Search by Service and Time

1. **Open Jaeger**: http://localhost:16686
2. **Select Service**: `soc-agent-system`
3. **Set time range**: Last 5 minutes
4. **Click "Find Traces"**
5. **Browse traces** and correlate with log timestamps in Grafana

## Why This Happened

The Docker Compose setup used an older Grafana version (or different configuration) where the `extractFields` transformation worked seamlessly with field links in logs panels. The K8s deployment uses Grafana 12.3.3 from the kube-prometheus-stack, which handles logs panel field links differently.

## Future Fix

To properly fix this, we would need to either:
1. Use a table visualization instead of logs panel (shows parsed JSON as columns with clickable links)
2. Downgrade Grafana to match the Docker Compose version
3. Use Grafana's data links feature with a different configuration
4. Wait for Grafana to improve logs panel field link support

For the interview demo, **Option 2 (helper script)** is recommended as it provides a clean demonstration of the trace correlation capability.

