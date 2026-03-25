"""Unit tests for Historical Agent adversarial detection (Phase 2).

Tests the detector's ability to identify Historical Agent data poisoning attacks.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from analyzers.adversarial_detector import AdversarialManipulationDetector
from models import ThreatSignal, AgentAnalysis, ThreatSeverity, ThreatType
from datetime import datetime


class TestHistoricalAgentDetection:
    """Test Historical Agent adversarial attack detection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = AdversarialManipulationDetector()
        self.signal = ThreatSignal(
            threat_type=ThreatType.ANOMALY_DETECTION,
            customer_name="TestCorp",
            timestamp=datetime.now(),
            metadata={"source_ip": "203.0.113.50"}
        )
    
    def test_historical_priority_contradiction_detected(self):
        """Test detection of Historical-Priority contradiction."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 50 similar incidents. All resolved as false positive. Historical FP rate: 100%. Likely benign.",
                confidence=0.92,
                key_findings=["High FP rate"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL: SQL injection attack detected. Malicious payload confirmed.",
                confidence=0.94,
                key_findings=["SQL injection"],
                processing_time_ms=100
            )
        }
        
        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.CRITICAL
        )
        
        assert result.manipulation_detected is True
        assert len(result.contradictions) == 1
        assert "Historical Agent" in result.contradictions[0].agents
        assert "Priority Agent" in result.contradictions[0].agents
        assert "historical data poisoning" in result.contradictions[0].description.lower()
    
    def test_no_contradiction_when_agents_agree(self):
        """Test no false positives when Historical and Priority agree."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 5 similar incidents. All confirmed as attacks. High threat pattern.",
                confidence=0.88,
                key_findings=["Attack pattern"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL: SQL injection attack detected.",
                confidence=0.94,
                key_findings=["SQL injection"],
                processing_time_ms=100
            )
        }
        
        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.CRITICAL
        )
        
        # Should not detect contradiction when agents agree
        historical_contradictions = [c for c in result.contradictions if c.type == "historical_priority_contradiction"]
        assert len(historical_contradictions) == 0
    
    def test_high_fp_rate_anomaly_detected(self):
        """Test detection of suspiciously high FP rate."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 30 similar incidents with 95% false positive rate in past 7 days.",
                confidence=0.85,
                key_findings=["High FP rate"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="SQL injection detected.",
                confidence=0.90,
                key_findings=["SQL injection"],
                processing_time_ms=100
            )
        }
        
        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.HIGH
        )
        
        assert result.manipulation_detected is True
        assert len(result.anomalies) > 0
        
        historical_anomalies = [a for a in result.anomalies if a.type == "historical_data_poisoning"]
        assert len(historical_anomalies) == 1
        assert "95%" in historical_anomalies[0].description
        assert "fp rate" in historical_anomalies[0].description.lower()
    
    def test_high_incident_count_anomaly_detected(self):
        """Test detection of suspiciously high incident count."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 50 similar incidents in database. Pattern matches current threat.",
                confidence=0.87,
                key_findings=["50 incidents"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }
        
        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.MEDIUM
        )
        
        assert result.manipulation_detected is True
        historical_anomalies = [a for a in result.anomalies if a.type == "historical_data_poisoning"]
        assert len(historical_anomalies) == 1
        assert "50 similar incidents" in historical_anomalies[0].description
    
    def test_temporal_clustering_anomaly_detected(self):
        """Test detection of temporal clustering (spike in incidents)."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 15 incidents in past 24 hours with similar characteristics.",
                confidence=0.86,
                key_findings=["Temporal spike"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }
        
        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.MEDIUM
        )
        
        assert result.manipulation_detected is True
        historical_anomalies = [a for a in result.anomalies if a.type == "historical_data_poisoning"]
        assert len(historical_anomalies) == 1
        assert "15 incidents" in historical_anomalies[0].description
        assert "temporal clustering" in historical_anomalies[0].description.lower()

    def test_multiple_anomalies_detected(self):
        """Test detection of multiple Historical anomalies simultaneously."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 40 similar incidents with 90% FP rate. 12 incidents in past 6 hours.",
                confidence=0.88,
                key_findings=["Multiple anomalies"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.HIGH
        )

        assert result.manipulation_detected is True
        historical_anomalies = [a for a in result.anomalies if a.type == "historical_data_poisoning"]
        assert len(historical_anomalies) == 1

        # Should detect all three anomaly types
        description = historical_anomalies[0].description
        assert "90%" in description  # FP rate
        assert "40 similar incidents" in description  # Incident count
        assert "12 incidents" in description  # Temporal clustering

    def test_combined_contradiction_and_anomaly(self):
        """Test detection of both contradiction and anomaly."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 35 similar incidents with 85% false positive rate. Likely benign.",
                confidence=0.90,
                key_findings=["High FP rate", "Benign"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL: Malicious SQL injection attack.",
                confidence=0.95,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.CRITICAL
        )

        assert result.manipulation_detected is True
        assert len(result.contradictions) == 1  # Historical-Priority contradiction
        assert len(result.anomalies) >= 1  # Historical data poisoning
        assert result.risk_score > 0.5  # High risk due to multiple detections
        assert "historical_agent" in result.attack_vector

    def test_attack_vector_identification(self):
        """Test correct identification of Historical Agent as attack vector."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 25 similar incidents. All false positives.",
                confidence=0.88,
                key_findings=["FP pattern"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Attack detected.",
                confidence=0.92,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.HIGH
        )

        assert result.manipulation_detected is True
        assert result.attack_vector is not None
        assert "historical_agent" in result.attack_vector

    def test_risk_score_calculation_with_historical(self):
        """Test risk score calculation for Historical attacks."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 30 similar incidents with 90% FP. Benign.",
                confidence=0.90,
                key_findings=["High FP"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL attack.",
                confidence=0.95,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.CRITICAL
        )

        assert result.manipulation_detected is True
        assert result.risk_score > 0.0
        assert result.risk_score <= 1.0
        # High severity contradiction + high severity anomaly should give significant risk
        assert result.risk_score >= 0.5

    def test_explanation_generation_for_historical(self):
        """Test explanation generation for Historical attacks."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 40 similar incidents with 95% FP rate. Benign.",
                confidence=0.92,
                key_findings=["High FP"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL attack.",
                confidence=0.94,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.CRITICAL
        )

        assert result.manipulation_detected is True
        assert result.explanation is not None
        assert len(result.explanation) > 0
        assert "contradiction" in result.explanation.lower() or "anomaly" in result.explanation.lower()
        assert "manual review" in result.explanation.lower()

    def test_no_false_positives_on_clean_historical_data(self):
        """Test no false positives when Historical data is clean."""
        agent_analyses = {
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Found 3 similar incidents. 2 confirmed attacks, 1 false positive. Normal pattern.",
                confidence=0.85,
                key_findings=["Normal pattern"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                processing_time_ms=100
            )
        }

        result = self.detector.analyze(
            self.signal,
            agent_analyses,
            ThreatSeverity.MEDIUM
        )

        # Should not detect Historical manipulation
        historical_contradictions = [c for c in result.contradictions if "Historical Agent" in c.agents]
        historical_anomalies = [a for a in result.anomalies if a.type == "historical_data_poisoning"]

        assert len(historical_contradictions) == 0
        assert len(historical_anomalies) == 0

