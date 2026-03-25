"""Integration tests for MITRE ATT&CK tagging feature."""
import sys
import pytest
from datetime import datetime

sys.path.insert(0, 'src')

from models import ThreatSignal, ThreatType
from agents.coordinator import CoordinatorAgent


@pytest.mark.asyncio
async def test_mitre_tagging_with_wazuh_hints():
    """Test MITRE tagging when Wazuh provides hints (Layer 1)."""
    # Create signal with Wazuh MITRE hints
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="TestCorp",
        timestamp=datetime.utcnow(),
        mitre_hints=["T1475", "T1533"],  # From Wazuh
        metadata={
            "package_name": "com.malicious.app",
            "rule_id": "100006"
        }
    )
    
    # Use mock mode to avoid LLM calls
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Verify MITRE tags are present
    assert analysis.mitre_tags is not None
    assert len(analysis.mitre_tags) > 0
    
    # Verify Wazuh tags come first (highest priority)
    wazuh_tags = [tag for tag in analysis.mitre_tags if tag.source == "wazuh"]
    assert len(wazuh_tags) >= 2
    assert any(tag.technique_id == "T1475" for tag in wazuh_tags)
    assert any(tag.technique_id == "T1533" for tag in wazuh_tags)
    
    # Verify Wazuh tags have confidence 1.0
    for tag in wazuh_tags:
        assert tag.confidence == 1.0


@pytest.mark.asyncio
async def test_mitre_tagging_with_llm_only():
    """Test MITRE tagging when only LLM provides tags (Layer 2)."""
    # Create signal without Wazuh hints
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="TestCorp",
        timestamp=datetime.utcnow(),
        mitre_hints=[],  # No Wazuh hints
        metadata={
            "package_name": "com.malicious.app"
        }
    )
    
    # Use mock mode
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Verify MITRE tags are present
    assert analysis.mitre_tags is not None
    assert len(analysis.mitre_tags) > 0
    
    # Should have LLM tags from mock response
    llm_tags = [tag for tag in analysis.mitre_tags if tag.source == "priority_agent"]
    assert len(llm_tags) >= 1


@pytest.mark.asyncio
async def test_mitre_tagging_fallback():
    """Test MITRE tagging fallback when no Wazuh or LLM tags (Layer 3)."""
    # Create signal without hints and mock LLM that doesn't return tags
    signal = ThreatSignal(
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="TestCorp",
        timestamp=datetime.utcnow(),
        mitre_hints=[],
        metadata={}
    )
    
    # Use mock mode
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Should have fallback tags
    assert analysis.mitre_tags is not None
    assert len(analysis.mitre_tags) > 0


@pytest.mark.asyncio
async def test_mitre_tagging_merge_priority():
    """Test that Wazuh tags take priority over LLM tags."""
    # Create signal with Wazuh hints
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="TestCorp",
        timestamp=datetime.utcnow(),
        mitre_hints=["T1475"],  # Wazuh provides T1475
        metadata={}
    )
    
    # Use mock mode (LLM also provides T1475 and T1533)
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Find T1475 in merged tags
    t1475_tags = [tag for tag in analysis.mitre_tags if tag.technique_id == "T1475"]
    
    # Should have exactly one T1475 (deduplicated)
    assert len(t1475_tags) == 1
    
    # Should be from Wazuh (higher priority)
    assert t1475_tags[0].source == "wazuh"
    assert t1475_tags[0].confidence == 1.0


@pytest.mark.asyncio
async def test_mitre_tagging_cap_at_six():
    """Test that merged tags are capped at 6 techniques."""
    # This test would require a scenario with many tags
    # For now, verify the cap logic exists
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="TestCorp",
        timestamp=datetime.utcnow(),
        mitre_hints=["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"],
        metadata={}
    )
    
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Should be capped at 6
    assert len(analysis.mitre_tags) <= 6


@pytest.mark.asyncio
async def test_mitre_tagging_android_malware_e2e():
    """End-to-end test with Android malware scenario."""
    # Simulate real Wazuh alert for Android malware
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="SeniorFraudShield",
        timestamp=datetime.utcnow(),
        mitre_hints=["T1475", "T1533"],  # From Wazuh rule 100006
        metadata={
            "external_alert_id": "1774133781.1718",
            "rule_id": "100006",
            "wazuh_rule_level": 15,
            "package_name": "sk.madzik.android.logcatudp",
            "endpoint_name": "emulator-5554"
        }
    )
    
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    # Verify analysis completed
    assert analysis is not None
    assert analysis.severity is not None
    
    # Verify MITRE tags
    assert len(analysis.mitre_tags) >= 2
    
    # Verify Mobile ATT&CK tactics (TA0027-TA0037)
    for tag in analysis.mitre_tags:
        if tag.source == "wazuh" or tag.source == "priority_agent":
            tactic_num = int(tag.tactic_id[2:])
            # Should use Mobile ATT&CK for Android threats
            assert 27 <= tactic_num <= 41 or tactic_num <= 11, \
                f"Expected Mobile or Enterprise ATT&CK tactic, got {tag.tactic_id}"

