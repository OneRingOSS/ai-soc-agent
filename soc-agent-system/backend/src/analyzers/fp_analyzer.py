"""False Positive Analyzer - Predicts likelihood of false positives."""
import logging
from typing import Dict, Any, List, Optional

from models import (
    ThreatSignal, FalsePositiveScore, FalsePositiveIndicator,
    ThreatType, HistoricalIncident
)

logger = logging.getLogger(__name__)


class FalsePositiveAnalyzer:
    """Analyzes threat signals to predict false positive likelihood."""

    # Historical FP rates by threat type (mock data - would be from DB in production)
    BASELINE_FP_RATES = {
        ThreatType.BOT_TRAFFIC: 0.35,  # 35% FP rate
        ThreatType.PROXY_NETWORK: 0.40,
        ThreatType.DEVICE_COMPROMISE: 0.10,
        ThreatType.ANOMALY_DETECTION: 0.50,
        ThreatType.RATE_LIMIT_BREACH: 0.45,
        ThreatType.GEO_ANOMALY: 0.55,
    }

    # Known benign patterns
    BENIGN_USER_AGENTS = [
        "googlebot", "bingbot", "slackbot", "facebookexternalhit",
        "twitterbot", "linkedinbot", "pingdom", "uptimerobot"
    ]

    BENIGN_IP_PATTERNS = [
        "66.249.",  # Google
        "157.55.",  # Microsoft/Bing
        "40.77.",   # Microsoft
    ]

    def __init__(self, historical_incidents: Optional[List[HistoricalIncident]] = None):
        """Initialize with optional historical data."""
        self.historical_incidents = historical_incidents or []

    def analyze(
        self, 
        signal: ThreatSignal, 
        agent_analyses: Dict[str, Any],
        similar_incidents: List[HistoricalIncident]
    ) -> FalsePositiveScore:
        """
        Analyze a threat signal and predict FP likelihood.

        Args:
            signal: The threat signal to analyze
            agent_analyses: Results from all agents
            similar_incidents: Historical incidents similar to this one

        Returns:
            FalsePositiveScore with prediction and indicators
        """
        logger.info(f"🔍 Analyzing FP likelihood for {signal.threat_type.value}")
        logger.info(
            "FP analysis started",
            extra={
                "threat_id": signal.id,
                "threat_type": signal.threat_type.value,
                "component": "fp_analyzer"
            }
        )

        indicators: List[FalsePositiveIndicator] = []

        # 1. Check user agent patterns
        ua_indicator = self._analyze_user_agent(signal)
        if ua_indicator:
            indicators.append(ua_indicator)

        # 2. Check IP patterns
        ip_indicator = self._analyze_ip(signal)
        if ip_indicator:
            indicators.append(ip_indicator)

        # 3. Check request volume patterns
        volume_indicator = self._analyze_request_volume(signal)
        if volume_indicator:
            indicators.append(volume_indicator)

        # 4. Analyze historical patterns
        history_indicators = self._analyze_historical_patterns(
            signal, similar_incidents
        )
        indicators.extend(history_indicators)

        # 5. Check agent confidence levels
        confidence_indicator = self._analyze_agent_confidence(agent_analyses)
        if confidence_indicator:
            indicators.append(confidence_indicator)

        # 6. Check for known benign patterns
        benign_indicator = self._check_benign_patterns(signal)
        if benign_indicator:
            indicators.append(benign_indicator)

        # Calculate final score
        fp_score = self._calculate_score(signal, indicators, similar_incidents)

        logger.info(f"   FP Score: {fp_score.score:.2f} ({fp_score.recommendation})")

        return fp_score

    def _analyze_user_agent(self, signal: ThreatSignal) -> Optional[FalsePositiveIndicator]:
        """Check if user agent suggests benign traffic."""
        user_agent = signal.metadata.get("user_agent")
        if not user_agent:
            return None

        ua_lower = user_agent.lower()

        for benign_ua in self.BENIGN_USER_AGENTS:
            if benign_ua in ua_lower:
                return FalsePositiveIndicator(
                    indicator=f"Known benign bot: {benign_ua}",
                    weight=0.4,  # Strong FP indicator
                    description=f"User agent matches known benign crawler: {benign_ua}",
                    source="FP Analyzer - User Agent Check"
                )

        # Check for suspicious patterns
        suspicious_patterns = ["python-requests", "curl", "wget", "scanner"]
        for pattern in suspicious_patterns:
            if pattern in ua_lower:
                return FalsePositiveIndicator(
                    indicator=f"Suspicious user agent: {pattern}",
                    weight=-0.2,  # Slight real threat indicator
                    description=f"User agent contains suspicious pattern: {pattern}",
                    source="FP Analyzer - User Agent Check"
                )

        return None

    def _analyze_ip(self, signal: ThreatSignal) -> Optional[FalsePositiveIndicator]:
        """Check if IP suggests benign or malicious traffic."""
        source_ip = signal.metadata.get("source_ip", "0.0.0.0")
        
        for benign_prefix in self.BENIGN_IP_PATTERNS:
            if source_ip.startswith(benign_prefix):
                return FalsePositiveIndicator(
                    indicator=f"Known benign IP range: {benign_prefix}*",
                    weight=0.5,  # Strong FP indicator
                    description="IP belongs to known benign service provider",
                    source="FP Analyzer - IP Check"
                )

        return None

    def _analyze_request_volume(self, signal: ThreatSignal) -> Optional[FalsePositiveIndicator]:
        """Analyze request volume patterns."""
        request_count = signal.metadata.get("request_count", 0)
        time_window = signal.metadata.get("time_window_minutes", 5)
        rpm = request_count / max(time_window, 1)

        if rpm < 10:
            return FalsePositiveIndicator(
                indicator="Low request volume",
                weight=0.2,
                description=f"Only {rpm:.1f} requests/minute - may be normal traffic",
                source="FP Analyzer - Volume Check"
            )
        elif rpm > 1000:
            return FalsePositiveIndicator(
                indicator="Extremely high request volume",
                weight=-0.3,
                description=f"{rpm:.0f} requests/minute indicates automated attack",
                source="FP Analyzer - Volume Check"
            )

        return None

    def _analyze_historical_patterns(
        self,
        signal: ThreatSignal,
        similar_incidents: List[HistoricalIncident]
    ) -> List[FalsePositiveIndicator]:
        """Analyze historical incident patterns."""
        indicators = []

        if not similar_incidents:
            return indicators

        # Count resolution types
        fp_count = sum(1 for i in similar_incidents if i.resolved_as == "false_positive")
        total = len(similar_incidents)

        if total > 0:
            fp_rate = fp_count / total

            if fp_rate > 0.5:
                indicators.append(FalsePositiveIndicator(
                    indicator=f"High historical FP rate: {fp_rate:.0%}",
                    weight=0.3,
                    description=f"{fp_count}/{total} similar incidents were false positives",
                    source="FP Analyzer - Historical Analysis"
                ))
            elif fp_rate < 0.2:
                indicators.append(FalsePositiveIndicator(
                    indicator=f"Low historical FP rate: {fp_rate:.0%}",
                    weight=-0.3,
                    description=f"Only {fp_count}/{total} similar incidents were false positives",
                    source="FP Analyzer - Historical Analysis"
                ))

        # Check for recurring customer patterns
        customer_incidents = [i for i in similar_incidents
                            if i.customer_name == signal.customer_name]
        if len(customer_incidents) >= 3:
            customer_fp = sum(1 for i in customer_incidents
                            if i.resolved_as == "false_positive")
            if customer_fp >= 2:
                indicators.append(FalsePositiveIndicator(
                    indicator="Recurring FP pattern for customer",
                    weight=0.25,
                    description=f"Customer has {customer_fp} previous false positives",
                    source="FP Analyzer - Customer History"
                ))

        return indicators

    def _analyze_agent_confidence(
        self,
        agent_analyses: Dict[str, Any]
    ) -> Optional[FalsePositiveIndicator]:
        """Check agent confidence levels for FP signals."""
        if not agent_analyses:
            return None

        confidences = []
        for name, analysis in agent_analyses.items():
            if hasattr(analysis, 'confidence'):
                confidences.append(analysis.confidence)

        if not confidences:
            return None

        avg_confidence = sum(confidences) / len(confidences)

        if avg_confidence < 0.5:
            return FalsePositiveIndicator(
                indicator="Low agent confidence",
                weight=0.2,
                description=f"Average agent confidence is {avg_confidence:.0%}",
                source="FP Analyzer - Agent Confidence"
            )
        elif avg_confidence > 0.85:
            return FalsePositiveIndicator(
                indicator="High agent confidence",
                weight=-0.2,
                description=f"Average agent confidence is {avg_confidence:.0%}",
                source="FP Analyzer - Agent Confidence"
            )

        return None

    def _check_benign_patterns(self, signal: ThreatSignal) -> Optional[FalsePositiveIndicator]:
        """Check for known benign patterns in raw data."""
        metadata = signal.metadata or {}

        # Check for monitoring/health check patterns
        endpoint = metadata.get("endpoint", "").lower()
        if endpoint in ["/health", "/ping", "/status", "/ready"]:
            return FalsePositiveIndicator(
                indicator="Health check endpoint",
                weight=0.4,
                description="Traffic to health check endpoint is typically benign",
                source="FP Analyzer - Endpoint Check"
            )

        # Check for known internal IPs
        source_ip = metadata.get("source_ip", "0.0.0.0")
        if source_ip.startswith("10.") or source_ip.startswith("192.168."):
            return FalsePositiveIndicator(
                indicator="Internal IP address",
                weight=0.3,
                description="Traffic from internal network",
                source="FP Analyzer - IP Check"
            )

        return None

    def _calculate_score(
        self,
        signal: ThreatSignal,
        indicators: List[FalsePositiveIndicator],
        similar_incidents: List[HistoricalIncident]
    ) -> FalsePositiveScore:
        """Calculate final FP score from all indicators."""

        # Start with baseline rate for this threat type
        baseline = self.BASELINE_FP_RATES.get(signal.threat_type, 0.3)

        # Apply indicator weights
        total_weight = sum(i.weight for i in indicators)
        adjusted_score = baseline + (total_weight * 0.3)  # Scale factor

        # Clamp to 0-1
        final_score = max(0.0, min(1.0, adjusted_score))

        # Calculate confidence based on data quality
        confidence = 0.5  # Base confidence
        if similar_incidents:
            confidence += min(0.3, len(similar_incidents) * 0.05)
        if indicators:
            confidence += min(0.2, len(indicators) * 0.04)
        confidence = min(1.0, confidence)

        # Determine recommendation
        if final_score >= 0.7:
            recommendation = "likely_false_positive"
            explanation = "Multiple indicators suggest this is likely a false positive. Consider auto-dismissing or quick review."
        elif final_score >= 0.4:
            recommendation = "needs_review"
            explanation = "Mixed signals - human review recommended to confirm threat status."
        else:
            recommendation = "likely_real_threat"
            explanation = "Strong indicators of real threat. Prioritize investigation and response."

        # Count historical resolutions
        fp_count = sum(1 for i in similar_incidents if i.resolved_as == "false_positive")
        tp_count = sum(1 for i in similar_incidents if i.resolved_as == "true_positive")

        fp_score_result = FalsePositiveScore(
            score=round(final_score, 3),
            confidence=round(confidence, 3),
            indicators=indicators,
            historical_fp_rate=self.BASELINE_FP_RATES.get(signal.threat_type),
            similar_resolved_as_fp=fp_count,
            similar_resolved_as_real=tp_count,
            recommendation=recommendation,
            explanation=explanation
        )

        logger.info(
            "FP analysis completed",
            extra={
                "threat_id": signal.id,
                "fp_score": fp_score_result.score,
                "recommendation": recommendation,
                "component": "fp_analyzer"
            }
        )

        return fp_score_result

