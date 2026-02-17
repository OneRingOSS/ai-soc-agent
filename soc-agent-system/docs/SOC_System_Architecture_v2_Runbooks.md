# SOC Agent System – Architecture v2: Runbooks
## Operational Playbooks for DevOps, SecOps, and Analysts

**Version:** 2.0
**Last Updated:** February 16, 2026
**Status:** Enterprise Architecture Blueprint

---

## Table of Contents

1. [Runbook Philosophy](#1-runbook-philosophy)
2. [DevOps Runbook](#2-devops-runbook)
   - 2.1 [Service Health Check](#21-service-health-check)
   - 2.2 [Error Spike Investigation](#22-error-spike-investigation)
   - 2.3 [Release Deployment](#23-release-deployment)
   - 2.4 [Release Rollback](#24-release-rollback)
   - 2.5 [Scaling Operations](#25-scaling-operations)
   - 2.6 [Database Operations](#26-database-operations)
   - 2.7 [Redis Operations](#27-redis-operations)
   - 2.8 [Disaster Recovery](#28-disaster-recovery)
3. [SecOps Runbook](#3-secops-runbook)
   - 3.1 [Critical Incident Triage](#31-critical-incident-triage)
   - 3.2 [False Positive Spike Investigation](#32-false-positive-spike-investigation)
   - 3.3 [Playbook & Rule Tuning](#33-playbook--rule-tuning)
   - 3.4 [Forensic Investigation & Export](#34-forensic-investigation--export)
   - 3.5 [Security Incident in the SOC Platform Itself](#35-security-incident-in-the-soc-platform-itself)
4. [Analyst Runbook](#4-analyst-runbook)
   - 4.1 [Daily Triage Workflow](#41-daily-triage-workflow)
   - 4.2 [Investigation Procedure](#42-investigation-procedure)
   - 4.3 [Customer Communication](#43-customer-communication)
   - 4.4 [Escalation Procedures](#44-escalation-procedures)
   - 4.5 [Shift Handoff](#45-shift-handoff)

---

## 1. Runbook Philosophy

### Principles

- **Every runbook starts with observability.** Before taking action, verify the problem using dashboards, traces, and logs.
- **Automate the diagnosis, human-approve the action.** Use scripts to gather data; require human sign-off for destructive operations.
- **Document as you go.** Every incident response creates or updates a runbook entry.
- **Test runbooks quarterly.** DR drills, game days, and tabletop exercises keep runbooks current.

### Severity Definitions

| Severity | Definition | Response SLA | Examples |
|----------|-----------|-------------|---------|
| **SEV1 — Critical** | System is down or data integrity at risk | 15 min acknowledge, 1 hr mitigate | All pods crashing, DB corruption, security breach |
| **SEV2 — High** | Major feature broken, significant user impact | 30 min acknowledge, 4 hr mitigate | Agent pipeline failures, WebSocket broadcasting down |
| **SEV3 — Medium** | Degraded performance, partial functionality | 2 hr acknowledge, 24 hr resolve | Elevated latency, one agent failing, FP rate spike |
| **SEV4 — Low** | Minor issue, workaround available | 24 hr acknowledge, 1 week resolve | UI cosmetic issue, non-critical log warnings |

### Tool Prerequisites

All runbooks assume access to:
- `kubectl` configured for the target cluster.
- Grafana dashboards (System Health, Agent Performance, Business Metrics).
- Jaeger/Tempo for distributed tracing.
- Loki for log queries (or vendor equivalent).
- PagerDuty/Opsgenie for on-call management.
- Helm CLI for release management.

---

## 2. DevOps Runbook

### 2.1 Service Health Check

**When to use:** Routine check, start of on-call shift, or as first step of any incident.

**Steps:**

1. **Check Kubernetes cluster health:**
```bash
# All pods running?
kubectl get pods -n soc-system --sort-by='.metadata.creationTimestamp'

# Any restarts?
kubectl get pods -n soc-system -o custom-columns=\
  NAME:.metadata.name,\
  RESTARTS:.status.containerStatuses[0].restartCount,\
  STATUS:.status.phase

# HPA status
kubectl get hpa -n soc-system

# Node health
kubectl top nodes
kubectl top pods -n soc-system --sort-by=cpu
```

2. **Check application health endpoints:**
```bash
# Backend liveness
curl -s http://<ingress>/health | jq .

# Backend readiness (includes component checks)
curl -s http://<ingress>/ready | jq .

# Expected output:
# {
#   "status": "ready",
#   "components": {
#     "coordinator": true,
#     "agents": {"historical": true, "config": true, "devops": true, "context": true, "priority": true},
#     "analyzers": {"fp": true, "response": true, "timeline": true},
#     "redis": true,
#     "database": true  <-- v2: PostgreSQL health
#   }
# }
```

3. **Check Grafana dashboards:**
   - **System Health:** Error rate <1%, P95 latency <1s, no pod restarts.
   - **Agent Performance:** All 5 agents responding, no timeouts.
   - **Business Metrics:** Threat processing rate consistent with baseline.

4. **Check dependent services:**
```bash
# Redis
kubectl exec -it deploy/redis -n soc-system -- redis-cli ping

# PostgreSQL (v2)
kubectl exec -it deploy/soc-backend -n soc-system -- python -c \
  "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"
```

**Healthy state checklist:**
- [ ] All pods Running, 0 restarts in last hour
- [ ] `/health` returns 200 on all pods
- [ ] `/ready` returns 200 with all components true
- [ ] Grafana dashboards show normal ranges
- [ ] Redis PING returns PONG
- [ ] PostgreSQL connection succeeds

---

### 2.2 Error Spike Investigation

**When to use:** Grafana alert fires for error rate >5% or PagerDuty incident created.

**Steps:**

1. **Identify the scope:**
```bash
# Which pods are affected?
kubectl get pods -n soc-system | grep -v Running

# Recent events
kubectl get events -n soc-system --sort-by='.lastTimestamp' | tail -20
```

2. **Check error rate by endpoint (Grafana or PromQL):**
```promql
# Error rate by endpoint
sum by (handler)(rate(http_request_duration_seconds_count{status=~"5.."}[5m]))
/
sum by (handler)(rate(http_request_duration_seconds_count[5m]))
```

3. **Find correlated errors in logs (Loki):**
```logql
{namespace="soc-system", app="soc-backend"} |= "ERROR" | json | line_format "{{.timestamp}} {{.trace_id}} {{.message}}"
```

4. **Drill into a failing trace (Jaeger):**
   - Filter by: service=soc-agent-system, status=error, last 15 minutes.
   - Find the root span with the error.
   - Check span attributes for: `threat.type`, `agent_name`, `error.message`.

5. **Common failure patterns and fixes:**

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All endpoints 503 | Pods not ready | Check `/ready` — which component is false? Restart the failing component. |
| POST /api/threats/trigger timeout | Agent hanging | Check per-agent latency in Grafana. Kill stuck pod: `kubectl delete pod <name>`. |
| Redis connection refused | Redis pod crashed or OOM | `kubectl describe pod redis` → check memory. Scale up Redis resources. |
| PostgreSQL connection pool exhausted | Too many connections | Check `pg_stat_activity`. Add PgBouncer or increase `max_connections`. |
| OTel Collector dropping spans | Collector resource limit | Scale collector replicas or increase batch size/timeout. |
| WebSocket disconnections | Pod scaling event | Expected during HPA scale-down. Clients auto-reconnect via Redis Pub/Sub. |

6. **Escalation:** If root cause not identified within 30 minutes, escalate to SEV2 and page the on-call engineer.

---

### 2.3 Release Deployment

**When to use:** Deploying a new version to staging or production.

**Pre-deployment checklist:**
- [ ] All CI pipeline stages passed (lint, test, scan, build)
- [ ] Staging E2E tests passed
- [ ] Changelog reviewed and approved
- [ ] Database migration tested on staging (if applicable)
- [ ] Rollback plan documented

**Steps:**

1. **Update image tag in Helm values:**
```bash
# For staging
helm upgrade soc-agent ./charts/soc-agent \
  -n soc-system \
  -f values.yaml \
  -f values-staging.yaml \
  --set backend.image.tag=v2.1.0 \
  --set frontend.image.tag=v2.1.0
```

2. **Monitor rollout:**
```bash
# Watch deployment progress
kubectl rollout status deployment/soc-backend -n soc-system --timeout=300s

# Verify new pods are healthy
kubectl get pods -n soc-system -l app=soc-backend -o wide

# Check health endpoint on new pods
kubectl port-forward svc/soc-backend 8000:8000 -n soc-system
curl -s localhost:8000/health | jq .
curl -s localhost:8000/ready | jq .
```

3. **Post-deployment verification:**
```bash
# Run smoke tests
./tests/e2e/test_docker_compose.sh  # (adapted for staging URL)

# Verify metrics flowing
curl -s http://<ingress>/metrics | head -20

# Trigger a test threat and verify end-to-end
curl -s -X POST http://<ingress>/api/threats/trigger \
  -H "Content-Type: application/json" \
  -d '{"threat_type":"bot_traffic","customer_name":"DeployTest","customer_id":"deploy-001","source_ip":"10.0.0.1","request_count":100,"time_window_minutes":5}' | jq .id
```

4. **For production — canary deployment (if using Argo Rollouts):**
```yaml
# Canary strategy in Argo Rollout
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: {duration: 5m}     # 10% traffic for 5 min
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency-p95
        - setWeight: 50
        - pause: {duration: 10m}    # 50% traffic for 10 min
        - analysis:
            templates:
              - templateName: success-rate
              - templateName: latency-p95
        - setWeight: 100            # Full rollout
```

---

### 2.4 Release Rollback

**When to use:** Post-deployment issues detected (error spike, performance regression, functional failure).

**Steps:**

1. **Immediate rollback via Helm:**
```bash
# List releases
helm history soc-agent -n soc-system

# Rollback to previous revision
helm rollback soc-agent <previous_revision> -n soc-system

# Verify rollback
kubectl rollout status deployment/soc-backend -n soc-system
kubectl get pods -n soc-system -l app=soc-backend
```

2. **If database migration was applied:**
```bash
# Run down migration BEFORE rolling back application
alembic downgrade -1

# Then rollback Helm release
helm rollback soc-agent <previous_revision> -n soc-system
```

3. **Post-rollback verification:**
   - Run health checks (Section 2.1).
   - Run E2E tests.
   - Verify error rate returned to baseline in Grafana.
   - Notify team in Slack with rollback reason.

4. **Post-mortem:** Schedule within 48 hours. Document root cause and prevention.

---

### 2.5 Scaling Operations

**Horizontal scaling (application):**
```bash
# Manual scale (override HPA temporarily)
kubectl scale deployment/soc-backend -n soc-system --replicas=6

# Adjust HPA limits
helm upgrade soc-agent ./charts/soc-agent \
  -n soc-system \
  --set backend.hpa.minReplicas=4 \
  --set backend.hpa.maxReplicas=20 \
  --set backend.hpa.targetCPU=60

# Monitor scaling
kubectl get hpa -n soc-system -w
```

**Vertical scaling (database):**
```bash
# AWS RDS
aws rds modify-db-instance \
  --db-instance-identifier soc-postgres \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately

# GCP Cloud SQL
gcloud sql instances patch soc-postgres \
  --tier=db-custom-8-32768 \
  --region=us-west1
```

**Redis scaling:**
```bash
# Scale Redis replica count (if using Redis Cluster)
kubectl scale statefulset/redis -n soc-system --replicas=3

# Or upgrade ElastiCache / Memorystore instance type via Terraform
```

---

### 2.6 Database Operations

**Check connection pool health:**
```sql
-- Active connections by state
SELECT state, count(*) FROM pg_stat_activity WHERE datname = 'soc' GROUP BY state;

-- Long-running queries (>30s)
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle' AND (now() - pg_stat_activity.query_start) > interval '30 seconds'
ORDER BY duration DESC;

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
```

**Run migration:**
```bash
# Test on staging first
alembic upgrade head --sql  # Preview SQL
alembic upgrade head        # Apply

# Verify
alembic current
```

**Backup & restore:**
```bash
# Manual backup (in addition to automated PITR)
pg_dump -h <host> -U soc_admin -d soc -Fc -f soc_backup_$(date +%Y%m%d).dump

# Restore to test environment
pg_restore -h <test_host> -U soc_admin -d soc_test -Fc soc_backup_20260216.dump
```

---

### 2.7 Redis Operations

**Health check:**
```bash
redis-cli -h <redis_host> info memory
redis-cli -h <redis_host> info clients
redis-cli -h <redis_host> info stats
```

**Monitor Pub/Sub:**
```bash
# Watch all Pub/Sub messages (debug only — generates high output)
redis-cli -h <redis_host> MONITOR | grep PUBLISH

# Check subscriber count on threats channel
redis-cli -h <redis_host> PUBSUB NUMSUB threats:events
```

**Flush stale data (caution):**
```bash
# Count threat keys
redis-cli -h <redis_host> KEYS "threat:*" | wc -l

# Remove threats older than 7 days (use scan, not keys, in production)
# This should be automated via TTL or background job
```

---

### 2.8 Disaster Recovery

**Scenario: Primary region failure**

1. Verify failure is region-wide (not just a service issue).
2. Promote read replica in secondary region:
   ```bash
   # AWS
   aws rds promote-read-replica --db-instance-identifier soc-postgres-replica

   # GCP
   gcloud sql instances promote-replica soc-postgres-replica
   ```
3. Update DNS to point to secondary region's load balancer.
4. Verify application connectivity to promoted DB.
5. Scale up secondary K8s cluster to handle full traffic.
6. Notify all stakeholders via incident channel.

**Scenario: Database corruption**

1. Stop all writes immediately: scale backend to 0 replicas.
2. Identify corruption scope from logs and audit trail.
3. Restore from PITR to the last known-good timestamp:
   ```bash
   # AWS: restore to point-in-time
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier soc-postgres \
     --target-db-instance-identifier soc-postgres-restored \
     --restore-time "2026-02-16T21:00:00Z"
   ```
4. Validate restored data integrity.
5. Swap application to use restored instance.
6. Scale backend back up and verify.

---

## 3. SecOps Runbook

### 3.1 Critical Incident Triage

**Trigger:** PagerDuty alert for a critical-severity threat, or manual escalation from Analyst.

**Steps:**

1. **Acknowledge** the PagerDuty incident within 15 minutes.
2. **Open the SOC Dashboard** → filter for the critical incident.
3. **Review the analysis:**
   - Read executive summary (LLM-generated in v2).
   - Check FP score and indicators — is this likely real?
   - Review all 5 agent analyses for consensus.
   - Check investigation timeline for the sequence of events.
4. **Validate the recommended response:**
   - Review the ResponsePlan's primary and secondary actions.
   - Cross-check with customer config (auto-block enabled? whitelist conflicts?).
   - If auto-executable and confidence >0.8: approve auto-execution.
   - If requires_approval: manually approve or modify.
5. **Execute response:**
   - From the UI: click "Execute Primary Action" (if integrated with WAF/firewall).
   - Or manually: apply the block/rate-limit via the customer's security tooling.
6. **Document:**
   - Add analyst comment explaining decision rationale.
   - Update incident status: `analyzing` → `escalated` or `resolved`.
7. **Communicate:**
   - Notify customer via established channel (email, Slack, ticket).
   - Use customer narrative (auto-generated) as starting point.

---

### 3.2 False Positive Spike Investigation

**Trigger:** Grafana alert for FP rate exceeding baseline by >20%, or analyst reports unusual FP volume.

**Steps:**

1. **Quantify the spike:**
   - Grafana → Business Metrics dashboard → FP Score Distribution panel.
   - PromQL: `increase(soc_threats_requiring_review_total[1h])` vs previous day.

2. **Identify affected threat types:**
```promql
# FP rate by threat type (last 1 hour)
sum by (threat_type)(rate(soc_threats_processed_total{fp_recommendation="likely_false_positive"}[1h]))
/
sum by (threat_type)(rate(soc_threats_processed_total[1h]))
```

3. **Root cause analysis:**
   - **New deployment?** Check if FP spike correlates with a release. → Rollback if confirmed.
   - **New customer traffic pattern?** Check specific customers with high FP rates. → Update customer config.
   - **External event?** Check External Context Agent for new threat intel feeds. → May need to update feed weights.
   - **Model drift?** If ML model is in production, check MLflow metrics. → Retrain or rollback model.

4. **Remediation:**
   - Update FP Analyzer thresholds if baseline rates changed.
   - Add customer-specific whitelists or rules.
   - If systemic: open a bug/story for the next sprint.

---

### 3.3 Playbook & Rule Tuning

**When to use:** Quarterly review, or after repeated incidents of the same type.

**Steps:**

1. **Pull metrics:**
   - What percentage of ResponsePlan recommendations were overridden by analysts?
   - Which action types have the highest override rate?
   - Which threat types have the longest time-to-resolution?

2. **Identify tuning opportunities:**
   - If analysts consistently downgrade `block_ip` to `rate_limit` for a threat type → update template.
   - If FP rate for a customer exceeds 50% → add customer-specific rules.
   - If SLA breaches are common for a severity level → adjust auto-escalation timing.

3. **Test changes:**
   - Apply rule changes in staging.
   - Replay historical threats through updated rules.
   - Compare outcomes with actual analyst decisions.

4. **Deploy:**
   - Rule changes go through the same CI/CD pipeline as code changes.
   - Feature flag new rules for gradual rollout.

---

### 3.4 Forensic Investigation & Export

**When to use:** Customer requests investigation report, compliance audit, or legal hold.

**Steps:**

1. **Gather evidence:**
   - Incident detail from SOC Dashboard (all tabs: overview, agents, timeline, actions).
   - Distributed trace from Jaeger showing full processing pipeline.
   - Relevant logs from Loki (filtered by trace_id).
   - Audit log entries for the incident (who viewed, modified, acted).

2. **Generate report:**
   - Use investigation timeline as the chronological backbone.
   - Add agent analysis summaries.
   - Include FP score reasoning.
   - Attach ResponsePlan and actual actions taken.
   - Redact PII as required by tenant's data classification policy.

3. **Export:**
   - JSON export via API: `GET /api/threats/{id}/export?format=json&redact_pii=true`
   - PDF export via UI: "Export Investigation Report" button.
   - Store export in object storage with retention tag matching compliance requirements.

4. **Chain of custody:**
   - Record export event in audit log.
   - Hash the exported file and store hash in audit log.
   - Maintain access log for who downloaded the report.

---

### 3.5 Security Incident in the SOC Platform Itself

**When to use:** The SOC platform itself is under attack or compromised.

**Steps:**

1. **Isolate:**
   - If external breach: remove public ingress immediately.
   - If internal: revoke compromised credentials, rotate API keys.

2. **Assess:**
   - Check audit log for unauthorized access.
   - Review K8s audit logs for unexpected API calls.
   - Check Falco alerts for anomalous container behavior.

3. **Contain:**
   - Rotate all secrets (DB passwords, Redis auth, API keys, JWT signing keys).
   - Force-expire all active sessions.
   - Re-deploy from known-good image tags.

4. **Notify:**
   - Internal security team immediately.
   - Affected customers per contractual SLA.
   - Regulators if PII was exposed (GDPR 72-hour window).

5. **Post-mortem:**
   - Full incident timeline.
   - Root cause analysis.
   - Preventive measures.
   - Update this runbook.

---

## 4. Analyst Runbook

### 4.1 Daily Triage Workflow

**Start of shift:**

1. Open SOC Dashboard.
2. Review shift handoff notes from previous shift.
3. Filter for **"Needs Review"** threats, sorted by:
   - Severity (Critical → High → Medium → Low).
   - SLA remaining (closest to breach first).
4. Claim incidents by assigning to yourself.
5. Process each incident using the Investigation Procedure (Section 4.2).

**End of shift:**
- Update all claimed incidents with current status.
- Write shift handoff (Section 4.5).

---

### 4.2 Investigation Procedure

For each incident assigned to you:

1. **Read the executive summary** (auto-generated).
   - Does it make sense? Flag inaccuracies.

2. **Check FP score and indicators:**
   - Score >0.7: Likely FP. Verify indicators, then resolve as FP if confirmed.
   - Score 0.4–0.7: Needs deeper investigation. Proceed to step 3.
   - Score <0.4: Likely real. Proceed with urgency appropriate to severity.

3. **Review agent analyses (all 5):**
   - **Historical:** Are there similar past incidents? What were they resolved as?
   - **Config:** Is the customer's config unusual (very high rate limits, auto-block disabled)?
   - **DevOps:** Was there a recent deployment that might explain the traffic pattern?
   - **Context:** Are there external threat advisories matching this pattern?
   - **Priority:** Does the MITRE mapping make sense for this threat type?

4. **Review investigation timeline:**
   - Does the sequence of events tell a coherent story?
   - Are there gaps or anomalies in timing?

5. **Review recommended response:**
   - Is the primary action appropriate?
   - Should it be escalated or downgraded based on your analysis?

6. **Make a decision:**
   - **True Positive:** Execute or approve the response plan. Document reasoning.
   - **False Positive:** Resolve as FP. Add comment explaining why. Update FP rules if applicable.
   - **Needs Escalation:** Escalate to Tier 2 / SOC Manager with summary of findings.

7. **Update incident:**
   - Set status: `resolved`, `false_positive`, or `escalated`.
   - Add analyst comment with decision rationale.
   - Close or reassign.

---

### 4.3 Customer Communication

**When to communicate:**
- All Critical incidents: always.
- High incidents: when action is taken affecting the customer.
- Medium/Low: only if customer-initiated or contractually required.

**Communication template:**

```
Subject: [SOC-{id}] {severity} Security Incident — {threat_type}

Dear {customer_name} team,

Our SOC detected a {severity} {threat_type} event affecting your environment.

Summary:
{customer_narrative}  ← auto-generated by LLM/template

Actions Taken:
{primary_action.action_type}: {primary_action.reason}

Current Status: {status}

Next Steps:
{next_steps}

Please contact us if you have questions or need to modify the response.

Best regards,
SOC Team
```

---

### 4.4 Escalation Procedures

| From | To | When | How |
|------|-----|------|-----|
| Analyst T1 | Analyst T2 | Unfamiliar threat type, complex investigation | Reassign in dashboard + Slack message |
| Analyst T2 | SOC Manager | Customer-impacting action needed, policy question | Reassign + PagerDuty escalation |
| SOC Manager | CISO / Security Lead | Data breach, regulatory notification needed | Phone + email + PagerDuty |
| Any | DevOps | Platform issue affecting SOC operations | PagerDuty + Slack #soc-platform channel |

---

### 4.5 Shift Handoff

**Format (posted in Slack #soc-handoff):**

```
## Shift Handoff — {date} {shift}
**Analyst:** {name}

### Open Critical/High Incidents
- SOC-{id}: {brief description} — Status: {status}, Assigned: {analyst}
- SOC-{id}: {brief description} — Status: {status}, Assigned: {analyst}

### Key Events This Shift
- {time}: {event description}
- {time}: {event description}

### FP Rate Status
- Current: {rate}% (baseline: {baseline}%)
- Notable: {any FP spikes or anomalies}

### Pending Actions
- {action needed and who should take it}

### Notes for Next Shift
- {anything the next analyst needs to know}
```

---

*This document covers Section 4 of the SOC Agent System Architecture v2.*
*See also:*
- *`SOC_System_Architecture_v2_Core.md` — Sections 1–3 (Architecture, Enterprise, Cloud)*
- *`SOC_System_Architecture_v2_Operations.md` — Sections 5–6 (CI/CD, Security Scanning)*
