#!/bin/bash
# Import K8s-aware SOC Dashboard to Grafana
# This script modifies the existing dashboard to aggregate metrics properly

set -e

# Wait for Grafana to be accessible
echo "Waiting for Grafana..."
until curl -s http://localhost:3000/api/health > /dev/null 2>&1; do
    echo "Grafana not ready, waiting..."
    sleep 2
done

echo "Grafana is ready!"

# Add Loki datasource
echo "Adding Loki datasource..."
curl -s -X POST http://admin:admin1234@localhost:3000/api/datasources \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Loki",
    "type": "loki",
    "uid": "loki",
    "access": "proxy",
    "url": "http://loki.observability.svc.cluster.local:3100",
    "basicAuth": false,
    "isDefault": false,
    "jsonData": {
      "maxLines": 1000
    }
  }' > /dev/null 2>&1 || echo "Loki datasource may already exist"

echo "Loki datasource configured!"

# Get the existing dashboard
DASHBOARD_FILE="../../observability/grafana/dashboards/soc-dashboard.json"

# Create a modified version with:
# 1. Pod variable filter
# 2. Aggregated queries (sum by endpoint/method, not by pod)
# 3. Separate panel showing per-pod breakdown

cat > /tmp/soc-k8s-dashboard.json << 'DASHBOARD_EOF'
{
  "annotations": {"list": []},
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 1,
  "id": null,
  "links": [],
  "templating": {
    "list": [
      {
        "current": {"selected": true, "text": "All", "value": "$__all"},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "definition": "label_values(http_requests_total, pod)",
        "hide": 0,
        "includeAll": true,
        "label": "Pod",
        "multi": true,
        "name": "pod",
        "options": [],
        "query": {"query": "label_values(http_requests_total, pod)", "refId": "VariableQuery"},
        "refresh": 1,
        "regex": "",
        "skipUrlSync": false,
        "sort": 1,
        "type": "query",
        "allValue": ".*"
      }
    ]
  },
  "panels": [
    {
      "title": "HTTP Request Rate (Total)",
      "description": "Total HTTP requests per second across selected pods, aggregated by endpoint.",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
      "id": 1,
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "custom": {
            "axisBorderShow": false,
            "axisCenteredZero": false,
            "axisLabel": "req/sec",
            "drawStyle": "line",
            "fillOpacity": 10,
            "lineWidth": 2,
            "pointSize": 5,
            "showPoints": "auto",
            "spanNulls": false,
            "stacking": {"group": "A", "mode": "normal"}
          },
          "unit": "reqps"
        },
        "overrides": []
      },
      "options": {
        "legend": {"calcs": ["mean", "max"], "displayMode": "table", "placement": "bottom"},
        "tooltip": {"mode": "multi", "sort": "desc"}
      },
      "targets": [
        {
          "datasource": {"type": "prometheus", "uid": "prometheus"},
          "expr": "sum by (method, handler) (rate(http_requests_total{pod=~\"$pod\"}[5m]))",
          "legendFormat": "{{method}} {{handler}}",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Active WebSocket Connections",
      "description": "Total active WebSocket connections across all selected pods.",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 12, "y": 0},
      "id": 2,
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "green", "value": null},
              {"color": "yellow", "value": 10},
              {"color": "red", "value": 50}
            ]
          },
          "unit": "short"
        },
        "overrides": []
      },
      "options": {
        "colorMode": "background",
        "graphMode": "area",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "targets": [
        {
          "datasource": {"type": "prometheus", "uid": "prometheus"},
          "expr": "sum(soc_active_websocket_connections{pod=~\"$pod\"})",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Active Pods",
      "description": "Number of healthy backend pods.",
      "type": "stat",
      "gridPos": {"h": 4, "w": 4, "x": 16, "y": 0},
      "id": 3,
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "thresholds"},
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {"color": "red", "value": null},
              {"color": "yellow", "value": 1},
              {"color": "green", "value": 2}
            ]
          },
          "unit": "short"
        },
        "overrides": []
      },
      "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "auto",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": false},
        "textMode": "auto"
      },
      "targets": [
        {
          "datasource": {"type": "prometheus", "uid": "prometheus"},
          "expr": "count(count by (pod) (http_requests_total{pod=~\"$pod\"}))",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Request Rate by Pod",
      "description": "HTTP requests per second broken down by pod (only visible when specific pods selected).",
      "type": "timeseries",
      "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
      "id": 4,
      "datasource": {"type": "prometheus", "uid": "prometheus"},
      "fieldConfig": {
        "defaults": {
          "color": {"mode": "palette-classic"},
          "custom": {
            "axisBorderShow": false,
            "axisCenteredZero": false,
            "axisLabel": "req/sec",
            "drawStyle": "line",
            "fillOpacity": 10,
            "lineWidth": 2,
            "pointSize": 5,
            "showPoints": "auto",
            "spanNulls": false,
            "stacking": {"group": "A", "mode": "none"}
          },
          "unit": "reqps"
        },
        "overrides": []
      },
      "options": {
        "legend": {"calcs": ["mean", "max"], "displayMode": "table", "placement": "bottom"},
        "tooltip": {"mode": "multi", "sort": "desc"}
      },
      "targets": [
        {
          "datasource": {"type": "prometheus", "uid": "prometheus"},
          "expr": "sum by (pod) (rate(http_requests_total{pod=~\"$pod\"}[5m]))",
          "legendFormat": "{{pod}}",
          "refId": "A"
        }
      ]
    },
    {
      "title": "Recent Logs",
      "description": "Live log stream from SOC Agent backend pods",
      "type": "logs",
      "gridPos": {"h": 10, "w": 24, "x": 0, "y": 24},
      "id": 5,
      "datasource": {"type": "loki", "uid": "loki"},
      "options": {
        "dedupStrategy": "none",
        "enableLogDetails": true,
        "prettifyLogMessage": false,
        "showCommonLabels": false,
        "showLabels": false,
        "showTime": true,
        "sortOrder": "Descending",
        "wrapLogMessage": false
      },
      "targets": [
        {
          "datasource": {"type": "loki", "uid": "loki"},
          "expr": "{namespace=\"soc-agent-test\"}",
          "refId": "A"
        }
      ]
    }
  ],
  "schemaVersion": 39,
  "tags": ["soc", "security", "kubernetes"],
  "title": "SOC Agent System - K8s",
  "uid": "soc-agent-k8s",
  "version": 1,
  "refresh": "30s",
  "time": {
    "from": "now-15m",
    "to": "now"
  },
  "timepicker": {}
}
DASHBOARD_EOF

echo "Importing dashboard to Grafana..."
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -u admin:admin1234 \
  http://localhost:3000/api/dashboards/db \
  -d "{\"dashboard\": $(cat /tmp/soc-k8s-dashboard.json), \"overwrite\": true}")

echo "$RESPONSE" | jq -r '.status, .url'

if echo "$RESPONSE" | jq -e '.status == "success"' > /dev/null; then
    echo "✓ Dashboard imported successfully!"
    DASHBOARD_URL=$(echo "$RESPONSE" | jq -r '.url')
    echo "  Dashboard URL: http://localhost:3000${DASHBOARD_URL}"
else
    echo "✗ Failed to import dashboard"
    echo "$RESPONSE" | jq .
    exit 1
fi

