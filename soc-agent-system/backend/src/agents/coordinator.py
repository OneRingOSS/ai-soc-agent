"""Coordinator Agent - Orchestrates multi-agent threat analysis."""
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from config import settings
from models import (
    ThreatSignal, ThreatAnalysis, AgentAnalysis,
    ThreatSeverity, ThreatStatus
)
from mock_data import MockDataStore
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent
from analyzers.fp_analyzer import FalsePositiveAnalyzer
from analyzers.adversarial_detector import AdversarialManipulationDetector
from analyzers.response_engine import ResponseActionEngine
from analyzers.timeline_builder import TimelineBuilder
from mitre_parser import extract_mitre_tags, build_wazuh_tags, merge_mitre_tags
from mitre_fallback import get_fallback_mitre_tags
from telemetry import get_tracer
from metrics import (
    record_threat_processed,
    record_agent_duration,
    record_fp_score,
    record_processing_phase
)

# Configure logger
logger = logging.getLogger(__name__)

# Get tracer for custom spans
tracer = get_tracer(__name__)


class CoordinatorAgent:
    """Orchestrates parallel analysis across all specialized agents."""

    def __init__(
        self,
        mock_data: Optional[MockDataStore] = None,
        client: Optional[AsyncOpenAI] = None,
        use_mock: bool = False,
        intel_cache=None,
        adversarial_detector_enabled: bool = True
    ):
        """
        Initialize coordinator with all specialized agents.

        Args:
            mock_data: Optional mock data store
            client: Optional OpenAI client
            use_mock: Whether to use mock mode
            intel_cache: Optional IntelFeedCache for threat intelligence enrichment
            adversarial_detector_enabled: Whether to enable adversarial detection (default: True)
        """
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.mock_data = mock_data or MockDataStore()
        self.use_mock = use_mock
        self.adversarial_detector_enabled = adversarial_detector_enabled

        # Initialize intel enricher if cache provided
        intel_enricher = None
        if intel_cache:
            from intel_enricher import IntelEnricher
            intel_enricher = IntelEnricher(cache=intel_cache)
            logger.info("CoordinatorAgent: intel enricher initialized")

        # Initialize specialized agents
        self.historical_agent = HistoricalAgent(
            client=self.client,
            intel_enricher=intel_enricher
        )
        self.config_agent = ConfigAgent(client=self.client)
        self.devops_agent = DevOpsAgent(client=self.client)
        self.context_agent = ContextAgent(client=self.client)
        self.priority_agent = PriorityAgent(client=self.client)

        # Initialize analyzers
        self.fp_analyzer = FalsePositiveAnalyzer()
        self.adversarial_detector = AdversarialManipulationDetector(use_mock=use_mock)
        self.response_engine = ResponseActionEngine()
        self.timeline_builder = TimelineBuilder()

        logger.info("🎯 Coordinator initialized with 5 specialized agents + 4 analyzers")
    
    async def analyze_threat(
        self,
        signal: ThreatSignal,
        historical_context_override: Optional[Dict[str, Any]] = None
    ) -> ThreatAnalysis:
        """Perform comprehensive threat analysis using all agents in parallel.

        Args:
            signal: The threat signal to analyze
            historical_context_override: Optional override for historical context
                                         (used for adversarial testing)

        Returns:
            Complete threat analysis
        """
        # Create parent span for the entire threat analysis
        with tracer.start_as_current_span("analyze_threat") as span:
            # Set initial span attributes
            span.set_attribute("threat.id", signal.id)
            span.set_attribute("threat.type", signal.threat_type.value)
            span.set_attribute("customer.name", signal.customer_name)
            span.set_attribute("source.ip", signal.metadata.get("source_ip", "unknown"))

            logger.info("=" * 80)
            logger.info(
                "Threat received",
                extra={
                    "threat_id": signal.id,
                    "customer_name": signal.customer_name,
                    "threat_type": signal.threat_type.value,
                    "component": "coordinator"
                }
            )
            logger.info(f"🚨 NEW THREAT DETECTED: {signal.threat_type.value}")
            logger.info(f"   Customer: {signal.customer_name}")
            logger.info(f"   Signal ID: {signal.id}")
            logger.info("=" * 80)

            start_time = time.time()

            # Gather context for each agent
            logger.info("\n📊 GATHERING CONTEXT FOR AGENTS...")
            contexts = self._build_agent_contexts(signal, historical_context_override)
            logger.info(f"   ✓ Historical: {len(contexts['historical'].get('similar_incidents', []))} similar incidents found")
            logger.info(f"   ✓ Config: Retrieved settings for {signal.customer_name}")
            logger.info(f"   ✓ DevOps: {len(contexts['devops'].get('infra_events', []))} recent infrastructure events")
            logger.info(f"   ✓ Context: {len(contexts['context'].get('news_items', []))} relevant news items")
            logger.info("   ✓ Priority: Context prepared for classification")

            # Determine analysis method
            analyze_method = "analyze_mock" if self.use_mock else "analyze"
            mode = "MOCK MODE" if self.use_mock else "LIVE MODE (OpenAI API)"

            logger.info(f"\n🤖 DISPATCHING 5 AGENTS IN PARALLEL ({mode})...")
            dispatch_start = time.time()

            # Dispatch all agents in parallel
            results = await asyncio.gather(
                self._log_agent_execution(
                    "Historical Agent",
                    getattr(self.historical_agent, analyze_method),
                    signal,
                    contexts["historical"]
                ),
                self._log_agent_execution(
                    "Config Agent",
                    getattr(self.config_agent, analyze_method),
                    signal,
                    contexts["config"]
                ),
                self._log_agent_execution(
                    "DevOps Agent",
                    getattr(self.devops_agent, analyze_method),
                    signal,
                    contexts["devops"]
                ),
                self._log_agent_execution(
                    "Context Agent",
                    getattr(self.context_agent, analyze_method),
                    signal,
                    contexts["context"]
                ),
                self._log_agent_execution(
                    "Priority Agent",
                    getattr(self.priority_agent, analyze_method),
                    signal,
                    contexts["priority"]
                ),
                return_exceptions=True
            )

            dispatch_time = (time.time() - dispatch_start) * 1000
            logger.info(f"\n⚡ ALL AGENTS COMPLETED IN {dispatch_time:.0f}ms (parallel execution)")

            # Process results
            agent_analyses = {}
            for i, (name, result) in enumerate(zip(
                ["historical", "config", "devops", "context", "priority"],
                results
            )):
                if isinstance(result, Exception):
                    logger.error(f"   ❌ {name} agent failed: {str(result)}")
                    agent_analyses[name] = AgentAnalysis(
                        agent_name=name,
                        analysis=f"Agent failed: {str(result)}",
                        confidence=0.0,
                        key_findings=["Error"],
                        recommendations=["Manual review required"],
                        processing_time_ms=0
                    )
                else:
                    agent_analyses[name] = result

            # Run enhanced analyzers
            logger.info("\n🔍 RUNNING ENHANCED ANALYZERS...")

            # 1. False Positive Analysis
            with tracer.start_as_current_span("fp_analyzer"):
                similar_incidents = contexts['historical'].get('similar_incidents', [])
                fp_score = self.fp_analyzer.analyze(signal, agent_analyses, similar_incidents)
                logger.info(f"   ✓ FP Score: {fp_score.score:.2f} ({fp_score.recommendation})")

            # 2. Determine severity (from priority agent or default)
            priority_analysis = agent_analyses.get("priority")
            severity = self._extract_severity(priority_analysis) if priority_analysis else ThreatSeverity.MEDIUM

            # 3. Adversarial Manipulation Detection
            with tracer.start_as_current_span("adversarial_detector"):
                if self.adversarial_detector_enabled:
                    # Pass similar_incidents for note authenticity check
                    similar_incidents = contexts.get('historical', {}).get('similar_incidents', [])
                    adversarial_result = self.adversarial_detector.analyze(
                        signal, agent_analyses, severity, fp_score, similar_incidents
                    )

                    # If manipulation detected, adjust FP score explanation
                    if adversarial_result.manipulation_detected:
                        fp_score.explanation = (
                            f"⚠️ WARNING: FP score may be unreliable due to detected adversarial manipulation. "
                            f"Original assessment: {fp_score.explanation}"
                        )
                        logger.warning(
                            "FP score potentially compromised by adversarial manipulation",
                            extra={
                                "threat_id": signal.id,
                                "original_fp_score": fp_score.score,
                                "attack_vector": adversarial_result.attack_vector,
                                "component": "coordinator"
                            }
                        )
                else:
                    # Detector disabled - return empty result
                    from models import AdversarialDetectionResult
                    adversarial_result = AdversarialDetectionResult(
                        manipulation_detected=False,
                        confidence=0.0,
                        risk_score=0.0,
                        contradictions=[],
                        anomalies=[],
                        attack_vector=None
                    )

                if adversarial_result.manipulation_detected:
                    logger.warning(
                        "🚨 ADVERSARIAL MANIPULATION DETECTED",
                        extra={
                            "threat_id": signal.id,
                            "risk_score": adversarial_result.risk_score,
                            "attack_vector": adversarial_result.attack_vector,
                            "contradictions": len(adversarial_result.contradictions),
                            "anomalies": len(adversarial_result.anomalies),
                            "component": "adversarial_detector"
                        }
                    )
                    logger.info(f"   🚨 Adversarial Detection: MANIPULATION DETECTED (risk: {adversarial_result.risk_score:.2f})")
                    logger.info(f"      Attack Vector: {adversarial_result.attack_vector}")
                    logger.info(f"      Contradictions: {len(adversarial_result.contradictions)}")
                    logger.info(f"      Anomalies: {len(adversarial_result.anomalies)}")
                    logger.info(f"      Recommendation: {adversarial_result.recommendation}")
                else:
                    logger.info(f"   ✓ Adversarial Detection: No manipulation detected")

            # 4. Generate Response Plan
            with tracer.start_as_current_span("response_engine"):
                customer_config = contexts['config'].get('customer_config')
                response_plan = self.response_engine.generate_response_plan(
                    signal, severity, fp_score, customer_config, agent_analyses
                )
                logger.info(f"   ✓ Response Plan: {response_plan.primary_action.action_type.value} ({response_plan.primary_action.urgency.value})")

            # 5. Build Investigation Timeline
            with tracer.start_as_current_span("timeline_builder"):
                timeline = self.timeline_builder.build_timeline(
                    signal, agent_analyses, fp_score, response_plan, severity
                )
                logger.info(f"   ✓ Timeline: {len(timeline.events)} events")

            # Synthesize final analysis
            logger.info("\n🔬 SYNTHESIZING FINAL ANALYSIS...")
            total_time = int((time.time() - start_time) * 1000)

            final_analysis = self._synthesize_analysis(
                signal, agent_analyses, total_time, severity, fp_score, response_plan, timeline, adversarial_result
            )

            # Set final span attributes
            span.set_attribute("threat.severity", severity.value)
            span.set_attribute("fp.score", fp_score.score)
            span.set_attribute("adversarial.detected", adversarial_result.manipulation_detected)
            if adversarial_result.manipulation_detected:
                span.set_attribute("adversarial.risk_score", adversarial_result.risk_score)
            span.set_attribute("requires_review", final_analysis.requires_human_review)

            # Record Prometheus metrics
            record_threat_processed(severity.value, signal.threat_type.value)
            record_fp_score(fp_score.score)
            record_processing_phase("total", total_time / 1000.0)

            logger.info("\n✅ ANALYSIS COMPLETE")
            logger.info(f"   Severity: {final_analysis.severity.value}")
            logger.info(f"   Total Processing Time: {total_time}ms")
            logger.info(f"   Requires Human Review: {final_analysis.requires_human_review}")
            logger.info("=" * 80 + "\n")

            return final_analysis

    async def _log_agent_execution(
        self,
        agent_name: str,
        analyze_func,
        signal: ThreatSignal,
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Wrapper to log individual agent execution with OpenTelemetry span."""
        # Create a child span for this agent
        span_name = agent_name.lower().replace(" ", "_")
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("agent.name", agent_name)

            logger.info(f"   🔄 {agent_name} starting...")
            start = time.time()

            try:
                result = await analyze_func(signal, context)
                elapsed = (time.time() - start) * 1000

                span.set_attribute("agent.confidence", result.confidence)
                span.set_attribute("agent.duration_ms", elapsed)

                # Record agent duration in Prometheus
                record_agent_duration(span_name, elapsed / 1000.0)

                logger.info(
                    "Agent completed",
                    extra={
                        "agent_name": agent_name,
                        "confidence": result.confidence,
                        "duration_ms": elapsed,
                        "component": "coordinator"
                    }
                )
                logger.info(f"   ✅ {agent_name} completed in {elapsed:.0f}ms")
                logger.info(f"      Confidence: {result.confidence:.2f}")
                logger.info(f"      Key Findings: {len(result.key_findings)}")

                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                span.set_attribute("agent.error", str(e))
                logger.error(f"   ❌ {agent_name} failed after {elapsed:.0f}ms: {str(e)}")
                raise
    
    def _build_agent_contexts(
        self,
        signal: ThreatSignal,
        historical_context_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Build context data for each agent.

        Args:
            signal: The threat signal
            historical_context_override: Optional override for historical context
                                         (used for adversarial testing)

        Returns:
            Dictionary of contexts for each agent
        """
        # Extract keywords for news search
        keywords = [signal.customer_name, signal.threat_type.value]
        if "crypto" in signal.customer_name.lower():
            keywords.append("bitcoin")

        # Use override if provided, otherwise use mock data
        if historical_context_override:
            historical_context = historical_context_override
        else:
            historical_context = {
                "similar_incidents": self.mock_data.get_similar_incidents(
                    signal.threat_type, signal.customer_name
                )
            }

        return {
            "historical": historical_context,
            "config": {
                "customer_config": self.mock_data.get_customer_config(signal.customer_name)
            },
            "devops": {
                "infra_events": self.mock_data.get_recent_infra_events(60)
            },
            "context": {
                "news_items": self.mock_data.get_relevant_news(keywords)
            },
            "priority": {}
        }
    
    def _synthesize_analysis(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis],
        total_time: int,
        severity: ThreatSeverity,
        fp_score,
        response_plan,
        timeline,
        adversarial_result
    ) -> ThreatAnalysis:
        """Synthesize all agent analyses into final threat analysis."""

        # Extract priority agent results for MITRE mapping
        priority_analysis = agent_analyses.get("priority")

        mitre_tactics = []
        mitre_techniques = []
        customer_narrative = "Analysis completed. Please review agent findings."
        requires_review = False
        review_reason = None

        if priority_analysis and priority_analysis.confidence > 0:
            # Check for human review requirement
            analysis_lower = priority_analysis.analysis.lower()
            requires_review = "review" in analysis_lower or severity == ThreatSeverity.CRITICAL

            if requires_review:
                if severity == ThreatSeverity.CRITICAL:
                    review_reason = "Critical severity threat requires human oversight"
                elif fp_score and fp_score.score >= 0.4 and fp_score.score <= 0.7:
                    review_reason = "Uncertain false positive classification"
                else:
                    review_reason = "Agent recommendation for manual review"

        # Check for adversarial manipulation detection
        if adversarial_result and adversarial_result.manipulation_detected:
            requires_review = True
            review_reason = f"Adversarial manipulation detected: {adversarial_result.explanation}"

        # 3-Layer MITRE ATT&CK Tag Merge
        # Layer 1: Wazuh hints (confidence 1.0)
        wazuh_tags = build_wazuh_tags(signal.mitre_hints) if signal.mitre_hints else []

        # Layer 2: LLM-generated tags from PriorityAgent (confidence >= 0.6)
        priority_tags = []
        if priority_analysis and priority_analysis.raw_output:
            priority_tags = extract_mitre_tags(priority_analysis.raw_output, source="priority_agent")

        # Layer 3: Fallback table (confidence 0.6)
        fallback_tags = get_fallback_mitre_tags(signal.threat_type)

        # Merge with priority: Wazuh > LLM > Fallback
        merged_tags = merge_mitre_tags(wazuh_tags, priority_tags)

        # If still no tags, use fallback
        if not merged_tags:
            merged_tags = fallback_tags[:6]  # Cap at 6

        logger.info(f"   ✓ MITRE Tags: {len(merged_tags)} techniques (Wazuh: {len(wazuh_tags)}, LLM: {len(priority_tags)}, Fallback: {len(fallback_tags)})")

        # Generate executive summary
        all_findings = []
        for analysis in agent_analyses.values():
            all_findings.extend(analysis.key_findings)

        executive_summary = self._generate_executive_summary(
            signal, severity, all_findings[:5], fp_score
        )

        # Extract intel_matches from historical agent metadata
        intel_matches = []
        historical_analysis = agent_analyses.get("historical")
        if historical_analysis and historical_analysis.raw_output:
            # Parse raw_output (should be JSON string)
            import json
            try:
                if isinstance(historical_analysis.raw_output, str):
                    raw_data = json.loads(historical_analysis.raw_output)
                else:
                    raw_data = historical_analysis.raw_output

                metadata = raw_data.get("metadata", {})
                intel_matches_data = metadata.get("intel_matches", [])

                if intel_matches_data:
                    from models import IntelMatch
                    intel_matches = [
                        IntelMatch(**match_data) for match_data in intel_matches_data
                    ]
                    logger.info(f"   ✓ Intel Matches: {len(intel_matches)} threat intelligence hits")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to extract intel_matches from historical agent: {e}")

        return ThreatAnalysis(
            signal=signal,
            status=ThreatStatus.COMPLETED,
            severity=severity,
            executive_summary=executive_summary,
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            mitre_tags=merged_tags,  # New: structured MITRE tags with source tracking
            intel_matches=intel_matches,  # New: threat intelligence matches
            customer_narrative=customer_narrative,
            agent_analyses=agent_analyses,
            false_positive_score=fp_score,
            adversarial_detection=adversarial_result,
            response_plan=response_plan,
            investigation_timeline=timeline,
            total_processing_time_ms=total_time,
            requires_human_review=requires_review,
            review_reason=review_reason
        )

    def _extract_severity(self, priority_analysis: AgentAnalysis) -> ThreatSeverity:
        """Extract severity from priority agent analysis."""
        if not priority_analysis or priority_analysis.confidence == 0:
            return ThreatSeverity.MEDIUM

        analysis_lower = priority_analysis.analysis.lower()
        if "critical" in analysis_lower:
            return ThreatSeverity.CRITICAL
        elif "high" in analysis_lower:
            return ThreatSeverity.HIGH
        elif "low" in analysis_lower:
            return ThreatSeverity.LOW
        else:
            return ThreatSeverity.MEDIUM

    def _generate_executive_summary(
        self,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        key_findings: List[str],
        fp_score=None
    ) -> str:
        """Generate executive summary from analysis results."""
        findings_text = "; ".join(key_findings) if key_findings else "Standard analysis completed"

        summary = (
            f"{severity.value} severity {signal.threat_type.value.replace('_', ' ')} "
            f"detected for {signal.customer_name}. "
            f"Key findings: {findings_text}."
        )

        # Add FP context if available
        if fp_score:
            if fp_score.score >= 0.7:
                summary += f" Note: High false positive likelihood ({fp_score.score:.0%})."
            elif fp_score.score <= 0.3:
                summary += f" High confidence real threat ({(1-fp_score.score):.0%})."

        return summary


# Factory function for easy instantiation
def create_coordinator(
    use_mock: bool = False,
    intel_cache=None,
    adversarial_detector_enabled: bool = True
) -> CoordinatorAgent:
    """
    Create a coordinator agent instance.

    Args:
        use_mock: Whether to use mock mode
        intel_cache: Optional IntelFeedCache for threat intelligence enrichment
        adversarial_detector_enabled: Whether to enable adversarial detection (default: True)

    Returns:
        CoordinatorAgent instance
    """
    return CoordinatorAgent(
        use_mock=use_mock,
        intel_cache=intel_cache,
        adversarial_detector_enabled=adversarial_detector_enabled
    )

