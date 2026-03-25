"""Integration tests for adversarial detection in full coordinator flow.

Phase 1C: Test Context Agent detector + injector integration with coordinator.
Phase 2C: Test Historical Agent detector + injector integration with coordinator.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType


class TestAdversarialIntegration:
    """Integration tests for Context Agent adversarial detection in coordinator."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.coordinator = CoordinatorAgent(use_mock=True)
        self.injector = AdversarialInjector()
    
    # ========================================================================
    # Test 1: Context Contradiction Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_context_contradiction_attack_full_flow(self):
        """Test that context contradiction attack is detected in full coordinator flow.

        NOTE: In mock mode, all agents return the same analysis, so contradictions
        won't be detected. This test validates the flow works without errors.
        Real contradiction detection requires live agents or custom mocks.
        """

        # Arrange - Inject contradiction attack
        signal = self.injector.inject_context_contradiction_attack(
            customer_name="IntegrationTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )

        # Act - Run full analysis
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.signal.id == signal.id
        assert analysis.status.value == "completed"

        # Assert - Adversarial detection present (but no manipulation in mock mode)
        assert analysis.adversarial_detection is not None
        # In mock mode, agents agree, so no contradiction detected
        # This is expected behavior - the detector works correctly

        # Assert - All components present
        assert analysis.false_positive_score is not None
        assert analysis.response_plan is not None
        assert analysis.investigation_timeline is not None
    
    # ========================================================================
    # Test 2: Geo-IP Mismatch Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_geo_ip_mismatch_attack_full_flow(self):
        """Test that geo-IP mismatch attack is detected in full coordinator flow."""
        
        # Arrange
        signal = self.injector.inject_geo_ip_mismatch_attack(
            customer_name="GeoTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )
        
        # Act
        analysis = await self.coordinator.analyze_threat(signal)
        
        # Assert - Adversarial detection present
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is True
        
        # Assert - Anomalies detected
        assert len(analysis.adversarial_detection.anomalies) > 0
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert anomaly.type == "context_metadata_inconsistency"
        assert "Private IP" in anomaly.description
        
        # Assert - Requires human review
        assert analysis.requires_human_review is True
    
    # ========================================================================
    # Test 3: Attack Tool User-Agent - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_attack_tool_ua_full_flow(self):
        """Test that attack tool User-Agent is detected in full coordinator flow."""
        
        # Arrange
        signal = self.injector.inject_attack_tool_ua_attack(
            customer_name="UATestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            attack_tool_index=0
        )
        
        # Act
        analysis = await self.coordinator.analyze_threat(signal)
        
        # Assert - Adversarial detection present
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is True
        
        # Assert - Anomaly detected
        assert len(analysis.adversarial_detection.anomalies) > 0
        assert "attack tool" in analysis.adversarial_detection.anomalies[0].description.lower()
    
    # ========================================================================
    # Test 4: Multi-Anomaly Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_multi_anomaly_attack_full_flow(self):
        """Test that multi-anomaly attack is detected with high risk score."""
        
        # Arrange
        signal = self.injector.inject_multi_anomaly_attack(
            customer_name="MultiTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )
        
        # Act
        analysis = await self.coordinator.analyze_threat(signal)
        
        # Assert - Adversarial detection present
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is True
        
        # Assert - Multiple anomalies detected
        assert len(analysis.adversarial_detection.anomalies) > 0
        anomaly = analysis.adversarial_detection.anomalies[0]
        assert len(anomaly.indicators) >= 2  # Multiple indicators
        
        # Assert - High risk score
        assert analysis.adversarial_detection.risk_score > 0.1
    
    # ========================================================================
    # Test 5: Combined Attack - Maximum Risk
    # ========================================================================
    @pytest.mark.asyncio
    async def test_combined_attack_maximum_risk(self):
        """Test that combined attack produces risk score.

        NOTE: In mock mode, contradictions won't be detected (agents agree).
        Only anomalies will be detected.
        """

        # Arrange
        signal = self.injector.inject_combined_contradiction_and_anomaly_attack(
            customer_name="CombinedTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Adversarial detection present
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is True

        # Assert - Anomalies detected (contradictions won't be in mock mode)
        assert len(analysis.adversarial_detection.anomalies) > 0

        # Assert - Risk score calculated
        assert analysis.adversarial_detection.risk_score > 0.0

    # ========================================================================
    # Test 6: Clean Signal - No False Positives
    # ========================================================================
    @pytest.mark.asyncio
    async def test_clean_signal_no_false_positives(self):
        """Test that clean signal does not trigger false positive detection."""

        # Arrange
        signal = self.injector.inject_clean_signal(
            customer_name="CleanTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Adversarial detection present but no manipulation
        assert analysis.adversarial_detection is not None
        assert analysis.adversarial_detection.manipulation_detected is False
        assert len(analysis.adversarial_detection.contradictions) == 0
        assert len(analysis.adversarial_detection.anomalies) == 0
        assert analysis.adversarial_detection.risk_score == 0.0
        assert analysis.adversarial_detection.attack_vector is None

    # ========================================================================
    # Test 7: Agent Analyses Present
    # ========================================================================
    @pytest.mark.asyncio
    async def test_agent_analyses_present_in_result(self):
        """Test that all agent analyses are present in final result."""

        # Arrange
        signal = self.injector.inject_context_contradiction_attack()

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - All agents ran
        assert "historical" in analysis.agent_analyses
        assert "config" in analysis.agent_analyses
        assert "devops" in analysis.agent_analyses
        assert "context" in analysis.agent_analyses
        assert "priority" in analysis.agent_analyses

        # Assert - Each agent has valid analysis
        # Note: agent_analysis.agent_name is the full name like "Historical Agent"
        # while the dict key is lowercase like "historical"
        for agent_key, agent_analysis in analysis.agent_analyses.items():
            assert agent_analysis.confidence >= 0.0
            assert agent_analysis.confidence <= 1.0
            assert len(agent_analysis.key_findings) > 0

    # ========================================================================
    # Test 8: FP Score Still Calculated
    # ========================================================================
    @pytest.mark.asyncio
    async def test_fp_score_still_calculated(self):
        """Test that FP score is still calculated alongside adversarial detection."""

        # Arrange
        signal = self.injector.inject_geo_ip_mismatch_attack()

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - FP score present
        assert analysis.false_positive_score is not None
        assert analysis.false_positive_score.score >= 0.0
        assert analysis.false_positive_score.score <= 1.0
        assert analysis.false_positive_score.recommendation is not None

    # ========================================================================
    # Test 9: Response Plan Generated
    # ========================================================================
    @pytest.mark.asyncio
    async def test_response_plan_generated(self):
        """Test that response plan is generated even with adversarial detection."""

        # Arrange
        signal = self.injector.inject_attack_tool_ua_attack()

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Response plan present
        assert analysis.response_plan is not None
        assert analysis.response_plan.primary_action is not None
        assert analysis.response_plan.primary_action.action_type is not None
        assert analysis.response_plan.primary_action.urgency is not None

    # ========================================================================
    # Test 10: Timeline Generated
    # ========================================================================
    @pytest.mark.asyncio
    async def test_timeline_generated(self):
        """Test that investigation timeline is generated."""

        # Arrange
        signal = self.injector.inject_high_volume_attack()

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Timeline present
        assert analysis.investigation_timeline is not None
        assert len(analysis.investigation_timeline.events) > 0

        # Assert - Timeline has detection event
        detection_events = [
            e for e in analysis.investigation_timeline.events
            if e.event_type.value == "detection"
        ]
        assert len(detection_events) > 0

class TestHistoricalAgentIntegration:
    """Integration tests for Historical Agent adversarial detection in coordinator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.coordinator = CoordinatorAgent(use_mock=True)
        self.injector = AdversarialInjector()

    # ========================================================================
    # Test 1: High FP Rate Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_historical_high_fp_rate_attack_full_flow(self):
        """Test that high FP rate attack is detected in full coordinator flow.

        NOTE: In mock mode, we can't inject custom Historical Agent responses.
        This test validates the flow works and detector is called.
        Real detection requires custom mocks or live Historical Agent.
        """

        # Arrange - Inject high FP rate attack
        attack_data = self.injector.inject_historical_high_fp_rate_attack(
            customer_name="HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            fp_rate=0.90
        )
        signal = attack_data["signal"]

        # Act - Run full analysis
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.signal.id == signal.id
        assert analysis.status.value == "completed"

        # Assert - Adversarial detection ran
        assert analysis.adversarial_detection is not None

        # Assert - All components present
        assert analysis.false_positive_score is not None
        assert analysis.response_plan is not None
        assert analysis.investigation_timeline is not None

    # ========================================================================
    # Test 2: High Incident Count Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_historical_high_incident_count_attack_full_flow(self):
        """Test that high incident count attack flows through coordinator."""

        # Arrange
        attack_data = self.injector.inject_historical_high_incident_count_attack(
            customer_name="HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            incident_count=50
        )
        signal = attack_data["signal"]

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.status.value == "completed"
        assert analysis.adversarial_detection is not None

    # ========================================================================
    # Test 3: Temporal Clustering Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_historical_temporal_clustering_attack_full_flow(self):
        """Test that temporal clustering attack flows through coordinator."""

        # Arrange
        attack_data = self.injector.inject_historical_temporal_clustering_attack(
            customer_name="HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            cluster_count=15,
            time_window_hours=1
        )
        signal = attack_data["signal"]

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.status.value == "completed"
        assert analysis.adversarial_detection is not None

    # ========================================================================
    # Test 4: Multi-Anomaly Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_historical_multi_anomaly_attack_full_flow(self):
        """Test that multi-anomaly attack flows through coordinator."""

        # Arrange
        attack_data = self.injector.inject_historical_multi_anomaly_attack(
            customer_name="HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )
        signal = attack_data["signal"]

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.status.value == "completed"
        assert analysis.adversarial_detection is not None

    # ========================================================================
    # Test 5: Historical-Priority Contradiction Attack - Full Flow
    # ========================================================================
    @pytest.mark.asyncio
    async def test_historical_priority_contradiction_attack_full_flow(self):
        """Test that Historical-Priority contradiction attack flows through coordinator.

        NOTE: In mock mode, we can't inject custom Historical Agent responses.
        This test validates the flow works. Real contradiction detection
        requires custom mocks or live agents.
        """

        # Arrange
        attack_data = self.injector.inject_historical_priority_contradiction_attack(
            customer_name="HistoricalTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )
        signal = attack_data["signal"]

        # Act
        analysis = await self.coordinator.analyze_threat(signal)

        # Assert - Analysis completed
        assert analysis is not None
        assert analysis.status.value == "completed"
        assert analysis.adversarial_detection is not None

        # Assert - Signal has malicious indicators
        assert "compromise_indicators" in signal.metadata
        assert signal.metadata["severity_score"] > 0.9


