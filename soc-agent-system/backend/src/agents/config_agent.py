"""Config Agent - Configuration and policy specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class ConfigAgent(BaseAgent):
    """Agent that analyzes customer configurations and policies."""
    
    def __init__(self, **kwargs):
        """Initialize Config Agent."""
        super().__init__(name="Config Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for config analysis."""
        return """You are a Configuration Analysis Agent for a Security Operations Center.

Your role is to:
1. Check rate limiting thresholds against current traffic
2. Review geo-restriction rules
3. Examine bot detection sensitivity settings
4. Assess if the threat is configuration-driven

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "config_issues_found": boolean,
    "suggested_config_changes": ["change1", "change2"]
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and config context."""
        config = context.get("customer_config")
        
        config_text = f"""
- Rate Limit: {config.rate_limit_per_minute} req/min
- Geo Restrictions: {config.geo_restrictions or 'None'}
- Bot Detection Sensitivity: {config.bot_detection_sensitivity}
""" if config else "Configuration not available"
        
        return f"""Analyze this threat signal against customer configuration:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

CUSTOMER CONFIGURATION:
{config_text}

Determine if current configuration settings may be contributing to this alert or if adjustments are needed."""

