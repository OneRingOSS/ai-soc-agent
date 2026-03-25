#!/bin/bash
# =============================================================================
# AlertManager Demo Script for SOC Agent System
# =============================================================================
# This script demonstrates AlertManager capabilities for interview demos
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_section() { echo -e "\n${CYAN}=========================================${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}=========================================${NC}\n"; }

log_section "SOC Agent AlertManager Demo"

# Check if AlertManager is accessible
if ! curl -s http://localhost:9093/api/v2/status > /dev/null 2>&1; then
    log_warning "AlertManager is not accessible at http://localhost:9093"
    log_info "Make sure port-forwards are running: bash soc-agent-system/k8s/demo/access_observability.sh"
    exit 1
fi

log_success "AlertManager is accessible"

# Show current alerts
log_section "Current Active Alerts"
curl -s "http://localhost:9093/api/v2/alerts" | python3 << 'PYTHON'
import sys, json
from datetime import datetime

alerts = json.load(sys.stdin)
print(f"Total active alerts: {len(alerts)}\n")

# Group by severity
by_severity = {}
for alert in alerts:
    severity = alert.get('labels', {}).get('severity', 'none')
    by_severity.setdefault(severity, []).append(alert)

# Display by severity
for severity in ['critical', 'warning', 'info', 'none']:
    if severity in by_severity:
        print(f"\n{severity.upper()} ({len(by_severity[severity])} alerts):")
        print("-" * 60)
        for alert in by_severity[severity]:
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            print(f"  • {labels.get('alertname', 'Unknown')}")
            if 'summary' in annotations:
                print(f"    {annotations['summary']}")
            if 'component' in labels:
                print(f"    Component: {labels['component']}")
PYTHON

# Show SOC-specific alert rules
log_section "SOC Agent Custom Alert Rules"
echo "The following custom alerts are configured for the SOC Agent system:"
echo ""
echo "1. 🔴 SOCAgentHighErrorRate (Critical)"
echo "   Triggers when: Error rate > 5% for 2 minutes"
echo "   Action: Check backend logs and recent deployments"
echo ""
echo "2. ⚠️  SOCAgentHighReviewQueue (Warning)"
echo "   Triggers when: >100 threats require manual review for 5 minutes"
echo "   Action: Assign more analysts to review queue"
echo ""
echo "3. ⚠️  SOCAgentHighFalsePositiveRate (Warning)"
echo "   Triggers when: >30% of threats have FP score >0.7 for 10 minutes"
echo "   Action: Review ML model performance, consider retraining"
echo ""
echo "4. ⚠️  SOCAgentSlowProcessing (Warning)"
echo "   Triggers when: P95 processing time >5 seconds for 5 minutes"
echo "   Action: Check system resources, scale up if needed"
echo ""
echo "5. 🔴 SOCAgentBackendDown (Critical)"
echo "   Triggers when: All backend pods are down for 1 minute"
echo "   Action: Immediate page to on-call engineer"
echo ""
echo "6. ⚠️  SOCAgentFrequentRestarts (Warning)"
echo "   Triggers when: Pod restart rate >0.1/min for 5 minutes"
echo "   Action: Check pod logs for crash reasons"
echo ""
echo "7. ℹ️  SOCAgentHighThreatVolume (Info)"
echo "   Triggers when: Processing >10 threats/sec for 10 minutes"
echo "   Action: Monitor for potential security incident"
echo ""

# Check if SOC alerts are loaded
log_section "Checking SOC Alert Rules Status"
curl -s "http://localhost:9090/api/v1/rules" | python3 << 'PYTHON'
import sys, json

data = json.load(sys.stdin)
groups = data.get('data', {}).get('groups', [])

soc_groups = [g for g in groups if 'soc' in g.get('name', '').lower()]

if soc_groups:
    print(f"✓ Found {len(soc_groups)} SOC-related rule group(s):\n")
    for group in soc_groups:
        print(f"  • {group['name']}: {len(group['rules'])} rules")
        for rule in group['rules']:
            if rule['type'] == 'alerting':
                print(f"    - {rule['name']} ({rule.get('labels', {}).get('severity', 'N/A')})")
else:
    print("⚠ No SOC-specific alert rules found")
    print("  Run: kubectl apply -f soc-agent-system/k8s/observability/soc-alert-rules.yaml")
PYTHON

echo ""
log_section "Demo Talking Points for Interviewers"
echo "1. ALERT HIERARCHY"
echo "   • Critical alerts page on-call engineers immediately"
echo "   • Warning alerts notify team via Slack/email"
echo "   • Info alerts are logged for trend analysis"
echo ""
echo "2. SOC-SPECIFIC METRICS"
echo "   • Monitor threat processing performance (latency, throughput)"
echo "   • Track ML model quality (false positive rates)"
echo "   • Alert on analyst workload (review queue depth)"
echo ""
echo "3. INTEGRATION POINTS"
echo "   • AlertManager → PagerDuty for critical alerts"
echo "   • AlertManager → Slack for team notifications"
echo "   • AlertManager → Jira for ticket creation"
echo "   • AlertManager → Webhook for custom integrations"
echo ""
echo "4. ALERT ROUTING & SILENCING"
echo "   • Route alerts by severity, component, or team"
echo "   • Silence alerts during maintenance windows"
echo "   • Group related alerts to reduce noise"
echo "   • Inhibit lower-severity alerts when critical ones fire"
echo ""
echo "5. RUNBOOK AUTOMATION"
echo "   • Each alert includes runbook URL in annotations"
echo "   • Alerts link directly to relevant dashboards"
echo "   • Suggested remediation actions in alert description"
echo ""

log_section "Quick Access Links"
echo "📊 AlertManager UI:  http://localhost:9093"
echo "📈 Grafana Dashboard: http://localhost:3000/d/soc-agent-system-overview"
echo "🔍 Prometheus Rules:  http://localhost:9090/rules"
echo "🎯 Prometheus Alerts: http://localhost:9090/alerts"
echo ""

log_success "Demo script complete!"
echo ""

