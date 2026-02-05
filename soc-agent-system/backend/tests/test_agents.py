"""Tests for individual agents."""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent


@pytest.mark.asyncio
async def test_historical_agent_mock_analysis(sample_threat_signal, mock_data_store):
    """Test historical agent mock analysis."""
    agent = HistoricalAgent()
    context = {
        "similar_incidents": mock_data_store.get_similar_incidents(
            sample_threat_signal.threat_type,
            sample_threat_signal.customer_name
        )
    }
    
    result = await agent.analyze_mock(sample_threat_signal, context)
    
    assert result is not None
    assert result.agent_name == "Historical Agent"
    assert result.confidence > 0
    assert len(result.key_findings) > 0
    assert len(result.recommendations) > 0


@pytest.mark.asyncio
async def test_config_agent_mock_analysis(sample_threat_signal, mock_data_store):
    """Test config agent mock analysis."""
    agent = ConfigAgent()
    context = {
        "customer_config": mock_data_store.get_customer_config(
            sample_threat_signal.customer_name
        )
    }
    
    result = await agent.analyze_mock(sample_threat_signal, context)
    
    assert result is not None
    assert result.agent_name == "Config Agent"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_devops_agent_mock_analysis(sample_threat_signal, mock_data_store):
    """Test devops agent mock analysis."""
    agent = DevOpsAgent()
    context = {
        "infra_events": mock_data_store.get_recent_infra_events(60)
    }
    
    result = await agent.analyze_mock(sample_threat_signal, context)
    
    assert result is not None
    assert result.agent_name == "DevOps Agent"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_context_agent_mock_analysis(sample_threat_signal, mock_data_store):
    """Test context agent mock analysis."""
    agent = ContextAgent()
    context = {
        "news_items": mock_data_store.get_relevant_news(["test"])
    }
    
    result = await agent.analyze_mock(sample_threat_signal, context)
    
    assert result is not None
    assert result.agent_name == "Context Agent"
    assert result.confidence > 0


@pytest.mark.asyncio
async def test_priority_agent_mock_analysis(sample_threat_signal):
    """Test priority agent mock analysis."""
    agent = PriorityAgent()
    context = {}
    
    result = await agent.analyze_mock(sample_threat_signal, context)
    
    assert result is not None
    assert result.agent_name == "Priority Agent"
    assert result.confidence > 0


def test_historical_agent_system_prompt():
    """Test historical agent system prompt."""
    agent = HistoricalAgent()
    prompt = agent.get_system_prompt()
    
    assert "Historical Pattern Analysis" in prompt
    assert "JSON" in prompt


def test_config_agent_system_prompt():
    """Test config agent system prompt."""
    agent = ConfigAgent()
    prompt = agent.get_system_prompt()
    
    assert "Configuration Analysis" in prompt
    assert "rate limiting" in prompt.lower()


def test_devops_agent_system_prompt():
    """Test devops agent system prompt."""
    agent = DevOpsAgent()
    prompt = agent.get_system_prompt()
    
    assert "DevOps Correlation" in prompt
    assert "infrastructure" in prompt.lower()


def test_context_agent_system_prompt():
    """Test context agent system prompt."""
    agent = ContextAgent()
    prompt = agent.get_system_prompt()
    
    assert "Business Context" in prompt
    assert "external events" in prompt.lower()


def test_priority_agent_system_prompt():
    """Test priority agent system prompt."""
    agent = PriorityAgent()
    prompt = agent.get_system_prompt()
    
    assert "Threat Prioritization" in prompt
    assert "MITRE ATT&CK" in prompt


def test_agent_user_prompts(sample_threat_signal, mock_data_store):
    """Test that all agents can build user prompts."""
    agents = [
        (HistoricalAgent(), {"similar_incidents": []}),
        (ConfigAgent(), {"customer_config": mock_data_store.get_customer_config("Test")}),
        (DevOpsAgent(), {"infra_events": []}),
        (ContextAgent(), {"news_items": []}),
        (PriorityAgent(), {})
    ]
    
    for agent, context in agents:
        prompt = agent.build_user_prompt(sample_threat_signal, context)
        assert prompt is not None
        assert len(prompt) > 0
        assert sample_threat_signal.threat_type.value in prompt

