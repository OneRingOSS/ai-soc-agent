# AlertManager Demo Guide for Interviews

## Overview
This guide helps you demonstrate AlertManager capabilities for the SOC Agent system during technical interviews.

## Quick Access
- **AlertManager UI**: http://localhost:9093
- **Prometheus Alerts**: http://localhost:9090/alerts
- **Prometheus Rules**: http://localhost:9090/rules
- **Grafana Dashboard**: http://localhost:3000/d/soc-agent-system-overview

---

## What to Show Interviewers

### 1. **Current Active Alerts** (10 alerts firing)

Navigate to http://localhost:9093 and show:

- **Critical Alerts** (2):
  - `etcdInsufficientMembers` - Infrastructure issue
  - Shows AlertManager is actively monitoring the cluster

- **Warning Alerts** (7):
  - `NodeClockNotSynchronising` - Time sync issues
  - `TargetDown` - Some Prometheus targets unreachable
  - `etcdMembersDown` - etcd cluster health
  
- **Info Alerts** (1):
  - `Watchdog` - Proves AlertManager is working (always fires)

**Talking Point**: "These are real alerts from the Kubernetes cluster. In production, we'd route these to PagerDuty for critical alerts and Slack for warnings."

---

### 2. **Custom SOC Agent Alert Rules** (7 rules)

Navigate to http://localhost:9090/rules and filter for "soc-agent":

#### Critical Alerts:
1. **SOCAgentHighErrorRate**
   - **Trigger**: Error rate > 5% for 2 minutes
   - **Use Case**: Detects when the SOC agent is failing to process threats
   - **Action**: Page on-call engineer, check recent deployments
   - **Query**: `(sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))) > 0.05`

2. **SOCAgentBackendDown**
   - **Trigger**: All backend pods down for 1 minute
   - **Use Case**: Complete service outage
   - **Action**: Immediate page, critical incident
   - **Query**: `sum(up{job="soc-agent-backend"}) == 0`

#### Warning Alerts:
3. **SOCAgentHighReviewQueue**
   - **Trigger**: >100 threats requiring manual review for 5 minutes
   - **Use Case**: Analyst workload management
   - **Action**: Assign more analysts, prioritize high-severity threats
   - **Query**: `soc_threats_requiring_review > 100`

4. **SOCAgentHighFalsePositiveRate**
   - **Trigger**: >30% of threats have FP score >0.7 for 10 minutes
   - **Use Case**: ML model quality monitoring
   - **Action**: Review model performance, consider retraining
   - **Query**: `(sum(rate(soc_fp_score_bucket{le="0.7"}[10m])) / sum(rate(soc_fp_score_count[10m]))) > 0.30`

5. **SOCAgentSlowProcessing**
   - **Trigger**: P95 processing time >5 seconds for 5 minutes
   - **Use Case**: Performance degradation detection
   - **Action**: Check resources, scale up if needed
   - **Query**: `histogram_quantile(0.95, sum by (le) (rate(soc_threat_processing_duration_seconds_bucket{phase="total"}[5m]))) > 5`

6. **SOCAgentFrequentRestarts**
   - **Trigger**: Pod restart rate >0.1/min for 5 minutes
   - **Use Case**: Stability issues (OOM, crashes)
   - **Action**: Check pod logs, investigate crash reasons
   - **Query**: `rate(kube_pod_container_status_restarts_total{namespace="soc-agent-demo",pod=~"soc-agent-backend.*"}[15m]) > 0.1`

#### Info Alerts:
7. **SOCAgentHighThreatVolume**
   - **Trigger**: Processing >10 threats/sec for 10 minutes
   - **Use Case**: Anomaly detection, potential security incident
   - **Action**: Monitor for attack campaigns
   - **Query**: `sum(rate(soc_threats_processed_total[5m])) > 10`

---

### 3. **Alert Annotations & Runbooks**

Show how each alert includes:
- **Summary**: Human-readable description
- **Description**: Detailed context with metric values
- **Dashboard**: Direct link to relevant Grafana dashboard
- **Runbook**: Link to remediation procedures (example URLs)
- **Action**: Suggested next steps

**Example** (from SOCAgentHighErrorRate):
```yaml
annotations:
  summary: "SOC Agent experiencing high error rate"
  description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"
  dashboard: "http://localhost:3000/d/soc-agent-system-overview"
  runbook: "https://wiki.company.com/soc-agent/runbooks/high-error-rate"
```

---

### 4. **Alert Routing & Notification Channels**

**Talking Points**:

"In production, we configure AlertManager to route alerts based on severity and component:

```yaml
route:
  group_by: ['alertname', 'component']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
        page: "true"
      receiver: 'pagerduty-critical'
    - match:
        severity: critical
      receiver: 'slack-critical'
    - match:
        severity: warning
      receiver: 'slack-warnings'
    - match:
        team: security-operations
      receiver: 'soc-team-slack'

receivers:
  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<key>'
  - name: 'slack-critical'
    slack_configs:
      - api_url: '<webhook>'
        channel: '#soc-alerts-critical'
  - name: 'slack-warnings'
    slack_configs:
      - api_url: '<webhook>'
        channel: '#soc-alerts'
```

---

### 5. **Alert Silencing & Maintenance Windows**

Navigate to http://localhost:9093/#/silences

**Demo**: "During deployments or maintenance, we can silence specific alerts:
- Silence by alertname, component, or custom labels
- Set expiration time
- Add comments for audit trail
- Prevents alert fatigue during planned changes"

---

## Key Interview Talking Points

### Why This Matters for SOC Operations:

1. **Proactive Threat Detection**
   - Alerts catch issues before they impact security operations
   - ML model quality monitoring ensures accurate threat detection
   - Performance alerts prevent SLA violations

2. **Operational Excellence**
   - Automated alerting reduces MTTR (Mean Time To Resolution)
   - Runbooks ensure consistent incident response
   - Dashboard links provide immediate context

3. **Team Efficiency**
   - Workload alerts (review queue) help balance analyst assignments
   - Severity-based routing ensures right people get right alerts
   - Alert grouping reduces noise and alert fatigue

4. **Business Impact**
   - High error rates could mean missed threats
   - Slow processing delays incident response
   - Backend downtime stops all threat detection

5. **Production-Ready Features**
   - Integration with PagerDuty, Slack, Jira
   - Alert inhibition (suppress lower-severity when critical fires)
   - Silencing for maintenance windows
   - Audit trail for compliance

---

## Demo Flow Suggestion

1. **Start**: Show AlertManager UI with current alerts
2. **Navigate**: Go to Prometheus Rules page, show SOC-specific rules
3. **Deep Dive**: Pick 2-3 alerts, explain the query and business impact
4. **Integration**: Discuss how alerts route to PagerDuty/Slack in production
5. **Runbooks**: Show how annotations link to dashboards and documentation
6. **Wrap Up**: Emphasize how this enables proactive SOC operations

---

## Files Created

- `soc-alert-rules.yaml` - PrometheusRule CRD with 7 custom SOC alerts
- `demo-alertmanager.sh` - Demo script showing alert status
- This guide - Interview talking points

---

## Quick Commands

```bash
# View all alert rules
kubectl get prometheusrules -n observability

# View SOC alert rules
kubectl get prometheusrule soc-agent-alerts -n observability -o yaml

# Check alert status in Prometheus
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name | contains("soc"))'

# Check active alerts in AlertManager
curl -s http://localhost:9093/api/v2/alerts | jq '.[] | {name: .labels.alertname, severity: .labels.severity}'
```

