"""Unit tests for AdversarialManipulationDetector - Context Agent attack vector.

Phase 1A: Test detector logic in isolation before integration.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from analyzers.adversarial_detector import AdversarialManipulationDetector
from models import ThreatSignal, AgentAnalysis, ThreatSeverity, ThreatType
from datetime import datetime


class TestAdversarialDetectorContext:
    """Unit tests for Context Agent adversarial detection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = AdversarialManipulationDetector()
    
    # ========================================================================
    # Test 1: Context-Priority Contradiction Detection
    # ========================================================================
    def test_context_priority_contradiction_detected(self):
        """Test that contradiction is detected when Context says benign but Priority says attack."""
        
        # Arrange
        agent_analyses = {
            "context": AgentAnalysis(
                agent_name="context",
                analysis="Normal user behavior from trusted internal network. Legitimate browser activity.",
                confidence=0.88,
                key_findings=["Trusted IP range", "Normal request volume"],
                recommendations=["No action needed"],
                processing_time_ms=100
            ),
            "priority": AgentAnalysis(
                agent_name="priority",
                analysis="CRITICAL SQL injection attack detected. Immediate action required.",
                confidence=0.94,
                key_findings=["SQL injection payload", "MITRE T1190"],
                recommendations=["Block immediately"],
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
        
        # Assert
        assert result.manipulation_detected is True
        assert result.attack_vector == "context_agent"
        assert len(result.contradictions) == 1
        assert result.contradictions[0].agents == ["context", "priority"]
        assert result.contradictions[0].severity_mismatch is True
        assert result.contradictions[0].confidence >= 0.8  # High confidence
        assert result.risk_score > 0.3  # Should have significant risk score
        assert "Context Agent reports benign" in result.contradictions[0].description
        assert "Priority Agent detects CRITICAL" in result.contradictions[0].description
    
    # ========================================================================
    # Test 2: No False Positives When Agents Agree
    # ========================================================================
    def test_no_false_positive_when_agents_agree(self):
        """Test that no contradiction is detected when agents agree."""
        
        # Arrange - Both agents agree it's an attack
        agent_analyses = {
            "context": AgentAnalysis(
                agent_name="context",
                analysis="Suspicious activity detected from unknown source.",
                confidence=0.85,
                key_findings=["Unknown IP", "High request volume"],
                recommendations=["Investigate"],
                processing_time_ms=100
            ),
            "priority": AgentAnalysis(
                agent_name="priority",
                analysis="CRITICAL SQL injection attack detected.",
                confidence=0.94,
                key_findings=["SQL injection payload"],
                recommendations=["Block immediately"],
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
        
        # Assert
        assert result.manipulation_detected is False
        assert len(result.contradictions) == 0
        assert result.risk_score == 0.0
        assert result.attack_vector is None
    
    # ========================================================================
    # Test 3: Geo-IP Mismatch Detection
    # ========================================================================
    def test_geo_ip_mismatch_detected(self):
        """Test that geo-IP mismatch is detected."""
        
        # Arrange
        signal = self._create_test_signal()
        signal.metadata["geo_location"] = "Tokyo, Japan"
        signal.metadata["source_ip"] = "192.168.1.1"  # Private IP
        
        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses={},
            severity=ThreatSeverity.MEDIUM
        )
        
        # Assert
        assert result.manipulation_detected is True
        assert len(result.anomalies) == 1
        assert result.anomalies[0].type == "context_metadata_inconsistency"
        assert "Private IP" in result.anomalies[0].description
        assert "Tokyo, Japan" in result.anomalies[0].description
        assert result.anomalies[0].severity == "medium"
    
    # ========================================================================
    # Test 4: Attack Tool User-Agent Detection
    # ========================================================================
    def test_attack_tool_user_agent_detected(self):
        """Test that attack tool User-Agent is detected."""
        
        # Arrange
        signal = self._create_test_signal()
        signal.metadata["user_agent"] = "sqlmap/1.5.12"
        
        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses={},
            severity=ThreatSeverity.MEDIUM
        )
        
        # Assert
        assert result.manipulation_detected is True
        assert len(result.anomalies) == 1
        assert "attack tool" in result.anomalies[0].description.lower()
        assert "sqlmap" in result.anomalies[0].description

    # ========================================================================
    # Test 5: High Request Volume Anomaly
    # ========================================================================
    def test_high_request_volume_anomaly_detected(self):
        """Test that high request volume is flagged as anomaly."""

        # Arrange
        signal = self._create_test_signal()
        signal.metadata["request_count"] = 5000  # Suspiciously high

        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses={},
            severity=ThreatSeverity.MEDIUM
        )

        # Assert
        assert result.manipulation_detected is True
        assert len(result.anomalies) == 1
        assert "High request volume" in result.anomalies[0].description
        assert "5000" in result.anomalies[0].description

    # ========================================================================
    # Test 6: Multiple Anomalies Detected
    # ========================================================================
    def test_multiple_anomalies_detected(self):
        """Test that multiple anomalies are detected and risk score increases."""

        # Arrange
        signal = self._create_test_signal()
        signal.metadata["geo_location"] = "London, UK"
        signal.metadata["source_ip"] = "10.0.0.1"  # Private IP
        signal.metadata["user_agent"] = "nikto/2.1.6"  # Attack tool
        signal.metadata["request_count"] = 2000  # High volume

        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses={},
            severity=ThreatSeverity.MEDIUM
        )

        # Assert
        assert result.manipulation_detected is True
        assert len(result.anomalies) == 1  # All combined into one anomaly
        assert len(result.anomalies[0].indicators) == 3  # 3 indicators
        assert "Private IP" in result.anomalies[0].description
        assert "nikto" in result.anomalies[0].description
        assert "High request volume" in result.anomalies[0].description

    # ========================================================================
    # Test 7: Risk Score Calculation
    # ========================================================================
    def test_risk_score_calculation(self):
        """Test that risk score is calculated correctly."""

        # Arrange - Create both contradiction and anomaly
        signal = self._create_test_signal()
        signal.metadata["user_agent"] = "sqlmap/1.0"

        agent_analyses = {
            "context": AgentAnalysis(
                agent_name="context",
                analysis="Benign traffic from trusted source.",
                confidence=0.90,
                key_findings=["Trusted IP"],
                recommendations=["Allow"],
                processing_time_ms=100
            ),
            "priority": AgentAnalysis(
                agent_name="priority",
                analysis="CRITICAL attack detected.",
                confidence=0.95,
                key_findings=["Attack signature"],
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
        assert len(result.contradictions) == 1  # High confidence contradiction
        assert len(result.anomalies) == 1  # Medium severity anomaly
        # Risk score = 1 contradiction (confidence 0.85 * 0.4) + 1 medium anomaly (0.15) = 0.49
        assert result.risk_score >= 0.45
        assert result.risk_score <= 0.55

    # ========================================================================
    # Test 8: Explanation Generation
    # ========================================================================
    def test_explanation_generation(self):
        """Test that explanation is generated correctly."""

        # Arrange
        signal = self._create_test_signal()
        signal.metadata["user_agent"] = "burp/2.0"

        agent_analyses = {
            "context": AgentAnalysis(
                agent_name="context",
                analysis="Normal behavior detected.",
                confidence=0.85,
                key_findings=["Normal pattern"],
                recommendations=["Monitor"],
                processing_time_ms=100
            ),
            "priority": AgentAnalysis(
                agent_name="priority",
                analysis="HIGH severity attack.",
                confidence=0.90,
                key_findings=["Attack pattern"],
                recommendations=["Block"],
                processing_time_ms=120
            )
        }
        severity = ThreatSeverity.HIGH

        # Act
        result = self.detector.analyze(
            signal=signal,
            agent_analyses=agent_analyses,
            severity=severity
        )

        # Assert
        assert result.manipulation_detected is True
        assert result.explanation != ""
        assert "contradiction" in result.explanation.lower()
        assert "anomaly" in result.explanation.lower()
        assert "manual review" in result.explanation.lower()
        assert result.recommendation == "flag_for_manual_review"

    # ========================================================================
    # Test 9: Private IP Detection
    # ========================================================================
    def test_private_ip_detection(self):
        """Test that private IP ranges are correctly identified."""

        # Test various private IP ranges
        private_ips = [
            "10.0.0.1",
            "10.255.255.255",
            "192.168.1.1",
            "192.168.255.255",
            "172.16.0.1",
            "172.31.255.255"
        ]

        for ip in private_ips:
            assert self.detector._is_private_ip(ip) is True, f"{ip} should be private"

        # Test public IPs
        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
            "203.0.113.1"
        ]

        for ip in public_ips:
            assert self.detector._is_private_ip(ip) is False, f"{ip} should be public"

    # ========================================================================
    # Test 10: Attack Tool UA Detection
    # ========================================================================
    def test_attack_tool_ua_detection(self):
        """Test that attack tool User-Agents are correctly identified."""

        # Test attack tools
        attack_uas = [
            "sqlmap/1.5.12",
            "Nikto/2.1.6",
            "Nmap Scripting Engine",
            "Burp Suite Professional",
            "Metasploit Framework"
        ]

        for ua in attack_uas:
            assert self.detector._is_attack_tool_ua(ua) is True, f"{ua} should be detected"

        # Test legitimate UAs
        legitimate_uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "curl/7.68.0",
            "Python-requests/2.28.0"
        ]

        for ua in legitimate_uas:
            assert self.detector._is_attack_tool_ua(ua) is False, f"{ua} should not be detected"

    # ========================================================================
    # Helper Methods
    # ========================================================================
    def _create_test_signal(self) -> ThreatSignal:
        """Create a test threat signal with valid metadata (no anomalies)."""
        return ThreatSignal(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            metadata={
                "source_ip": "203.0.113.50",  # Public IP (no geo mismatch)
                "user_agent": "Mozilla/5.0",
                "request_count": 10,
                "geo_location": ""  # No geo-location to avoid mismatch
            }
        )

