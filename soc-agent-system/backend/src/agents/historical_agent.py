"""Historical Agent - Pattern recognition specialist."""
from typing import Any, Dict, List
from agents.base_agent import BaseAgent
from models import ThreatSignal, IntelMatch
import logging

logger = logging.getLogger(__name__)


class HistoricalAgent(BaseAgent):
    """Agent that analyzes historical patterns and similar incidents."""

    def __init__(self, intel_enricher=None, **kwargs):
        """
        Initialize Historical Agent.

        Args:
            intel_enricher: Optional IntelEnricher for threat intelligence lookups
            **kwargs: Additional arguments passed to BaseAgent
        """
        super().__init__(name="Historical Agent", **kwargs)
        self.intel_enricher = intel_enricher

        if self.intel_enricher:
            logger.info("HistoricalAgent: intel enricher configured")
        else:
            logger.debug("HistoricalAgent: no intel enricher (backward compat mode)")

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

    async def analyze(self, signal: ThreatSignal, context: Dict[str, Any]):
        """
        Analyze threat signal with historical patterns and intel enrichment.

        Args:
            signal: ThreatSignal to analyze
            context: Additional context (similar_incidents, etc.)

        Returns:
            AgentAnalysis with optional intel_matches in raw_output metadata
        """
        # Step 1: Perform intel enrichment if available
        intel_matches: List[IntelMatch] = []

        if self.intel_enricher:
            try:
                logger.debug(f"HistoricalAgent.analyze: running VT enrichment for {signal.id}")

                # Convert signal to dict for enricher
                signal_data = {
                    "metadata": signal.metadata,
                    "threat_type": signal.threat_type.value,
                    "customer_name": signal.customer_name
                }

                intel_matches = await self.intel_enricher.enrich(signal_data)

                logger.info(
                    f"HistoricalAgent.analyze: VT enrichment complete | "
                    f"matches={len(intel_matches)}"
                )
            except Exception as e:
                logger.error(f"HistoricalAgent.analyze: intel enrichment error — {e}")
                # Continue without intel matches (graceful degradation)
                intel_matches = []

        # Step 2: Perform standard historical analysis
        analysis_result = await super().analyze(signal, context)

        # Step 3: Add intel_matches to raw_output metadata
        if intel_matches or self.intel_enricher:
            # Parse raw_output to add metadata
            import json
            try:
                raw_data = json.loads(analysis_result.raw_output) if analysis_result.raw_output else {}
            except (json.JSONDecodeError, ValueError, TypeError):
                raw_data = {}

            if "metadata" not in raw_data:
                raw_data["metadata"] = {}

            raw_data["metadata"]["intel_matches"] = [
                match.model_dump() for match in intel_matches
            ]

            # Update raw_output with enriched metadata (must be JSON string)
            analysis_result.raw_output = json.dumps(raw_data)

            logger.info(
                f"HistoricalAgent.analyze: added {len(intel_matches)} intel matches to analysis"
            )

        return analysis_result

    async def analyze_mock(self, signal: ThreatSignal, context: Dict[str, Any]):
        """
        Mock analysis with intel enrichment.

        Overrides base class to add VT enrichment even in mock mode.
        """
        # Step 1: Perform intel enrichment if available
        intel_matches: List[IntelMatch] = []

        if self.intel_enricher:
            try:
                logger.info(f"HistoricalAgent.analyze_mock: running VT enrichment for {signal.id}")

                # Convert signal to dict for enricher
                signal_data = {
                    "metadata": signal.metadata,
                    "threat_type": signal.threat_type.value,
                    "customer_name": signal.customer_name
                }

                intel_matches = await self.intel_enricher.enrich(signal_data)

                logger.info(
                    f"HistoricalAgent.analyze_mock: VT enrichment complete | "
                    f"matches={len(intel_matches)}"
                )
            except Exception as e:
                logger.error(f"HistoricalAgent.analyze_mock: intel enrichment error — {e}")
                # Continue without intel matches (graceful degradation)
                intel_matches = []

        # Step 2: Perform standard mock analysis
        analysis_result = await super().analyze_mock(signal, context)

        # Step 3: Add intel_matches to raw_output metadata
        if intel_matches or self.intel_enricher:
            # Parse raw_output to add metadata
            import json
            try:
                raw_data = json.loads(analysis_result.raw_output) if analysis_result.raw_output else {}
            except (json.JSONDecodeError, ValueError, TypeError):
                raw_data = {}

            if "metadata" not in raw_data:
                raw_data["metadata"] = {}

            raw_data["metadata"]["intel_matches"] = [
                match.model_dump() for match in intel_matches
            ]

            # Update raw_output with enriched metadata (must be JSON string)
            analysis_result.raw_output = json.dumps(raw_data)

            logger.info(
                f"HistoricalAgent.analyze_mock: added {len(intel_matches)} intel matches to analysis"
            )

        return analysis_result


