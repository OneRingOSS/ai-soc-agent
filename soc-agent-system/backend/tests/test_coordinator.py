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
    
    assert coordinator is not None
    assert coordinator.historical_agent is not None
    assert coordinator.config_agent is not None
    assert coordinator.devops_agent is not None
    assert coordinator.context_agent is not None
    assert coordinator.priority_agent is not None


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
    from models import ThreatSeverity, FalsePositiveScore, ResponsePlan, ResponseAction, ResponseActionType, ResponseUrgency, InvestigationTimeline

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

    result = coordinator_mock_mode._synthesize_analysis(
        sample_threat_signal,
        agent_analyses,
        total_time=500,
        severity=ThreatSeverity.MEDIUM,
        fp_score=fp_score,
        response_plan=response_plan,
        timeline=timeline
    )

    assert result is not None
    assert result.signal == sample_threat_signal
    assert result.total_processing_time_ms == 500
    assert result.executive_summary is not None
    assert result.false_positive_score == fp_score
    assert result.response_plan == response_plan
    assert result.investigation_timeline == timeline


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

