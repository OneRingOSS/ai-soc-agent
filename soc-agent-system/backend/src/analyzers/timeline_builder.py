"""Investigation Timeline Builder - Creates chronological event timeline."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

from models import (
    ThreatSignal, InvestigationTimeline, TimelineEvent, TimelineEventType,
    ThreatSeverity, AgentAnalysis, FalsePositiveScore, ResponsePlan
)

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Builds investigation timelines for threat analysis."""

    def __init__(self):
        """Initialize timeline builder."""
        self.events: List[TimelineEvent] = []
        self.start_time: Optional[datetime] = None

    def build_timeline(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis],
        fp_score: Optional[FalsePositiveScore],
        response_plan: Optional[ResponsePlan],
        severity: ThreatSeverity
    ) -> InvestigationTimeline:
        """
        Build complete investigation timeline.

        Args:
            signal: Original threat signal
            agent_analyses: Results from all agents
            fp_score: False positive analysis
            response_plan: Generated response plan
            severity: Assessed severity

        Returns:
            Complete InvestigationTimeline
        """
        logger.info("📅 Building investigation timeline...")

        self.events = []
        self.start_time = signal.timestamp

        # 1. Detection event
        self._add_detection_event(signal)

        # 2. Enrichment events (data gathering)
        self._add_enrichment_events(signal)

        # 3. Agent analysis events
        self._add_agent_analysis_events(agent_analyses)

        # 4. FP analysis event
        if fp_score:
            self._add_fp_analysis_event(fp_score)

        # 5. Correlation events
        self._add_correlation_events(signal, agent_analyses)

        # 6. Decision event (severity determination)
        self._add_decision_event(severity, fp_score)

        # 7. Response action events
        if response_plan:
            self._add_response_events(response_plan)

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - self.start_time).total_seconds() * 1000)

        timeline = InvestigationTimeline(
            events=sorted(self.events, key=lambda e: e.timestamp),
            start_time=self.start_time,
            end_time=end_time,
            duration_ms=duration_ms
        )

        logger.info(f"   Timeline built with {len(self.events)} events")

        return timeline

    def _add_detection_event(self, signal: ThreatSignal):
        """Add initial detection event."""
        self.events.append(TimelineEvent(
            timestamp=signal.timestamp,
            event_type=TimelineEventType.DETECTION,
            title="Threat Detected",
            description=f"{signal.threat_type.value.replace('_', ' ').title()} detected from {signal.metadata.get('source_ip', 'unknown')}",
            source="Detection Engine",
            data={
                "threat_type": signal.threat_type.value,
                "source_ip": signal.metadata.get("source_ip", "unknown"),
                "customer": signal.customer_name,
                "request_count": signal.metadata.get("request_count", 0),
            },
            severity=ThreatSeverity.INFO
        ))

    def _add_enrichment_events(self, signal: ThreatSignal):
        """Add data enrichment events."""
        base_time = signal.timestamp + timedelta(milliseconds=50)

        # Historical data lookup
        self.events.append(TimelineEvent(
            timestamp=base_time,
            event_type=TimelineEventType.ENRICHMENT,
            title="Historical Data Retrieved",
            description="Queried incident database for similar past events",
            source="Historical Database",
            data={"query_type": "similar_incidents", "time_range": "90 days"}
        ))

        # Customer config lookup
        self.events.append(TimelineEvent(
            timestamp=base_time + timedelta(milliseconds=20),
            event_type=TimelineEventType.ENRICHMENT,
            title="Customer Configuration Loaded",
            description=f"Retrieved security settings for {signal.customer_name}",
            source="Config Service",
            data={"customer": signal.customer_name}
        ))

        # Infrastructure events lookup
        self.events.append(TimelineEvent(
            timestamp=base_time + timedelta(milliseconds=35),
            event_type=TimelineEventType.ENRICHMENT,
            title="Infrastructure Events Retrieved",
            description="Queried recent deployments and infrastructure changes",
            source="DevOps Platform",
            data={"time_range": "60 minutes"}
        ))

        # Threat intelligence lookup
        self.events.append(TimelineEvent(
            timestamp=base_time + timedelta(milliseconds=50),
            event_type=TimelineEventType.ENRICHMENT,
            title="Threat Intelligence Gathered",
            description="Retrieved relevant security news and bulletins",
            source="Threat Intel Feed",
            data={"keywords": [signal.customer_name, signal.threat_type.value]}
        ))

    def _add_agent_analysis_events(self, agent_analyses: Dict[str, AgentAnalysis]):
        """Add agent analysis events."""
        base_time = self.start_time + timedelta(milliseconds=100)

        agent_descriptions = {
            "historical": "Analyzed patterns from similar past incidents",
            "config": "Evaluated against customer security policies",
            "devops": "Correlated with infrastructure events",
            "context": "Assessed business context and external factors",
            "priority": "Determined severity and classification"
        }

        for name, analysis in agent_analyses.items():
            # Add small random offset to show parallel execution
            offset = timedelta(milliseconds=random.randint(0, 50))

            self.events.append(TimelineEvent(
                timestamp=base_time + offset,
                event_type=TimelineEventType.ANALYSIS,
                title=f"{name.title()} Agent Analysis",
                description=agent_descriptions.get(name, "Performed specialized analysis"),
                source=f"{name.title()} Agent",
                data={
                    "confidence": analysis.confidence,
                    "key_findings": analysis.key_findings[:2] if analysis.key_findings else [],
                    "processing_time_ms": analysis.processing_time_ms
                }
            ))

    def _add_fp_analysis_event(self, fp_score: FalsePositiveScore):
        """Add false positive analysis event."""
        self.events.append(TimelineEvent(
            timestamp=self.start_time + timedelta(milliseconds=800),
            event_type=TimelineEventType.ANALYSIS,
            title="False Positive Analysis",
            description=f"FP likelihood assessed: {fp_score.recommendation.replace('_', ' ')}",
            source="FP Analyzer",
            data={
                "fp_score": fp_score.score,
                "confidence": fp_score.confidence,
                "indicators_count": len(fp_score.indicators),
                "recommendation": fp_score.recommendation
            }
        ))

    def _add_correlation_events(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis]
    ):
        """Add correlation events."""
        base_time = self.start_time + timedelta(milliseconds=900)

        # Cross-agent correlation
        self.events.append(TimelineEvent(
            timestamp=base_time,
            event_type=TimelineEventType.CORRELATION,
            title="Cross-Agent Correlation",
            description=f"Synthesized findings from {len(agent_analyses)} specialized agents",
            source="Coordinator",
            data={
                "agents_count": len(agent_analyses),
                "avg_confidence": sum(a.confidence for a in agent_analyses.values()) / len(agent_analyses) if agent_analyses else 0
            }
        ))

        # Pattern matching
        self.events.append(TimelineEvent(
            timestamp=base_time + timedelta(milliseconds=50),
            event_type=TimelineEventType.CORRELATION,
            title="Pattern Matching Complete",
            description="Matched threat against known attack patterns and signatures",
            source="Pattern Matcher",
            data={"threat_type": signal.threat_type.value}
        ))

    def _add_decision_event(self, severity: ThreatSeverity, fp_score: Optional[FalsePositiveScore]):
        """Add decision event."""
        description = f"Threat classified as {severity.value}"
        if fp_score:
            description += f" with {fp_score.score:.0%} FP likelihood"

        self.events.append(TimelineEvent(
            timestamp=self.start_time + timedelta(milliseconds=1000),
            event_type=TimelineEventType.DECISION,
            title="Severity Determination",
            description=description,
            source="Coordinator",
            data={
                "severity": severity.value,
                "fp_score": fp_score.score if fp_score else None
            },
            severity=severity
        ))

    def _add_response_events(self, response_plan: ResponsePlan):
        """Add response action events."""
        base_time = self.start_time + timedelta(milliseconds=1100)

        # Primary action
        self.events.append(TimelineEvent(
            timestamp=base_time,
            event_type=TimelineEventType.ACTION,
            title=f"Primary Action: {response_plan.primary_action.action_type.value.replace('_', ' ').title()}",
            description=response_plan.primary_action.reason,
            source="Response Engine",
            data={
                "action_type": response_plan.primary_action.action_type.value,
                "urgency": response_plan.primary_action.urgency.value,
                "target": response_plan.primary_action.target,
                "auto_executable": response_plan.primary_action.auto_executable
            }
        ))

        # Secondary actions
        for idx, action in enumerate(response_plan.secondary_actions):
            self.events.append(TimelineEvent(
                timestamp=base_time + timedelta(milliseconds=20 * (idx + 1)),
                event_type=TimelineEventType.ACTION,
                title=f"Secondary Action: {action.action_type.value.replace('_', ' ').title()}",
                description=action.reason,
                source="Response Engine",
                data={
                    "action_type": action.action_type.value,
                    "urgency": action.urgency.value,
                    "target": action.target
                }
            ))

        # Escalation path
        if response_plan.escalation_path:
            self.events.append(TimelineEvent(
                timestamp=base_time + timedelta(milliseconds=100),
                event_type=TimelineEventType.ESCALATION,
                title="Escalation Path Defined",
                description=f"Escalation chain: {' → '.join(response_plan.escalation_path)}",
                source="Response Engine",
                data={
                    "escalation_path": response_plan.escalation_path,
                    "sla_minutes": response_plan.sla_minutes
                }
            ))

