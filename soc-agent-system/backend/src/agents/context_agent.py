"""Context Agent - Business context specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class ContextAgent(BaseAgent):
    """Agent that provides business context from external events."""
    
    def __init__(self, **kwargs):
        """Initialize Context Agent."""
        super().__init__(name="Context Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for context analysis."""
        return """You are a Business Context Agent for a Security Operations Center.

Your role is to:
1. Search for relevant external events (news, market data)
2. Correlate with industry-specific activities
3. Provide business context for anomalies
4. Distinguish legitimate surges from attacks

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "external_factors_found": boolean,
    "business_context": "Explanation of relevant business context"
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and news context."""
        news_items = context.get("news_items", [])
        
        news_text = "\n".join([
            f"- [{n.source}] {n.title}: {n.summary}"
            for n in news_items
        ]) if news_items else "No relevant news items found"
        
        return f"""Analyze this threat signal for business context:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

RELEVANT NEWS AND MARKET EVENTS:
{news_text}

Determine if external business factors may explain this threat signal or if it represents genuine malicious activity."""

