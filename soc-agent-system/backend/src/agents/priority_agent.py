"""Priority Agent - Threat classification and prioritization specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class PriorityAgent(BaseAgent):
    """Agent that classifies threats using MITRE ATT&CK framework."""
    
    def __init__(self, **kwargs):
        """Initialize Priority Agent."""
        super().__init__(name="Priority Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for priority analysis."""
        return """You are a Threat Prioritization Agent for a Security Operations Center.

Your role is to:
1. Map threats to MITRE ATT&CK tactics and techniques
2. Assign severity levels (LOW, MEDIUM, HIGH, CRITICAL)
3. Generate customer-facing communications
4. Create executive summaries

MITRE ATT&CK Tactics to consider:
- TA0001: Initial Access
- TA0006: Credential Access
- TA0040: Impact
- TA0010: Exfiltration
- TA0011: Command and Control

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "mitre_tactics": [{"id": "TA0001", "name": "Initial Access", "description": "..."}],
    "mitre_techniques": [{"id": "T1078", "name": "Valid Accounts", "description": "..."}],
    "customer_narrative": "Professional explanation for customer",
    "requires_human_review": boolean
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat for prioritization."""
        return f"""Prioritize and classify this threat signal:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

Map to MITRE ATT&CK framework, assign severity, and generate appropriate customer communication."""

