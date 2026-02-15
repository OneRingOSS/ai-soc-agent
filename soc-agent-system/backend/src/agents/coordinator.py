"""Coordinator Agent - Orchestrates multi-agent threat analysis."""
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from config import settings
from models import (
    ThreatSignal, ThreatAnalysis, AgentAnalysis,
    ThreatSeverity, MITRETactic, MITRETechnique, ThreatStatus
)
from mock_data import MockDataStore
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent
from analyzers.fp_analyzer import FalsePositiveAnalyzer
from analyzers.response_engine import ResponseActionEngine
from analyzers.timeline_builder import TimelineBuilder
from telemetry import get_tracer

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
        use_mock: bool = False
    ):
        """Initialize coordinator with all specialized agents."""
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.mock_data = mock_data or MockDataStore()
        self.use_mock = use_mock

        # Initialize specialized agents
        self.historical_agent = HistoricalAgent(client=self.client)
        self.config_agent = ConfigAgent(client=self.client)
        self.devops_agent = DevOpsAgent(client=self.client)
        self.context_agent = ContextAgent(client=self.client)
        self.priority_agent = PriorityAgent(client=self.client)

        # Initialize analyzers
        self.fp_analyzer = FalsePositiveAnalyzer()
        self.response_engine = ResponseActionEngine()
        self.timeline_builder = TimelineBuilder()

        logger.info("🎯 Coordinator initialized with 5 specialized agents + 3 analyzers")
    
    async def analyze_threat(self, signal: ThreatSignal) -> ThreatAnalysis:
        """Perform comprehensive threat analysis using all agents in parallel."""
        # Create parent span for the entire threat analysis
        with tracer.start_as_current_span("analyze_threat") as span:
            # Set initial span attributes
            span.set_attribute("threat.type", signal.threat_type.value)
            span.set_attribute("customer.name", signal.customer_name)
            span.set_attribute("source.ip", signal.metadata.get("source_ip", "unknown"))

            logger.info("=" * 80)
            logger.info(f"🚨 NEW THREAT DETECTED: {signal.threat_type.value}")
            logger.info(f"   Customer: {signal.customer_name}")
            logger.info(f"   Signal ID: {signal.id}")
            logger.info("=" * 80)

            start_time = time.time()

            # Gather context for each agent
            logger.info("\n📊 GATHERING CONTEXT FOR AGENTS...")
            contexts = self._build_agent_contexts(signal)
            logger.info(f"   ✓ Historical: {len(contexts['historical'].get('similar_incidents', []))} similar incidents found")
            logger.info(f"   ✓ Config: Retrieved settings for {signal.customer_name}")
            logger.info(f"   ✓ DevOps: {len(contexts['devops'].get('infra_events', []))} recent infrastructure events")
            logger.info(f"   ✓ Context: {len(contexts['context'].get('news_items', []))} relevant news items")
            logger.info(f"   ✓ Priority: Context prepared for classification")

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

            # 3. Generate Response Plan
            with tracer.start_as_current_span("response_engine"):
                customer_config = contexts['config'].get('customer_config')
                response_plan = self.response_engine.generate_response_plan(
                    signal, severity, fp_score, customer_config, agent_analyses
                )
                logger.info(f"   ✓ Response Plan: {response_plan.primary_action.action_type.value} ({response_plan.primary_action.urgency.value})")

            # 4. Build Investigation Timeline
            with tracer.start_as_current_span("timeline_builder"):
                timeline = self.timeline_builder.build_timeline(
                    signal, agent_analyses, fp_score, response_plan, severity
                )
                logger.info(f"   ✓ Timeline: {len(timeline.events)} events")

            # Synthesize final analysis
            logger.info("\n🔬 SYNTHESIZING FINAL ANALYSIS...")
            total_time = int((time.time() - start_time) * 1000)

            final_analysis = self._synthesize_analysis(
                signal, agent_analyses, total_time, severity, fp_score, response_plan, timeline
            )

            # Set final span attributes
            span.set_attribute("threat.severity", severity.value)
            span.set_attribute("fp.score", fp_score.score)
            span.set_attribute("requires_review", final_analysis.requires_human_review)

            logger.info(f"\n✅ ANALYSIS COMPLETE")
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

                logger.info(f"   ✅ {agent_name} completed in {elapsed:.0f}ms")
                logger.info(f"      Confidence: {result.confidence:.2f}")
                logger.info(f"      Key Findings: {len(result.key_findings)}")

                return result
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                span.set_attribute("agent.error", str(e))
                logger.error(f"   ❌ {agent_name} failed after {elapsed:.0f}ms: {str(e)}")
                raise
    
    def _build_agent_contexts(self, signal: ThreatSignal) -> Dict[str, Dict[str, Any]]:
        """Build context data for each agent."""
        # Extract keywords for news search
        keywords = [signal.customer_name, signal.threat_type.value]
        if "crypto" in signal.customer_name.lower():
            keywords.append("bitcoin")
        
        return {
            "historical": {
                "similar_incidents": self.mock_data.get_similar_incidents(
                    signal.threat_type, signal.customer_name
                )
            },
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
        timeline
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

        # Generate executive summary
        all_findings = []
        for analysis in agent_analyses.values():
            all_findings.extend(analysis.key_findings)

        executive_summary = self._generate_executive_summary(
            signal, severity, all_findings[:5], fp_score
        )
        
        return ThreatAnalysis(
            signal=signal,
            status=ThreatStatus.COMPLETED,
            severity=severity,
            executive_summary=executive_summary,
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            customer_narrative=customer_narrative,
            agent_analyses=agent_analyses,
            false_positive_score=fp_score,
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
def create_coordinator(use_mock: bool = False) -> CoordinatorAgent:
    """Create a coordinator agent instance."""
    return CoordinatorAgent(use_mock=use_mock)

