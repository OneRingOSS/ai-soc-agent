"""Unit tests for Phase 3: Coordinated Attack Detection & Ensemble Validation.

Tests the AdversarialManipulationDetector's ability to detect:
1. Coordinated multi-agent attacks (Context + Historical simultaneously)
2. Priority Agent outliers (ensemble validation)
"""
import pytest
from models import (
    ThreatSignal, AgentAnalysis, ThreatSeverity,
    Contradiction, Anomaly
)
from analyzers.adversarial_detector import AdversarialManipulationDetector


class TestCoordinatedAttackDetection:
    """Test coordinated attack detection (Phase 3)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = AdversarialManipulationDetector()
    
    def _create_test_signal(self, **metadata_overrides):
        """Create a test threat signal."""
        metadata = {
            "source_ip": "203.0.113.50",
            "user_agent": "Mozilla/5.0",
            "geo_location": "San Francisco, CA",
            "request_count": 5
        }
        metadata.update(metadata_overrides)
        
        return ThreatSignal(
            signal_id="test-signal-123",
            customer_name="TestCorp",
            threat_type="anomaly_detection",
            payload="SELECT * FROM users",
            metadata=metadata,
            timestamp="2024-01-15T10:30:00Z"
        )
    
    # ========================================================================
    # Test 1: Coordinated Attack - Context + Historical Manipulation
    # ========================================================================
    def test_coordinated_attack_context_and_historical(self):
        """Test detection of coordinated Context + Historical manipulation."""
        
        # Arrange: Create signal with both Context and Historical anomalies
        signal = self._create_test_signal(
            source_ip="10.0.1.50",  # Private IP
            geo_location="San Francisco, CA",  # Public location (Geo-IP mismatch)
            user_agent="sqlmap/1.0"  # Attack tool
        )
        
        agent_analyses = {
            "context": AgentAnalysis(
                agent_name="context",
                analysis="Benign traffic from trusted source.",
                confidence=0.90,
                key_findings=["Trusted source"],
                recommendations=["Allow"],
                processing_time_ms=100
            ),
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Likely false positive. 95% FP rate. 50 similar incidents marked as FP.",
                confidence=0.88,
                key_findings=["High FP rate"],
                recommendations=["Ignore"],
                processing_time_ms=110
            ),
            "priority": AgentAnalysis(
                agent_name="priority",
                analysis="SQL injection attack detected.",
                confidence=0.95,
                key_findings=["SQL injection"],
                recommendations=["Block"],
                processing_time_ms=120
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="SQL injection attack detected.",
                confidence=0.95,
                key_findings=["SQL injection"],
                recommendations=["Block"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL
        
        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses=agent_analyses,
            severity=severity
        )
        
        # Assert
        assert result.manipulation_detected is True
        assert "coordinated_attack" in result.attack_vector
        
        # Should have Context-Priority contradiction
        context_contradictions = [c for c in result.contradictions if "context" in str(c.agents).lower()]
        assert len(context_contradictions) >= 1
        
        # Should have Historical-Priority contradiction
        historical_contradictions = [c for c in result.contradictions if "historical" in str(c.agents).lower()]
        assert len(historical_contradictions) >= 1
        
        # Should have Context metadata anomalies
        context_anomalies = [a for a in result.anomalies if "context_metadata" in a.type]
        assert len(context_anomalies) >= 1
        
        # Should have Historical data anomalies
        historical_anomalies = [a for a in result.anomalies if "historical_data" in a.type]
        assert len(historical_anomalies) >= 1
        
        # Should have coordinated attack anomaly
        coordinated_anomalies = [a for a in result.anomalies if a.type == "coordinated_attack"]
        assert len(coordinated_anomalies) == 1
        assert coordinated_anomalies[0].severity == "critical"
        assert "2 agents manipulated simultaneously" in coordinated_anomalies[0].description
        
        # Risk score should be high (multiple contradictions + anomalies)
        assert result.risk_score > 0.7
    
    # ========================================================================
    # Test 2: No Coordinated Attack - Only Context Manipulation
    # ========================================================================
    def test_no_coordinated_attack_single_agent(self):
        """Test that single agent manipulation doesn't trigger coordinated attack."""
        
        # Arrange: Only Context Agent manipulation
        signal = self._create_test_signal(
            source_ip="10.0.1.50",
            geo_location="San Francisco, CA"
        )
        
        agent_analyses = {
            "Context Agent": AgentAnalysis(
                agent_name="Context Agent",
                analysis="Benign traffic. Low risk.",
                confidence=0.90,
                key_findings=["Benign"],
                recommendations=["Allow"],
                processing_time_ms=100
            ),
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Real CRITICAL attack. 10% FP rate.",
                confidence=0.92,
                key_findings=["Real attack"],
                recommendations=["Block"],
                processing_time_ms=110
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL SQL injection detected.",
                confidence=0.95,
                key_findings=["SQL injection"],
                recommendations=["Block"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL

        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert
        assert result.manipulation_detected is True
        assert "context_agent" in result.attack_vector

        # Should NOT have coordinated attack anomaly (only 1 agent compromised)
        coordinated_anomalies = [a for a in result.anomalies if a.type == "coordinated_attack"]
        assert len(coordinated_anomalies) == 0


class TestEnsembleValidation:
    """Test ensemble validation / Priority Agent outlier detection (Phase 3)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = AdversarialManipulationDetector()

    def _create_test_signal(self):
        """Create a test threat signal."""
        return ThreatSignal(
            signal_id="test-signal-456",
            customer_name="TestCorp",
            threat_type="anomaly_detection",
            payload="SELECT * FROM users",
            metadata={
                "source_ip": "203.0.113.50",
                "user_agent": "Mozilla/5.0"
            },
            timestamp="2024-01-15T10:30:00Z"
        )

    # ========================================================================
    # Test 3: Priority Agent Outlier - 1 vs 4 Consensus
    # ========================================================================
    def test_priority_agent_outlier_detected(self):
        """Test detection when Priority Agent disagrees with 4 other agents."""

        # Arrange: 4 agents say CRITICAL, Priority says LOW (outlier)
        agent_analyses = {
            "Context Agent": AgentAnalysis(
                agent_name="Context Agent",
                analysis="CRITICAL attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                recommendations=["Block"],
                processing_time_ms=100
            ),
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Real CRITICAL attack.",
                confidence=0.88,
                key_findings=["Real attack"],
                recommendations=["Block"],
                processing_time_ms=110
            ),
            "Config Agent": AgentAnalysis(
                agent_name="Config Agent",
                analysis="CRITICAL policy violation.",
                confidence=0.85,
                key_findings=["Policy violation"],
                recommendations=["Block"],
                processing_time_ms=105
            ),
            "DevOps Agent": AgentAnalysis(
                agent_name="DevOps Agent",
                analysis="CRITICAL abnormal traffic.",
                confidence=0.87,
                key_findings=["Abnormal"],
                recommendations=["Block"],
                processing_time_ms=108
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Benign query. Low risk.",  # OUTLIER!
                confidence=0.95,
                key_findings=["Benign"],
                recommendations=["Allow"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL  # System severity (from consensus)

        # Act
        result = self.detector.analyze(
            signal=self._create_test_signal(),
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert
        assert result.manipulation_detected is True
        assert "priority_agent_outlier" in result.attack_vector

        # Should have Priority Agent outlier contradiction
        outlier_contradictions = [
            c for c in result.contradictions
            if c.metadata and "priority_severity" in c.metadata
        ]
        assert len(outlier_contradictions) == 1

        outlier = outlier_contradictions[0]
        assert "Priority Agent" in outlier.agents
        assert outlier.severity_mismatch is True
        assert outlier.confidence >= 0.8
        assert "outlier detected" in outlier.description.lower()
        assert "4 other agents agree" in outlier.description or "4 agents agree" in outlier.description

        # Check metadata
        assert outlier.metadata["priority_severity"] == "LOW"
        assert outlier.metadata["consensus_severity"] == "CRITICAL"
        assert outlier.metadata["consensus_count"] == 4

    # ========================================================================
    # Test 4: No Outlier - Priority Agrees with Consensus
    # ========================================================================
    def test_no_outlier_when_priority_agrees(self):
        """Test that no outlier is detected when Priority agrees with consensus."""

        # Arrange: All agents agree on CRITICAL
        agent_analyses = {
            "Context Agent": AgentAnalysis(
                agent_name="Context Agent",
                analysis="CRITICAL attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                recommendations=["Block"],
                processing_time_ms=100
            ),
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Real CRITICAL attack.",
                confidence=0.88,
                key_findings=["Real attack"],
                recommendations=["Block"],
                processing_time_ms=110
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="CRITICAL SQL injection detected.",
                confidence=0.95,
                key_findings=["SQL injection"],
                recommendations=["Block"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL

        # Act
        result = self.detector.analyze(
            signal=self._create_test_signal(),
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert - No outlier detection
        outlier_contradictions = [
            c for c in result.contradictions
            if c.metadata and "priority_severity" in c.metadata
        ]
        assert len(outlier_contradictions) == 0
        if result.attack_vector:
            assert "priority_agent_outlier" not in result.attack_vector

    # ========================================================================
    # Test 5: Insufficient Agents for Consensus
    # ========================================================================
    def test_no_outlier_insufficient_agents(self):
        """Test that outlier detection requires at least 3 agents."""

        # Arrange: Only 2 agents (not enough for consensus)
        agent_analyses = {
            "Context Agent": AgentAnalysis(
                agent_name="Context Agent",
                analysis="CRITICAL attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                recommendations=["Block"],
                processing_time_ms=100
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Benign query. Low risk.",
                confidence=0.95,
                key_findings=["Benign"],
                recommendations=["Allow"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL

        # Act
        result = self.detector.analyze(
            signal=self._create_test_signal(),
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert - No outlier detection (need 3+ agents)
        outlier_contradictions = [
            c for c in result.contradictions
            if c.metadata and "priority_severity" in c.metadata
        ]
        assert len(outlier_contradictions) == 0

    # ========================================================================
    # Test 6: Priority Agent Outlier - Minimum Consensus (3 agents)
    # ========================================================================
    def test_priority_agent_outlier_minimum_consensus(self):
        """Test outlier detection with minimum consensus (3 agents vs 1)."""

        # Arrange: 3 agents say CRITICAL, Priority says LOW
        agent_analyses = {
            "Context Agent": AgentAnalysis(
                agent_name="Context Agent",
                analysis="CRITICAL attack detected.",
                confidence=0.90,
                key_findings=["Attack"],
                recommendations=["Block"],
                processing_time_ms=100
            ),
            "Historical Agent": AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Real CRITICAL attack.",
                confidence=0.88,
                key_findings=["Real attack"],
                recommendations=["Block"],
                processing_time_ms=110
            ),
            "Config Agent": AgentAnalysis(
                agent_name="Config Agent",
                analysis="CRITICAL policy violation.",
                confidence=0.85,
                key_findings=["Policy violation"],
                recommendations=["Block"],
                processing_time_ms=105
            ),
            "Priority Agent": AgentAnalysis(
                agent_name="Priority Agent",
                analysis="Benign query. Low risk.",
                confidence=0.95,
                key_findings=["Benign"],
                recommendations=["Allow"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.CRITICAL

        # Act
        result = self.detector.analyze(
            signal=self._create_test_signal(),
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert - Should detect outlier with 3 vs 1
        outlier_contradictions = [
            c for c in result.contradictions
            if c.metadata and "priority_severity" in c.metadata
        ]
        assert len(outlier_contradictions) == 1
        assert outlier_contradictions[0].metadata["consensus_count"] == 3
