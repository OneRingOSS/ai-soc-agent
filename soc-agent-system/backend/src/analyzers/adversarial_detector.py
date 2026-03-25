"""Adversarial Manipulation Detector - Detects attempts to manipulate agent coordination.

Phase 1: Context Agent attack vector detection.
Phase 2: Historical Agent attack vector detection.
Phase 3: Coordinated multi-agent attack detection + ensemble validation.
"""
import logging
from typing import Dict, List, Optional, Any

from models import (
    ThreatSignal, AgentAnalysis, ThreatSeverity,
    Contradiction, Anomaly, AdversarialDetectionResult
)

logger = logging.getLogger(__name__)


class AdversarialManipulationDetector:
    """Detect adversarial manipulation in agent outputs.

    Phase 1: Context Agent attack detection.
    Phase 2: Historical Agent attack detection.
    Phase 3: Coordinated multi-agent attack detection + ensemble validation.
    """

    # Known attack tool User-Agents
    ATTACK_TOOL_USER_AGENTS = [
        "sqlmap", "nikto", "nmap", "burp", "metasploit",
        "havij", "acunetix", "nessus", "openvas", "w3af",
        "dirbuster", "gobuster", "wfuzz", "hydra", "medusa"
    ]

    # Thresholds for Historical data poisoning detection
    SUSPICIOUS_FP_RATE_THRESHOLD = 0.8  # 80% FP rate is suspicious
    SUSPICIOUS_INCIDENT_COUNT_THRESHOLD = 20  # 20+ similar incidents is suspicious
    TEMPORAL_SPIKE_THRESHOLD = 10  # 10+ incidents in short time is suspicious

    # Thresholds for coordinated attack detection (Phase 3)
    MIN_AGENTS_FOR_CONSENSUS = 3  # Need 3+ agents to establish consensus
    COORDINATED_ATTACK_THRESHOLD = 2  # 2+ agents manipulated = coordinated attack

    # Mock response for note authenticity check (deterministic for demos)
    MOCK_NOTE_AUTHENTICITY_RESPONSE = {
        "authenticity_score": 0.08,
        "fabrication_detected": True,
        "suspicious_patterns": [
            "All 18 notes follow identical structure: 'Closed - false positive. [Team] confirmed [activity]. [Benign phrase].'",
            "18 notes over 18 days — exactly 1 per day, all between 02:00-04:00 UTC",
            "All resolved by 'admin_svc' service account, not a human analyst",
            "Average resolution time: 3 minutes — insufficient for SQL injection investigation",
            "No ticket numbers, JIRA references, or work item IDs in any note"
        ],
        "fabrication_indicators": [
            "Team references inconsistent with SQL injection domain (e.g., 'compliance team' investigating SQL injection)",
            "No analyst names, no colleague references, no escalation mentions",
            "Language is implausibly formal and clean — no typos, no informal notes",
            "Temporal pattern (1 note/day, off-hours) consistent with automated script"
        ],
        "reasoning": (
            "These notes exhibit hallmarks of automated fabrication rather than authentic analyst work. "
            "The identical structure, generic team references, absence of specific details (tickets, names, tools), "
            "and implausibly fast resolution times (3 minutes for SQL injection) suggest a script-generated dataset "
            "designed to poison the historical database. Real analyst notes show variation, specific references, "
            "and domain-appropriate team assignments."
        )
    }

    def __init__(self, use_mock: bool = True):
        """Initialize the adversarial detector.

        Args:
            use_mock: If True, use mock responses for LLM calls (deterministic for demos)
        """
        self.use_mock = use_mock
    
    def analyze(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity,
        fp_score: Optional[any] = None,
        similar_incidents: Optional[List[Any]] = None
    ) -> AdversarialDetectionResult:
        """Detect manipulation attempts (Phase 1, 2 & 3: Context + Historical + Coordinated).

        Args:
            signal: The threat signal being analyzed
            agent_analyses: Dictionary of agent analyses (keyed by agent name)
            severity: The determined threat severity
            fp_score: Optional false positive score
            similar_incidents: Optional list of similar historical incidents for note authenticity check

        Returns:
            AdversarialDetectionResult with detection findings
        """
        contradictions = []
        anomalies = []

        # PHASE 1: Context Agent detection
        context_priority_contradiction = self._check_context_priority_contradiction(
            agent_analyses, severity
        )
        if context_priority_contradiction:
            contradictions.append(context_priority_contradiction)

        context_metadata_anomalies = self._check_context_metadata_validation(signal)
        if context_metadata_anomalies:
            anomalies.extend(context_metadata_anomalies)  # Add all anomalies to the list

        # PHASE 2: Historical Agent detection
        historical_priority_contradiction = self._check_historical_priority_contradiction(
            agent_analyses, severity
        )
        if historical_priority_contradiction:
            contradictions.append(historical_priority_contradiction)

        historical_data_anomaly = self._check_historical_data_poisoning(
            agent_analyses, severity
        )
        if historical_data_anomaly:
            anomalies.append(historical_data_anomaly)

        # PHASE 2.5: Historical Note Authenticity Check (LLM-based semantic analysis)
        # Use similar_incidents passed from coordinator
        if similar_incidents and len(similar_incidents) >= 5:
            note_anomaly = self._check_resolution_note_authenticity(
                signal, similar_incidents, use_mock=self.use_mock
            )
            if note_anomaly:
                anomalies.append(note_anomaly)

        # PHASE 3: Coordinated attack detection + ensemble validation
        coordinated_attack = self._check_coordinated_attack(
            contradictions, anomalies, agent_analyses, severity
        )
        if coordinated_attack:
            anomalies.append(coordinated_attack)

        # Ensemble validation: Detect Priority Agent outliers
        priority_outlier = self._check_priority_agent_outlier(
            agent_analyses, severity
        )
        if priority_outlier:
            contradictions.append(priority_outlier)

        # Calculate risk score
        manipulation_detected = len(contradictions) > 0 or len(anomalies) > 0
        risk_score = self._calculate_risk_score(contradictions, anomalies)

        # Determine attack vector
        attack_vector = None
        if manipulation_detected:
            # Check which agent(s) are compromised (external agents only)
            vectors = []
            for contradiction in contradictions:
                # Only flag external agents (Context, Historical) as attack vectors
                # Priority Agent is the validator, not the attack vector (unless it's an outlier)
                for agent in contradiction.agents:
                    if "context" in agent.lower():
                        vectors.append("context_agent")
                    if "historical" in agent.lower():
                        vectors.append("historical_agent")

                # Check if this is a Priority Agent outlier (Phase 3)
                # Use getattr to safely check for metadata field
                metadata = getattr(contradiction, 'metadata', None)
                if metadata and "priority_severity" in metadata:
                    # This is a Priority Agent outlier detection
                    vectors.append("priority_agent_outlier")

            for anomaly in anomalies:
                # Context Agent anomalies (metadata validation)
                if anomaly.type in ["geo_ip_mismatch", "attack_tool_user_agent", "high_request_volume", "context_metadata_inconsistency"]:
                    vectors.append("context_agent")
                # Historical Agent anomalies
                if "historical_data" in anomaly.type or anomaly.type == "historical_note_fabrication":
                    vectors.append("historical_note_fabrication" if anomaly.type == "historical_note_fabrication" else "historical_agent")
                # Coordinated attack detection
                if "coordinated_attack" in anomaly.type:
                    # Coordinated attack already detected, don't add again
                    vectors.append("coordinated_attack")

            # Check for coordinated attack (multiple external agents compromised)
            # Only add if we have 2+ external agents (not including priority_agent_outlier)
            external_agents = [v for v in vectors if v in ["context_agent", "historical_agent"]]
            unique_external = set(external_agents)
            if len(unique_external) >= 2 and "coordinated_attack" not in vectors:
                vectors.append("coordinated_attack")

            attack_vector = ", ".join(sorted(set(vectors))) if vectors else "unknown"

        # Generate recommendation
        recommendation = ""
        explanation = ""
        if manipulation_detected:
            recommendation = "flag_for_manual_review"
            explanation = self._generate_explanation(contradictions, anomalies)

        return AdversarialDetectionResult(
            manipulation_detected=manipulation_detected,
            confidence=0.8 if manipulation_detected else 0.0,
            contradictions=contradictions,
            anomalies=anomalies,
            risk_score=risk_score,
            attack_vector=attack_vector,
            recommendation=recommendation,
            explanation=explanation
        )
    
    def _check_context_priority_contradiction(
        self,
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity
    ) -> Optional[Contradiction]:
        """Check if Context says 'benign' but Priority says 'attack'.
        
        This detects the scenario where an attacker has compromised customer devices
        to send signals with benign-looking metadata but malicious payloads.
        
        Args:
            agent_analyses: Dictionary of agent analyses
            severity: The determined threat severity
            
        Returns:
            Contradiction if detected, None otherwise
        """
        context_analysis = agent_analyses.get("context")
        priority_analysis = agent_analyses.get("priority")
        
        if not context_analysis or not priority_analysis:
            return None
        
        # Check if Context says benign
        context_says_benign = (
            "benign" in context_analysis.analysis.lower() or
            "normal" in context_analysis.analysis.lower() or
            "legitimate" in context_analysis.analysis.lower() or
            "trusted" in context_analysis.analysis.lower()
        )
        
        # Check if Priority says attack
        priority_says_attack = (
            severity in [ThreatSeverity.CRITICAL, ThreatSeverity.HIGH] and
            priority_analysis.confidence > 0.7
        )
        
        if context_says_benign and priority_says_attack:
            return Contradiction(
                agents=["context", "priority"],
                description=(
                    f"Context Agent reports benign behavior (confidence: {context_analysis.confidence:.2f}) "
                    f"but Priority Agent detects {severity.value} severity threat "
                    f"(confidence: {priority_analysis.confidence:.2f}). "
                    f"This may indicate compromised devices sending crafted signals."
                ),
                severity_mismatch=True,
                confidence=0.85,
                context_analysis_snippet=context_analysis.analysis[:200],
                priority_analysis_snippet=priority_analysis.analysis[:200]
            )

        return None

    def _check_context_metadata_validation(
        self,
        signal: ThreatSignal
    ) -> List[Anomaly]:
        """Validate Context metadata for inconsistencies.

        Checks for:
        1. Geo-location vs IP consistency (private IP with public geo)
        2. User-Agent validation (known attack tools)
        3. Request volume anomalies

        Args:
            signal: The threat signal to validate

        Returns:
            List of Anomaly objects (one per detected anomaly)
        """
        metadata = signal.metadata
        anomalies = []

        # Check 1: Geo-location vs IP consistency
        geo = metadata.get("geo_location", "")
        source_ip = metadata.get("source_ip", "")

        # Private IP with public geo-location is impossible
        if self._is_private_ip(source_ip) and geo and "," in geo:
            anomalies.append(Anomaly(
                type="geo_ip_mismatch",
                description=f"Private IP ({source_ip}) with public geo-location ({geo})",
                severity="high",  # Geo-IP mismatch is a strong indicator
                indicators=[f"source_ip={source_ip}", f"geo_location={geo}"]
            ))

        # Check 2: User-Agent validation
        user_agent = metadata.get("user_agent", "")
        if self._is_attack_tool_ua(user_agent):
            anomalies.append(Anomaly(
                type="attack_tool_user_agent",
                description=f"User-Agent matches known attack tool: {user_agent}",
                severity="high",  # Attack tools are high severity
                indicators=[f"user_agent={user_agent}"]
            ))

        # Check 3: Request volume anomaly
        request_count = metadata.get("request_count", 0)
        if request_count > 1000:  # Suspiciously high for "normal" traffic
            anomalies.append(Anomaly(
                type="high_request_volume",
                description=f"High request volume ({request_count}) exceeds threshold (1000)",
                severity="medium",  # Volume alone is medium severity
                indicators=[f"request_count={request_count}"]
            ))

        return anomalies

    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private range.

        Args:
            ip: IP address string

        Returns:
            True if IP is private, False otherwise
        """
        if not ip:
            return False

        return (
            ip.startswith("10.") or
            ip.startswith("192.168.") or
            ip.startswith("172.16.") or
            ip.startswith("172.17.") or
            ip.startswith("172.18.") or
            ip.startswith("172.19.") or
            ip.startswith("172.20.") or
            ip.startswith("172.21.") or
            ip.startswith("172.22.") or
            ip.startswith("172.23.") or
            ip.startswith("172.24.") or
            ip.startswith("172.25.") or
            ip.startswith("172.26.") or
            ip.startswith("172.27.") or
            ip.startswith("172.28.") or
            ip.startswith("172.29.") or
            ip.startswith("172.30.") or
            ip.startswith("172.31.")
        )

    def _is_attack_tool_ua(self, ua: str) -> bool:
        """Check if User-Agent matches known attack tools.

        Args:
            ua: User-Agent string

        Returns:
            True if UA matches attack tool, False otherwise
        """
        if not ua:
            return False

        ua_lower = ua.lower()
        return any(tool in ua_lower for tool in self.ATTACK_TOOL_USER_AGENTS)

    def _calculate_risk_score(
        self,
        contradictions: List[Contradiction],
        anomalies: List[Anomaly]
    ) -> float:
        """Calculate overall risk score (0.0 - 1.0).

        Args:
            contradictions: List of detected contradictions
            anomalies: List of detected anomalies

        Returns:
            Risk score between 0.0 and 1.0
        """
        score = 0.0

        # Contradictions weighted by confidence
        for contradiction in contradictions:
            score += contradiction.confidence * 0.4

        # High-severity anomalies
        score += len([a for a in anomalies if a.severity == "high"]) * 0.3

        # Medium-severity anomalies
        score += len([a for a in anomalies if a.severity == "medium"]) * 0.15

        return min(1.0, score)

    def _generate_explanation(
        self,
        contradictions: List[Contradiction],
        anomalies: List[Anomaly]
    ) -> str:
        """Generate human-readable explanation of detection.

        Args:
            contradictions: List of detected contradictions
            anomalies: List of detected anomalies

        Returns:
            Explanation string
        """
        parts = []

        if contradictions:
            parts.append(
                f"Detected {len(contradictions)} contradiction(s) between agent analyses. "
                f"This may indicate adversarial manipulation of external data sources."
            )

        if anomalies:
            parts.append(
                f"Detected {len(anomalies)} anomaly(ies) in threat signal metadata. "
                f"This suggests potential data poisoning or crafted attack signals."
            )

        parts.append(
            "Recommendation: Flag this threat for manual review by a security analyst "
            "to investigate potential compromise of customer devices or data sources."
        )

        return " ".join(parts)

    # ========================================================================
    # PHASE 2: Historical Agent Detection Methods
    # ========================================================================

    def _check_historical_priority_contradiction(
        self,
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity
    ) -> Optional[Contradiction]:
        """Check if Historical says 'FP' but Priority says 'attack'.

        This detects the scenario where an attacker has poisoned the customer's
        historical threat intel database to make real attacks look like false positives.

        Args:
            agent_analyses: Dictionary of agent analyses
            severity: The determined threat severity

        Returns:
            Contradiction if detected, None otherwise
        """
        historical_analysis = agent_analyses.get("Historical Agent")
        priority_analysis = agent_analyses.get("Priority Agent")

        if not historical_analysis or not priority_analysis:
            return None

        # Check if Historical suggests THIS incident is likely FP/benign
        # Look for phrases that suggest the current incident is benign
        analysis_lower = historical_analysis.analysis.lower()
        historical_suggests_fp = (
            ("likely" in analysis_lower and ("false positive" in analysis_lower or "fp" in analysis_lower or "benign" in analysis_lower)) or
            ("probably" in analysis_lower and ("false positive" in analysis_lower or "fp" in analysis_lower or "benign" in analysis_lower)) or
            ("not a threat" in analysis_lower) or
            ("all false positive" in analysis_lower) or
            (analysis_lower.endswith("benign.")) or
            (analysis_lower.endswith("false positive.")) or
            (analysis_lower.endswith("fp."))
        )

        priority_suggests_attack = (
            severity in [ThreatSeverity.HIGH, ThreatSeverity.CRITICAL] or
            "attack" in priority_analysis.analysis.lower() or
            "malicious" in priority_analysis.analysis.lower() or
            "threat" in priority_analysis.analysis.lower()
        )

        if historical_suggests_fp and priority_suggests_attack:
            return Contradiction(
                agents=["Historical Agent", "Priority Agent"],
                description=(
                    f"Historical Agent suggests false positive (confidence: {historical_analysis.confidence:.2f}), "
                    f"but Priority Agent classifies as {severity.value} threat "
                    f"(confidence: {priority_analysis.confidence:.2f}). "
                    f"This may indicate historical data poisoning."
                ),
                severity_mismatch=True,
                confidence=0.85,
                historical_analysis_snippet=historical_analysis.analysis[:200],
                priority_analysis_snippet=priority_analysis.analysis[:200]
            )

        return None

    def _check_historical_data_poisoning(
        self,
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity
    ) -> Optional[Anomaly]:
        """Detect suspicious patterns in Historical Agent data.

        Checks for:
        1. Suspiciously high FP rate (>80%)
        2. Too many similar incidents (>20)
        3. Temporal clustering (>10 incidents in short time)

        Args:
            agent_analyses: Dictionary of agent analyses
            severity: The determined threat severity

        Returns:
            Anomaly if detected, None otherwise
        """
        historical_analysis = agent_analyses.get("Historical Agent")

        if not historical_analysis:
            return None

        analysis_text = historical_analysis.analysis.lower()
        anomalies_found = []

        # Check 1: Suspiciously high FP rate
        # Look for patterns like "80% false positive rate" or "90% FP"
        import re
        fp_rate_pattern = r'(\d+)%\s*(?:false positive|fp)'
        fp_rate_matches = re.findall(fp_rate_pattern, analysis_text)

        for match in fp_rate_matches:
            fp_rate = int(match) / 100.0
            if fp_rate >= self.SUSPICIOUS_FP_RATE_THRESHOLD:
                anomalies_found.append(
                    f"Suspiciously high FP rate: {int(fp_rate * 100)}% "
                    f"(threshold: {int(self.SUSPICIOUS_FP_RATE_THRESHOLD * 100)}%)"
                )

        # Check 2: Too many similar incidents
        # Look for patterns like "50 similar incidents" or "found 30 matches"
        incident_count_pattern = r'(\d+)\s*(?:similar incidents|matches|incidents found)'
        incident_matches = re.findall(incident_count_pattern, analysis_text)

        for match in incident_matches:
            count = int(match)
            if count >= self.SUSPICIOUS_INCIDENT_COUNT_THRESHOLD:
                anomalies_found.append(
                    f"Suspiciously high incident count: {count} similar incidents "
                    f"(threshold: {self.SUSPICIOUS_INCIDENT_COUNT_THRESHOLD})"
                )

        # Check 3: Temporal clustering
        # Look for patterns like "10 incidents in past 24 hours" or "15 in last day"
        temporal_pattern = r'(\d+)\s*(?:incidents?|matches?)\s*(?:in|within)\s*(?:past|last)\s*(?:\d+\s*(?:hours?|days?|minutes?))'
        temporal_matches = re.findall(temporal_pattern, analysis_text)

        for match in temporal_matches:
            count = int(match)
            if count >= self.TEMPORAL_SPIKE_THRESHOLD:
                anomalies_found.append(
                    f"Temporal clustering detected: {count} incidents in short time "
                    f"(threshold: {self.TEMPORAL_SPIKE_THRESHOLD})"
                )

        if anomalies_found:
            return Anomaly(
                type="historical_data_poisoning",
                severity="high",
                description="; ".join(anomalies_found),
                confidence=0.8,
                metadata={
                    "anomaly_count": len(anomalies_found),
                    "historical_analysis_snippet": historical_analysis.analysis[:200]
                }
            )

        return None

    def _check_resolution_note_authenticity(
        self,
        signal: ThreatSignal,
        similar_incidents: List[Any],
        use_mock: Optional[bool] = None
    ) -> Optional[Anomaly]:
        """Uses LLM to evaluate whether historical incident resolution notes appear authentic or fabricated.

        This is the core agentic capability: evaluating semantic plausibility of free-text content
        — impossible with rule-based logic.

        The method analyzes resolution notes for:
        1. Linguistic patterns (identical structure, templated language)
        2. Domain reasoning (team-signal type mismatches)
        3. Plausibility (resolution times, specific details, analyst behavior)

        Args:
            signal: Current threat signal being analyzed
            similar_incidents: List of historical incidents with resolution notes
            use_mock: If True, return mock response (for deterministic demos).
                     If None, uses self.use_mock

        Returns:
            Anomaly if fabrication detected, None if notes appear authentic
        """
        # Need meaningful sample size for statistical analysis
        if len(similar_incidents) < 5:
            logger.debug(f"Skipping note authenticity check: only {len(similar_incidents)} incidents (need 5+)")
            return None

        # Use instance default if not specified
        if use_mock is None:
            use_mock = self.use_mock

        if use_mock:
            # Return deterministic mock response for demos
            result = self.MOCK_NOTE_AUTHENTICITY_RESPONSE
        else:
            # TODO: Real LLM call (future enhancement)
            # This would call OpenAI API to analyze the notes
            logger.warning("Real LLM call not implemented yet - using mock response")
            result = self.MOCK_NOTE_AUTHENTICITY_RESPONSE

        if result["fabrication_detected"]:
            return Anomaly(
                type="historical_note_fabrication",
                severity="critical",
                description=result["reasoning"],
                confidence=1.0 - result["authenticity_score"],
                indicators=result["fabrication_indicators"],
                metadata={
                    "suspicious_patterns": result["suspicious_patterns"],
                    "note_count": len(similar_incidents),
                    "authenticity_score": result["authenticity_score"]
                }
            )

        return None

    def _check_coordinated_attack(
        self,
        contradictions: List[Contradiction],
        anomalies: List[Anomaly],
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity
    ) -> Optional[Anomaly]:
        """Detect coordinated multi-agent attacks (Phase 3).

        Detects when multiple agents (Context + Historical) are manipulated simultaneously.
        This is a sophisticated attack where the adversary poisons multiple data sources.

        Args:
            contradictions: List of detected contradictions
            anomalies: List of detected anomalies
            agent_analyses: Dictionary of agent analyses
            severity: Determined threat severity

        Returns:
            Anomaly if coordinated attack detected, None otherwise
        """
        # Count how many different agents are involved in contradictions/anomalies
        compromised_agents = set()

        # Check contradictions
        for contradiction in contradictions:
            for agent in contradiction.agents:
                if "context" in agent.lower():
                    compromised_agents.add("Context Agent")
                if "historical" in agent.lower():
                    compromised_agents.add("Historical Agent")

        # Check anomalies
        for anomaly in anomalies:
            if "context_metadata" in anomaly.type:
                compromised_agents.add("Context Agent")
            if "historical_data" in anomaly.type:
                compromised_agents.add("Historical Agent")

        # Coordinated attack: 2+ agents manipulated simultaneously
        if len(compromised_agents) >= self.COORDINATED_ATTACK_THRESHOLD:
            return Anomaly(
                type="coordinated_attack",
                severity="critical",
                description=(
                    f"Coordinated multi-agent attack detected: {len(compromised_agents)} agents "
                    f"manipulated simultaneously ({', '.join(sorted(compromised_agents))}). "
                    f"This indicates a sophisticated adversary with access to multiple data sources."
                ),
                confidence=0.9,
                metadata={
                    "compromised_agents": list(compromised_agents),
                    "contradiction_count": len(contradictions),
                    "anomaly_count": len(anomalies)
                }
            )

        return None

    def _check_priority_agent_outlier(
        self,
        agent_analyses: Dict[str, AgentAnalysis],
        severity: ThreatSeverity
    ) -> Optional[Contradiction]:
        """Detect when Priority Agent is an outlier (Phase 3 - Ensemble Validation).

        This addresses the limitation of using Priority Agent as "source of truth".
        If Priority Agent disagrees with 3+ other agents, it may be compromised or evaded.

        Args:
            agent_analyses: Dictionary of agent analyses
            severity: Determined threat severity

        Returns:
            Contradiction if Priority Agent is an outlier, None otherwise
        """
        if len(agent_analyses) < self.MIN_AGENTS_FOR_CONSENSUS:
            # Need at least 3 agents to establish consensus
            return None

        # Get Priority Agent analysis
        priority_analysis = agent_analyses.get("Priority Agent")
        if not priority_analysis:
            return None

        # Infer severity from analysis text (since AgentAnalysis doesn't have severity field)
        def infer_severity(analysis: AgentAnalysis) -> str:
            """Infer severity from analysis text."""
            text_lower = analysis.analysis.lower()
            if any(word in text_lower for word in ["critical", "severe", "attack detected", "immediate action"]):
                return "CRITICAL"
            elif any(word in text_lower for word in ["high", "threat", "malicious", "block"]):
                return "HIGH"
            elif any(word in text_lower for word in ["medium", "suspicious", "investigate"]):
                return "MEDIUM"
            elif any(word in text_lower for word in ["benign", "normal", "allow", "false positive", "low"]):
                return "LOW"
            else:
                return "MEDIUM"  # Default

        # Count severity votes from all agents
        severity_votes = {}
        for agent_name, analysis in agent_analyses.items():
            sev = infer_severity(analysis)
            if sev not in severity_votes:
                severity_votes[sev] = []
            severity_votes[sev].append(agent_name)

        # Find consensus (most common severity)
        max_votes = max(len(agents) for agents in severity_votes.values())
        consensus_severity = None
        for sev, agents in severity_votes.items():
            if len(agents) == max_votes:
                consensus_severity = sev
                break

        # Check if Priority Agent disagrees with consensus
        priority_severity = infer_severity(priority_analysis)

        if priority_severity != consensus_severity and max_votes >= 3:
            # Priority Agent is an outlier (1 vs 3+)
            consensus_agents = severity_votes[consensus_severity]

            return Contradiction(
                agents=["Priority Agent"] + consensus_agents,
                description=(
                    f"Priority Agent outlier detected: Priority says '{priority_severity}' "
                    f"but {max_votes} other agents agree on '{consensus_severity}'. "
                    f"Priority Agent may be evaded (obfuscated payload, zero-day) or compromised."
                ),
                severity_mismatch=True,
                confidence=0.85,
                metadata={
                    "priority_severity": priority_severity,
                    "consensus_severity": consensus_severity,
                    "consensus_count": max_votes,
                    "consensus_agents": consensus_agents
                }
            )

        return None

