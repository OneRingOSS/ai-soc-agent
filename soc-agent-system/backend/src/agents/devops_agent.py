"""DevOps Agent - Infrastructure correlation specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class DevOpsAgent(BaseAgent):
    """Agent that correlates threats with infrastructure events."""
    
    def __init__(self, **kwargs):
        """Initialize DevOps Agent."""
        super().__init__(name="DevOps Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for DevOps analysis."""
        return """You are a DevOps Correlation Agent for a Security Operations Center.

Your role is to:
1. Correlate threat timing with infrastructure events
2. Check for deployment-related issues
3. Identify platform-wide problems
4. Assess if the threat is infrastructure-caused

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "infra_correlation_found": boolean,
    "related_events": ["event1", "event2"]
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and infra context."""
        infra_events = context.get("infra_events", [])
        
        events_text = "\n".join([
            f"- {e.timestamp.isoformat()}: [{e.event_type}] {e.description} "
            f"(Services: {', '.join(e.affected_services)})"
            for e in infra_events
        ]) if infra_events else "No recent infrastructure events"
        
        return f"""Analyze this threat signal for infrastructure correlations:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

RECENT INFRASTRUCTURE EVENTS (last 60 minutes):
{events_text}

Determine if any infrastructure events may explain or correlate with this threat signal."""

