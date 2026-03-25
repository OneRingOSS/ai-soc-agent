"""
Unit tests for Agent Integration with Intel Enrichment.

Stage 4 Gate: These tests must pass before proceeding to Stage 5.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agents.historical_agent import HistoricalAgent
from src.agents.coordinator import CoordinatorAgent
from src.models import ThreatSignal, ThreatType, IntelMatch
from datetime import datetime


@pytest.fixture
def mock_intel_enricher():
    """Create a mock IntelEnricher."""
    enricher = Mock()
    enricher.enrich = AsyncMock(return_value=[])
    return enricher


@pytest.fixture
def sample_signal():
    """Create a sample ThreatSignal."""
    return ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="TestCustomer",
        metadata={"package_name": "com.kingroot.kinguser"}
    )


class TestHistoricalAgentWithEnricher:
    """Test HistoricalAgent with intel enricher."""

    def test_init_with_enricher(self, mock_intel_enricher):
        """Test HistoricalAgent initialization with enricher."""
        agent = HistoricalAgent(intel_enricher=mock_intel_enricher)
        
        assert agent.intel_enricher == mock_intel_enricher

    def test_init_without_enricher(self):
        """Test HistoricalAgent initialization without enricher (backward compat)."""
        agent = HistoricalAgent()
        
        assert agent.intel_enricher is None

    @pytest.mark.asyncio
    async def test_analyze_with_enricher_no_matches(self, mock_intel_enricher, sample_signal):
        """Test analyze with enricher but no intel matches."""
        from models import AgentAnalysis

        mock_intel_enricher.enrich = AsyncMock(return_value=[])

        agent = HistoricalAgent(intel_enricher=mock_intel_enricher)

        # Mock the parent analyze method to return AgentAnalysis object
        with patch.object(agent.__class__.__bases__[0], 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Test analysis",
                confidence=0.8,
                key_findings=[],
                recommendations=[],
                processing_time_ms=100,
                raw_output=""
            )

            result = await agent.analyze(sample_signal, {})

        # Verify enricher was called
        mock_intel_enricher.enrich.assert_called_once()

        # Verify intel_matches in raw_output metadata
        import json
        raw_data = json.loads(result.raw_output)
        assert "metadata" in raw_data
        assert "intel_matches" in raw_data["metadata"]
        assert raw_data["metadata"]["intel_matches"] == []

    @pytest.mark.asyncio
    async def test_analyze_with_enricher_with_matches(self, mock_intel_enricher, sample_signal):
        """Test analyze with enricher returning intel matches."""
        from models import AgentAnalysis

        intel_match = IntelMatch(
            ioc_type="hash",
            ioc_value="abc123def456",
            source="virustotal",
            description="28/72 AV engines flagged",
            date_added="2024-01-01T00:00:00",
            confidence=0.91,
            threat_actor=None
        )
        mock_intel_enricher.enrich = AsyncMock(return_value=[intel_match])

        agent = HistoricalAgent(intel_enricher=mock_intel_enricher)

        # Mock the parent analyze method to return AgentAnalysis object
        with patch.object(agent.__class__.__bases__[0], 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Test analysis",
                confidence=0.8,
                key_findings=[],
                recommendations=[],
                processing_time_ms=100,
                raw_output=""
            )

            result = await agent.analyze(sample_signal, {})

        # Verify enricher was called
        mock_intel_enricher.enrich.assert_called_once()

        # Verify intel_matches in raw_output metadata
        import json
        raw_data = json.loads(result.raw_output)
        assert "metadata" in raw_data
        assert "intel_matches" in raw_data["metadata"]
        assert len(raw_data["metadata"]["intel_matches"]) == 1
        assert raw_data["metadata"]["intel_matches"][0]["ioc_value"] == "abc123def456"

    @pytest.mark.asyncio
    async def test_analyze_enricher_error_graceful_degradation(self, mock_intel_enricher, sample_signal):
        """Test analyze gracefully handles enricher errors."""
        from models import AgentAnalysis

        mock_intel_enricher.enrich = AsyncMock(side_effect=Exception("VT API error"))

        agent = HistoricalAgent(intel_enricher=mock_intel_enricher)

        # Mock the parent analyze method to return AgentAnalysis object
        with patch.object(agent.__class__.__bases__[0], 'analyze', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = AgentAnalysis(
                agent_name="Historical Agent",
                analysis="Test analysis",
                confidence=0.8,
                key_findings=[],
                recommendations=[],
                processing_time_ms=100,
                raw_output=""
            )

            result = await agent.analyze(sample_signal, {})

        # Verify analysis still completes (graceful degradation)
        assert result.analysis == "Test analysis"
        # When enricher errors, intel_matches should be empty list
        import json
        raw_data = json.loads(result.raw_output) if result.raw_output else {}
        assert "metadata" in raw_data
        assert "intel_matches" in raw_data["metadata"]
        assert raw_data["metadata"]["intel_matches"] == []


class TestCoordinatorWithIntelCache:
    """Test CoordinatorAgent with intel cache."""

    def test_init_with_intel_cache(self):
        """Test CoordinatorAgent initialization with intel_cache."""
        mock_cache = Mock()

        with patch('intel_enricher.IntelEnricher') as mock_enricher_class:
            mock_enricher_instance = Mock()
            mock_enricher_class.return_value = mock_enricher_instance

            coordinator = CoordinatorAgent(intel_cache=mock_cache)

            # Verify IntelEnricher was created with cache
            mock_enricher_class.assert_called_once_with(cache=mock_cache)

            # Verify historical agent has enricher
            assert coordinator.historical_agent.intel_enricher == mock_enricher_instance

    def test_init_without_intel_cache(self):
        """Test CoordinatorAgent initialization without intel_cache (backward compat)."""
        coordinator = CoordinatorAgent()
        
        # Verify historical agent has no enricher
        assert coordinator.historical_agent.intel_enricher is None

