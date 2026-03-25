#!/usr/bin/env python3
"""
Test script to send a threat with MITRE tags to the frontend for UI testing.
Run this while the backend and frontend are running to see MITRE tags in the UI.
"""
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, 'src')

from models import ThreatSignal, ThreatType
from agents.coordinator import CoordinatorAgent


async def test_mitre_ui():
    """Send a test threat with MITRE tags through the system."""
    
    print("=" * 80)
    print("MITRE ATT&CK UI Test - Android Malware Scenario")
    print("=" * 80)
    
    # Create a realistic Android malware threat signal
    signal = ThreatSignal(
        threat_type=ThreatType.DEVICE_COMPROMISE,
        customer_name="SeniorFraudShield",
        timestamp=datetime.utcnow(),
        mitre_hints=["T1475", "T1533"],  # From Wazuh
        metadata={
            "external_alert_id": "1774133781.1718",
            "rule_id": "100006",
            "wazuh_rule_level": 15,
            "package_name": "sk.madzik.android.logcatudp",
            "endpoint_name": "emulator-5554",
            "agent_id": "001",
            "agent_name": "Android-Test-Device"
        }
    )
    
    print(f"\n📱 Test Signal Created:")
    print(f"   Customer: {signal.customer_name}")
    print(f"   Threat Type: {signal.threat_type.value}")
    print(f"   MITRE Hints from Wazuh: {signal.mitre_hints}")
    print(f"   Package: {signal.metadata.get('package_name')}")
    
    # Analyze with mock mode
    print(f"\n🤖 Running Coordinator Analysis (Mock Mode)...")
    coordinator = CoordinatorAgent(use_mock=True)
    analysis = await coordinator.analyze_threat(signal)
    
    print(f"\n✅ Analysis Complete!")
    print(f"   Severity: {analysis.severity.value}")
    print(f"   Processing Time: {analysis.total_processing_time_ms}ms")
    print(f"   Requires Review: {analysis.requires_human_review}")
    
    # Display MITRE tags
    print(f"\n🎯 MITRE ATT&CK Tags ({len(analysis.mitre_tags)} techniques):")
    print("   " + "-" * 76)
    for tag in analysis.mitre_tags:
        source_label = {
            'wazuh': '🟢 Wazuh',
            'priority_agent': '🔵 AI',
            'fallback': '🟡 Fallback'
        }.get(tag.source, tag.source)
        
        print(f"   {tag.technique_id:12} | {tag.technique_name:40} | {source_label:12} | {tag.confidence:.0%}")
        print(f"   {'':12} | {tag.tactic_id} - {tag.tactic}")
        print("   " + "-" * 76)
    
    # Show JSON for API response
    print(f"\n📊 Analysis Summary:")
    print(f"   Executive Summary: {analysis.executive_summary[:100]}...")
    print(f"   FP Score: {analysis.false_positive_score.score:.2f}")
    print(f"   Agent Analyses: {len(analysis.agent_analyses)}")
    
    print(f"\n💡 To view in UI:")
    print(f"   1. Make sure backend is running: cd soc-agent-system/backend && python src/main.py")
    print(f"   2. Make sure frontend is running: cd soc-agent-system/frontend && npm run dev")
    print(f"   3. Open http://localhost:5173 in your browser")
    print(f"   4. Send a test alert: curl -X POST http://localhost:8000/api/wazuh/webhook \\")
    print(f"      -H 'Content-Type: application/json' -d @wazuh-integration/test-payloads/android-malware.json")
    
    print("\n" + "=" * 80)
    print("Test Complete! Check the frontend to see MITRE tags displayed.")
    print("=" * 80 + "\n")
    
    return analysis


if __name__ == "__main__":
    asyncio.run(test_mitre_ui())

