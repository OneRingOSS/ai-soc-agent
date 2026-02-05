"""Historical Agent - Pattern recognition specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class HistoricalAgent(BaseAgent):
    """Agent that analyzes historical patterns and similar incidents."""
    
    def __init__(self, **kwargs):
        """Initialize Historical Agent."""
        super().__init__(name="Historical Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for historical analysis."""
        return """You are a Historical Pattern Analysis Agent for a Security Operations Center.

Your role is to:
1. Analyze past incidents for similar patterns
2. Identify recurring threats across customers
3. Provide context from previous resolutions
4. Calculate pattern similarity scores

You have access to a 30-day window of historical incident data.

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "similar_incidents_found": number,
    "pattern_match_score": 0.0-1.0
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and historical context."""
        similar_incidents = context.get("similar_incidents", [])
        
        incidents_text = "\n".join([
            f"- {inc.timestamp.isoformat()}: {inc.customer_name} - {inc.threat_type.value} - "
            f"Resolution: {inc.resolution} (False positive: {inc.was_false_positive})"
            for inc in similar_incidents
        ]) if similar_incidents else "No similar incidents found"
        
        return f"""Analyze this threat signal for historical patterns:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

SIMILAR HISTORICAL INCIDENTS (last 30 days):
{incidents_text}

Analyze patterns, identify if this is a recurring issue, and provide insights from past resolutions."""

