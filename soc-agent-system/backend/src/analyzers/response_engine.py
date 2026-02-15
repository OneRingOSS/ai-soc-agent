"""Response Action Engine - Determines appropriate response actions."""
import logging
from typing import Dict, Any, List, Optional

from models import (
    ThreatSignal, ThreatSeverity, ThreatType, FalsePositiveScore,
    ResponseAction, ResponsePlan, ResponseActionType, ResponseUrgency,
    CustomerConfig, AgentAnalysis
)

logger = logging.getLogger(__name__)


class ResponseActionEngine:
    """Determines appropriate automated response actions for threats."""

    # Response templates by threat type and severity
    RESPONSE_TEMPLATES = {
        ThreatType.BOT_TRAFFIC: {
            ThreatSeverity.CRITICAL: [
                (ResponseActionType.BLOCK_IP, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.IMMEDIATE),
            ],
            ThreatSeverity.HIGH: [
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.URGENT),
                (ResponseActionType.CHALLENGE, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.MEDIUM: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.NORMAL),
                (ResponseActionType.MONITOR, ResponseUrgency.NORMAL),
            ],
            ThreatSeverity.LOW: [
                (ResponseActionType.MONITOR, ResponseUrgency.LOW),
            ],
        },
        ThreatType.PROXY_NETWORK: {
            ThreatSeverity.CRITICAL: [
                (ResponseActionType.BLOCK_IP, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.ESCALATE, ResponseUrgency.IMMEDIATE),
            ],
            ThreatSeverity.HIGH: [
                (ResponseActionType.BLOCK_IP, ResponseUrgency.URGENT),
                (ResponseActionType.CHALLENGE, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.MEDIUM: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.NORMAL),
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.NORMAL),
            ],
            ThreatSeverity.LOW: [
                (ResponseActionType.MONITOR, ResponseUrgency.NORMAL),
            ],
        },
        ThreatType.DEVICE_COMPROMISE: {
            ThreatSeverity.CRITICAL: [
                (ResponseActionType.QUARANTINE, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.ESCALATE, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.BLOCK_IP, ResponseUrgency.IMMEDIATE),
            ],
            ThreatSeverity.HIGH: [
                (ResponseActionType.QUARANTINE, ResponseUrgency.URGENT),
                (ResponseActionType.CHALLENGE, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.MEDIUM: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.NORMAL),
                (ResponseActionType.MONITOR, ResponseUrgency.NORMAL),
            ],
            ThreatSeverity.LOW: [
                (ResponseActionType.MONITOR, ResponseUrgency.LOW),
            ],
        },
        ThreatType.RATE_LIMIT_BREACH: {
            ThreatSeverity.CRITICAL: [
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.BLOCK_IP, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.HIGH: [
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.MEDIUM: [
                (ResponseActionType.RATE_LIMIT, ResponseUrgency.NORMAL),
            ],
            ThreatSeverity.LOW: [
                (ResponseActionType.MONITOR, ResponseUrgency.LOW),
            ],
        },
        ThreatType.GEO_ANOMALY: {
            ThreatSeverity.CRITICAL: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.IMMEDIATE),
                (ResponseActionType.ESCALATE, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.HIGH: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.URGENT),
            ],
            ThreatSeverity.MEDIUM: [
                (ResponseActionType.CHALLENGE, ResponseUrgency.NORMAL),
            ],
            ThreatSeverity.LOW: [
                (ResponseActionType.MONITOR, ResponseUrgency.LOW),
            ],
        },
    }

    # SLA times by severity (minutes)
    SLA_TIMES = {
        ThreatSeverity.CRITICAL: 15,
        ThreatSeverity.HIGH: 30,
        ThreatSeverity.MEDIUM: 60,
        ThreatSeverity.LOW: 240,
        ThreatSeverity.INFO: 480,
    }

    def __init__(self):
        """Initialize response engine."""
        pass

    def generate_response_plan(
        self,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        fp_score: Optional[FalsePositiveScore],
        customer_config: Optional[CustomerConfig],
        agent_analyses: Dict[str, AgentAnalysis]
    ) -> ResponsePlan:
        """
        Generate a response plan for the threat.

        Args:
            signal: The threat signal
            severity: Assessed severity
            fp_score: False positive analysis
            customer_config: Customer-specific settings
            agent_analyses: Results from all agents

        Returns:
            Complete ResponsePlan with actions
        """
        logger.info(f"⚡ Generating response plan for {severity.value} {signal.threat_type.value}")
        logger.info(
            "Response plan generation started",
            extra={
                "threat_id": signal.id,
                "severity": severity.value,
                "threat_type": signal.threat_type.value,
                "component": "response_engine"
            }
        )

        # Check if likely false positive - recommend minimal action
        if fp_score and fp_score.score >= 0.7:
            logger.info(f"   High FP score ({fp_score.score:.2f}) - recommending minimal action")
            return self._generate_fp_response_plan(signal, fp_score)

        # Get response templates for this threat type and severity
        templates = self.RESPONSE_TEMPLATES.get(signal.threat_type, {})
        actions = templates.get(severity, [(ResponseActionType.MONITOR, ResponseUrgency.NORMAL)])

        # Build response actions
        response_actions = []
        for action_type, urgency in actions:
            action = self._build_action(
                action_type=action_type,
                urgency=urgency,
                signal=signal,
                severity=severity,
                customer_config=customer_config
            )
            response_actions.append(action)

        # Check customer config for auto-block settings
        if customer_config and customer_config.auto_block_enabled:
            for action in response_actions:
                if action.action_type == ResponseActionType.BLOCK_IP:
                    action.auto_executable = True
                    action.requires_approval = False

        # Primary action is the first (highest priority)
        primary_action = response_actions[0] if response_actions else self._build_monitor_action(signal)
        secondary_actions = response_actions[1:] if len(response_actions) > 1 else []

        # Build escalation path
        escalation_path = self._build_escalation_path(severity, customer_config)

        # Determine SLA
        sla_minutes = self.SLA_TIMES.get(severity, 60)

        response_plan = ResponsePlan(
            primary_action=primary_action,
            secondary_actions=secondary_actions,
            escalation_path=escalation_path,
            sla_minutes=sla_minutes,
            auto_escalate_after_minutes=sla_minutes // 2,
            notes=self._generate_response_notes(signal, severity, agent_analyses)
        )

        logger.info(
            "Response plan generated",
            extra={
                "threat_id": signal.id,
                "primary_action": primary_action.action_type.value,
                "sla_minutes": sla_minutes,
                "component": "response_engine"
            }
        )

        return response_plan

    def _generate_fp_response_plan(
        self,
        signal: ThreatSignal,
        fp_score: FalsePositiveScore
    ) -> ResponsePlan:
        """Generate minimal response plan for likely false positives."""
        source_ip = signal.metadata.get("source_ip", "0.0.0.0")

        return ResponsePlan(
            primary_action=ResponseAction(
                action_type=ResponseActionType.MONITOR,
                urgency=ResponseUrgency.LOW,
                target=source_ip,
                reason=f"Likely false positive (score: {fp_score.score:.2f})",
                confidence=fp_score.confidence,
                auto_executable=True,
                requires_approval=False,
                estimated_impact="Low",
                rollback_possible=True,
                parameters={"duration_minutes": 30}
            ),
            secondary_actions=[],
            escalation_path=["SOC Tier 1"],
            sla_minutes=240,
            auto_escalate_after_minutes=120,
            notes=f"High FP likelihood. {fp_score.explanation}"
        )

    def _build_action(
        self,
        action_type: ResponseActionType,
        urgency: ResponseUrgency,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        customer_config: Optional[CustomerConfig]
    ) -> ResponseAction:
        """Build a specific response action."""

        # Action-specific configurations
        action_configs = {
            ResponseActionType.BLOCK_IP: {
                "reason": f"Block malicious IP due to {signal.threat_type.value}",
                "impact": "High" if severity in [ThreatSeverity.CRITICAL, ThreatSeverity.HIGH] else "Medium",
                "params": {"duration_minutes": 60, "scope": "customer"},
                "auto_exec": False,
            },
            ResponseActionType.RATE_LIMIT: {
                "reason": f"Apply rate limiting due to {signal.threat_type.value}",
                "impact": "Medium",
                "params": {"requests_per_minute": 10, "duration_minutes": 30},
                "auto_exec": True,
            },
            ResponseActionType.CHALLENGE: {
                "reason": f"Require CAPTCHA/challenge due to {signal.threat_type.value}",
                "impact": "Low",
                "params": {"challenge_type": "captcha", "duration_minutes": 60},
                "auto_exec": True,
            },
            ResponseActionType.WHITELIST: {
                "reason": "Add to whitelist - confirmed legitimate traffic",
                "impact": "Low",
                "params": {"duration_minutes": 1440},
                "auto_exec": False,
            },
            ResponseActionType.MONITOR: {
                "reason": f"Enhanced monitoring for {signal.threat_type.value}",
                "impact": "Low",
                "params": {"duration_minutes": 60, "alert_threshold": 100},
                "auto_exec": True,
            },
            ResponseActionType.ESCALATE: {
                "reason": f"Escalate {severity.value} {signal.threat_type.value} for review",
                "impact": "Low",
                "params": {"escalation_level": "Tier 2"},
                "auto_exec": True,
            },
            ResponseActionType.QUARANTINE: {
                "reason": f"Quarantine affected account due to {signal.threat_type.value}",
                "impact": "High",
                "params": {"notify_user": True},
                "auto_exec": False,
            },
        }

        config = action_configs.get(action_type, {
            "reason": f"Respond to {signal.threat_type.value}",
            "impact": "Medium",
            "params": {},
            "auto_exec": False,
        })

        # Determine target based on action type
        source_ip = signal.metadata.get("source_ip", "0.0.0.0")
        if action_type in [ResponseActionType.BLOCK_IP, ResponseActionType.RATE_LIMIT,
                          ResponseActionType.CHALLENGE, ResponseActionType.MONITOR]:
            target = source_ip
        elif action_type == ResponseActionType.QUARANTINE:
            target = signal.metadata.get("user_id", signal.customer_name)
        else:
            target = signal.customer_name

        return ResponseAction(
            action_type=action_type,
            urgency=urgency,
            target=target,
            reason=config["reason"],
            confidence=0.8 if severity in [ThreatSeverity.CRITICAL, ThreatSeverity.HIGH] else 0.6,
            auto_executable=config["auto_exec"],
            requires_approval=not config["auto_exec"],
            estimated_impact=config["impact"],
            rollback_possible=True,
            parameters=config["params"]
        )

    def _build_monitor_action(self, signal: ThreatSignal) -> ResponseAction:
        """Build a default monitor action."""
        source_ip = signal.metadata.get("source_ip", "0.0.0.0")

        return ResponseAction(
            action_type=ResponseActionType.MONITOR,
            urgency=ResponseUrgency.NORMAL,
            target=source_ip,
            reason="Standard monitoring",
            confidence=0.5,
            auto_executable=True,
            requires_approval=False,
            estimated_impact="Low",
            rollback_possible=True,
            parameters={"duration_minutes": 60}
        )

    def _build_escalation_path(
        self,
        severity: ThreatSeverity,
        customer_config: Optional[CustomerConfig]
    ) -> List[str]:
        """Build escalation path based on severity and customer config."""
        base_path = {
            ThreatSeverity.CRITICAL: ["SOC Tier 2", "SOC Manager", "CISO", "Customer Success"],
            ThreatSeverity.HIGH: ["SOC Tier 2", "SOC Manager", "Customer Success"],
            ThreatSeverity.MEDIUM: ["SOC Tier 1", "SOC Tier 2"],
            ThreatSeverity.LOW: ["SOC Tier 1"],
            ThreatSeverity.INFO: ["SOC Tier 1"],
        }

        path = base_path.get(severity, ["SOC Tier 1"])

        # Add customer-specific contacts if available
        if customer_config and customer_config.escalation_contacts:
            path.extend(customer_config.escalation_contacts[:2])

        return path

    def _generate_response_notes(
        self,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        agent_analyses: Dict[str, AgentAnalysis]
    ) -> str:
        """Generate notes summarizing response rationale."""
        notes = []

        notes.append(f"Threat: {signal.threat_type.value.replace('_', ' ').title()}")
        notes.append(f"Severity: {severity.value.upper()}")
        notes.append(f"Customer: {signal.customer_name}")

        # Add key agent insights
        for name, analysis in agent_analyses.items():
            if analysis.key_findings:
                notes.append(f"{name.title()}: {analysis.key_findings[0]}")

        return " | ".join(notes)

