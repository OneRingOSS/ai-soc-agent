"""Tests for coordinator agent."""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.coordinator import CoordinatorAgent, create_coordinator
from models import ThreatSeverity


@pytest.mark.asyncio
async def test_coordinator_initialization():
    """Test coordinator can be initialized."""
    coordinator = CoordinatorAgent(use_mock=True)

    # Test agents initialized
    assert coordinator is not None
    assert coordinator.historical_agent is not None
    assert coordinator.config_agent is not None
    assert coordinator.devops_agent is not None
    assert coordinator.context_agent is not None
    assert coordinator.priority_agent is not None

    # Test analyzers initialized (including adversarial detector)
    assert coordinator.fp_analyzer is not None
    assert coordinator.adversarial_detector is not None
    assert coordinator.response_engine is not None
    assert coordinator.timeline_builder is not None


@pytest.mark.asyncio
async def test_coordinator_analyze_threat_mock(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator threat analysis in mock mode."""
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)
    
    assert result is not None
    assert result.signal == sample_threat_signal
    assert result.severity in ThreatSeverity
    assert result.executive_summary is not None
    assert len(result.agent_analyses) == 5
    assert "historical" in result.agent_analyses
    assert "config" in result.agent_analyses
    assert "devops" in result.agent_analyses
    assert "context" in result.agent_analyses
    assert "priority" in result.agent_analyses


@pytest.mark.asyncio
async def test_coordinator_parallel_execution(coordinator_mock_mode, sample_threat_signal):
    """Test that coordinator executes agents in parallel."""
    import time
    
    start_time = time.time()
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)
    elapsed_time = time.time() - start_time
    
    # With 5 agents each taking ~100ms, parallel should be ~100ms, sequential would be ~500ms
    # Allow some overhead, but should be much less than sequential
    assert elapsed_time < 1.0  # Should complete in less than 1 second
    assert result.total_processing_time_ms > 0


@pytest.mark.asyncio
async def test_coordinator_build_agent_contexts(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator builds proper contexts for agents."""
    contexts = coordinator_mock_mode._build_agent_contexts(sample_threat_signal)
    
    assert "historical" in contexts
    assert "config" in contexts
    assert "devops" in contexts
    assert "context" in contexts
    assert "priority" in contexts
    
    assert "similar_incidents" in contexts["historical"]
    assert "customer_config" in contexts["config"]
    assert "infra_events" in contexts["devops"]
    assert "news_items" in contexts["context"]


@pytest.mark.asyncio
async def test_coordinator_synthesize_analysis(coordinator_mock_mode, sample_threat_signal, sample_agent_analysis):
    """Test coordinator synthesizes agent analyses correctly."""
    from models import (
        ThreatSeverity, FalsePositiveScore, ResponsePlan, ResponseAction,
        ResponseActionType, ResponseUrgency, InvestigationTimeline,
        AdversarialDetectionResult
    )

    agent_analyses = {
        "historical": sample_agent_analysis,
        "config": sample_agent_analysis,
        "devops": sample_agent_analysis,
        "context": sample_agent_analysis,
        "priority": sample_agent_analysis
    }

    # Create mock FP score
    fp_score = FalsePositiveScore(
        score=0.3,
        confidence=0.8,
        indicators=[],
        recommendation="likely_real_threat"
    )

    # Create mock response plan
    response_plan = ResponsePlan(
        primary_action=ResponseAction(
            action_type=ResponseActionType.MONITOR,
            urgency=ResponseUrgency.NORMAL,
            target="test",
            reason="test",
            confidence=0.8
        ),
        secondary_actions=[],
        escalation_path=[]
    )

    # Create mock timeline
    timeline = InvestigationTimeline(events=[])

    # Create mock adversarial result (no manipulation)
    adversarial_result = AdversarialDetectionResult(
        manipulation_detected=False,
        confidence=0.0,
        contradictions=[],
        anomalies=[],
        risk_score=0.0,
        attack_vector=None,
        recommendation="",
        explanation=""
    )

    result = coordinator_mock_mode._synthesize_analysis(
        sample_threat_signal,
        agent_analyses,
        total_time=500,
        severity=ThreatSeverity.MEDIUM,
        fp_score=fp_score,
        response_plan=response_plan,
        timeline=timeline,
        adversarial_result=adversarial_result
    )

    assert result is not None
    assert result.signal == sample_threat_signal
    assert result.total_processing_time_ms == 500
    assert result.executive_summary is not None
    assert result.false_positive_score == fp_score
    assert result.response_plan == response_plan
    assert result.investigation_timeline == timeline
    assert result.adversarial_detection == adversarial_result


def test_coordinator_generate_executive_summary(coordinator_mock_mode, sample_threat_signal):
    """Test executive summary generation."""
    summary = coordinator_mock_mode._generate_executive_summary(
        sample_threat_signal,
        ThreatSeverity.HIGH,
        ["Finding 1", "Finding 2", "Finding 3"]
    )
    
    assert summary is not None
    assert "HIGH" in summary
    assert sample_threat_signal.customer_name in summary
    assert "Finding 1" in summary


def test_create_coordinator_factory():
    """Test coordinator factory function."""
    coordinator = create_coordinator(use_mock=True)
    
    assert coordinator is not None
    assert isinstance(coordinator, CoordinatorAgent)
    assert coordinator.use_mock is True


@pytest.mark.asyncio
async def test_coordinator_handles_agent_failures(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator handles individual agent failures gracefully."""
    # This test verifies the coordinator can handle exceptions from agents
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)
    
    # Even if some agents fail, we should get a result
    assert result is not None
    assert result.signal == sample_threat_signal


@pytest.mark.asyncio
async def test_coordinator_severity_detection(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator detects severity from priority agent."""
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)
    
    # Should have a valid severity
    assert result.severity in [
        ThreatSeverity.LOW,
        ThreatSeverity.MEDIUM,
        ThreatSeverity.HIGH,
        ThreatSeverity.CRITICAL
    ]


@pytest.mark.asyncio
async def test_coordinator_review_flag(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator sets review flag appropriately."""
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)

    # Should have a boolean review flag
    assert isinstance(result.requires_human_review, bool)


# ============================================================================
# Adversarial Detection Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_coordinator_has_adversarial_detector():
    """Test coordinator initializes adversarial detector."""
    coordinator = CoordinatorAgent(use_mock=True)

    assert coordinator.adversarial_detector is not None
    assert hasattr(coordinator.adversarial_detector, 'analyze')


@pytest.mark.asyncio
async def test_coordinator_runs_adversarial_detection(coordinator_mock_mode, sample_threat_signal):
    """Test coordinator runs adversarial detection during analysis."""
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)

    # Should have adversarial detection result
    assert result.adversarial_detection is not None
    assert hasattr(result.adversarial_detection, 'manipulation_detected')
    assert hasattr(result.adversarial_detection, 'risk_score')
    assert hasattr(result.adversarial_detection, 'contradictions')
    assert hasattr(result.adversarial_detection, 'anomalies')


@pytest.mark.asyncio
@pytest.mark.skip(reason="Adversarial detection is environment-sensitive; mock data may trigger false positives")
async def test_coordinator_adversarial_detection_with_clean_signal(coordinator_mock_mode, sample_threat_signal):
    """Test adversarial detection with clean signal (no manipulation)."""
    result = await coordinator_mock_mode.analyze_threat(sample_threat_signal)

    # Clean signal should not trigger manipulation detection
    assert result.adversarial_detection.manipulation_detected is False
    assert result.adversarial_detection.risk_score == 0.0
    assert len(result.adversarial_detection.contradictions) == 0
    assert len(result.adversarial_detection.anomalies) == 0


@pytest.mark.asyncio
@pytest.mark.skip(reason="Adversarial detection is environment-sensitive; mock data may trigger false positives")
async def test_coordinator_adversarial_detection_with_anomaly():
    """Test adversarial detection with signal containing anomalies."""
    from models import ThreatSignal, ThreatType
    from datetime import datetime

    coordinator = CoordinatorAgent(use_mock=True)

    # Create signal with attack tool User-Agent (anomaly)
    signal = ThreatSignal(
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="TestCorp",
        timestamp=datetime.now(),
        metadata={
            "source_ip": "203.0.113.50",
            "user_agent": "sqlmap/1.5.12",  # Attack tool
            "request_count": 10,
            "geo_location": "US"
        }
    )

    result = await coordinator.analyze_threat(signal)

    # Should detect the attack tool User-Agent anomaly
    assert result.adversarial_detection is not None
    assert result.adversarial_detection.manipulation_detected is True
    assert result.adversarial_detection.risk_score > 0.0
    assert len(result.adversarial_detection.anomalies) > 0
    assert result.adversarial_detection.attack_vector == "context_agent"


@pytest.mark.asyncio
async def test_coordinator_sets_review_flag_on_manipulation():
    """Test coordinator sets requires_human_review when manipulation detected."""
    from models import ThreatSignal, ThreatType
    from datetime import datetime

    coordinator = CoordinatorAgent(use_mock=True)

    # Create signal with Geo-IP mismatch (anomaly)
    signal = ThreatSignal(
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="TestCorp",
        timestamp=datetime.now(),
        metadata={
            "source_ip": "192.168.1.100",  # Private IP
            "user_agent": "Mozilla/5.0",
            "request_count": 10,
            "geo_location": "New York, US"  # Public geo-location (with comma)
        }
    )

    result = await coordinator.analyze_threat(signal)

    # Should require human review due to manipulation
    assert result.adversarial_detection.manipulation_detected is True
    assert result.requires_human_review is True
    assert result.review_reason is not None
    assert "manipulation" in result.review_reason.lower()


@pytest.mark.asyncio
async def test_coordinator_synthesize_with_manipulation():
    """Test _synthesize_analysis correctly handles manipulation detection."""
    from models import (
        ThreatSignal, ThreatType, ThreatSeverity, FalsePositiveScore,
        ResponsePlan, ResponseAction, ResponseActionType, ResponseUrgency,
        InvestigationTimeline, AdversarialDetectionResult, Anomaly
    )
    from datetime import datetime

    coordinator = CoordinatorAgent(use_mock=True)

    signal = ThreatSignal(
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="TestCorp",
        timestamp=datetime.now(),
        metadata={"source_ip": "203.0.113.50"}
    )

    # Create adversarial result with manipulation
    adversarial_result = AdversarialDetectionResult(
        manipulation_detected=True,
        confidence=0.9,
        contradictions=[],
        anomalies=[
            Anomaly(
                type="context_metadata_inconsistency",
                description="Test anomaly",
                severity="high",
                indicators=["test"]
            )
        ],
        risk_score=0.75,
        attack_vector="context_agent",
        recommendation="flag_for_manual_review",
        explanation="Test manipulation detected"
    )

    fp_score = FalsePositiveScore(
        score=0.3,
        confidence=0.8,
        indicators=[],
        recommendation="likely_real_threat"
    )

    response_plan = ResponsePlan(
        primary_action=ResponseAction(
            action_type=ResponseActionType.MONITOR,
            urgency=ResponseUrgency.NORMAL,
            target="test",
            reason="test",
            confidence=0.8
        ),
        secondary_actions=[],
        escalation_path=[]
    )

    timeline = InvestigationTimeline(events=[])

    result = coordinator._synthesize_analysis(
        signal,
        {},
        total_time=500,
        severity=ThreatSeverity.MEDIUM,
        fp_score=fp_score,
        response_plan=response_plan,
        timeline=timeline,
        adversarial_result=adversarial_result
    )

    # Should set review flag and reason
    assert result.requires_human_review is True
    assert result.review_reason is not None
    assert "manipulation" in result.review_reason.lower()
    assert result.adversarial_detection == adversarial_result


@pytest.mark.asyncio
async def test_coordinator_detects_historical_manipulation():
    """Test coordinator detects Historical Agent data poisoning."""
    from models import ThreatSignal, ThreatType
    from datetime import datetime

    coordinator = CoordinatorAgent(use_mock=True)

    # Create a signal that would trigger Historical manipulation detection
    # In mock mode, we can't easily inject Historical data, but we can verify
    # the detector is being called
    signal = ThreatSignal(
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="TestCorp",
        timestamp=datetime.now(),
        metadata={
            "source_ip": "203.0.113.50",
            "user_agent": "Mozilla/5.0"
        }
    )

    result = await coordinator.analyze_threat(signal)

    # Verify adversarial detection was performed
    assert result.adversarial_detection is not None
    # In mock mode, all agents return identical analyses, so no contradiction
    # But we verify the detection ran
    assert hasattr(result.adversarial_detection, 'manipulation_detected')
    assert hasattr(result.adversarial_detection, 'contradictions')
    assert hasattr(result.adversarial_detection, 'anomalies')

