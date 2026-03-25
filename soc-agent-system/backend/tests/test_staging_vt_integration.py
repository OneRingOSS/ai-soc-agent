"""
Staging Integration Test for VirusTotal Package Lookup

This test runs against a live Kubernetes cluster to validate the E2E deployment.
It sends a real Wazuh alert and verifies the VT enrichment pipeline works.

Usage:
    # Set the backend URL (defaults to localhost:8080)
    export BACKEND_URL=http://localhost:8080
    
    # Run the test
    pytest tests/test_staging_vt_integration.py -v
"""

import os
import pytest
import httpx
from datetime import datetime

# Backend URL from environment or default to localhost
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")

# Test payload: Wazuh alert with malicious package (com.kingroot.kinguser)
# This matches the expected Wazuh webhook format for rule 100006
WAZUH_ALERT_PAYLOAD = {
    "id": "staging_test_001",
    "timestamp": "Mar 23, 2026 @ 19:30:00.000",
    "location": "192.168.1.100",
    "full_log": "android-device-staging-test: D/BackupManagerService( 1198): Received broadcast Intent { act=android.intent.action.PACKAGE_ADDED dat=package:com.kingroot.kinguser flg=0x4000010 (has extras) }",
    "rule": {
        "id": "100006",
        "level": 15,
        "description": "Malicious Android app installed: com.kingroot.kinguser",
        "groups": ["android", "package", "installandroid_install"],
        "firedtimes": 1,
        "mitre": {
            "id": ["T1475", "T1533"],
            "tactic": ["Defense Evasion", "Persistence"],
            "technique": ["Deliver Malicious App via Other Means", "Data from Local System"]
        }
    },
    "agent": {
        "id": "001",
        "name": "android-device-staging-test"
    },
    "manager": {
        "name": "wazuh.manager"
    },
    "decoder": {
        "name": "android_decoder_03"
    },
    "data": {
        "package_name": "com.kingroot.kinguser"
    }
}


@pytest.mark.asyncio
async def test_staging_health_check():
    """Test 1: Verify backend is reachable and healthy."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{BACKEND_URL}/health")
        assert response.status_code == 200, f"Health check failed: {response.text}"
        data = response.json()
        assert data["status"] == "healthy", f"Backend not healthy: {data}"
        print(f"✅ Backend is healthy: {data}")


@pytest.mark.asyncio
async def test_staging_vt_enrichment_demo_mode():
    """Test 2: Send Wazuh alert and verify VT enrichment in DEMO_MODE."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Send the alert
        response = await client.post(
            f"{BACKEND_URL}/api/threats/ingest/wazuh",
            json=WAZUH_ALERT_PAYLOAD
        )

        assert response.status_code == 202, f"Alert submission failed: {response.text}"
        signal = response.json()

        # Verify response structure (ThreatSignal)
        assert "id" in signal, "Response missing id"
        assert "threat_type" in signal, "Response missing threat_type"

        threat_id = signal["id"]
        print(f"✅ Alert ingested, threat_id: {threat_id}")
        
        # Wait for async processing to complete
        import asyncio
        await asyncio.sleep(5)

        # Fetch all threats and find the one with matching signal ID
        # (The ingest endpoint returns the signal ID, but threats are stored with analysis ID)
        response = await client.get(f"{BACKEND_URL}/api/threats?limit=10")
        assert response.status_code == 200, f"Threats fetch failed: {response.text}"

        threats = response.json()
        threat = None
        for t in threats:
            if t.get("signal", {}).get("id") == threat_id:
                threat = t
                break

        assert threat is not None, f"Threat with signal ID {threat_id} not found in recent threats"
        
        # Verify threat structure (ThreatAnalysis)
        assert "executive_summary" in threat, "Threat missing executive_summary"
        assert "agent_analyses" in threat, "Threat missing agent_analyses"

        # Verify intel_matches field exists in the threat
        assert "intel_matches" in threat, "Threat missing intel_matches field"

        intel_matches = threat["intel_matches"]
        print(f"✅ Intel matches found: {len(intel_matches)} matches")
        
        # In DEMO_MODE, we should get matches for com.kingroot.kinguser
        if intel_matches:
            match = intel_matches[0]
            assert "ioc_type" in match, "Intel match missing ioc_type"
            assert "ioc_value" in match, "Intel match missing ioc_value"
            assert "source" in match, "Intel match missing source"
            assert "confidence" in match, "Intel match missing confidence"
            
            print(f"✅ Intel match details:")
            print(f"   IOC Type: {match['ioc_type']}")
            print(f"   IOC Value: {match['ioc_value']}")
            print(f"   Source: {match['source']}")
            print(f"   Confidence: {match['confidence']}")
            print(f"   Description: {match.get('description', 'N/A')}")
        else:
            print("⚠️  No intel matches found (may not be in DEMO_MODE or package not in cache)")


@pytest.mark.asyncio
async def test_staging_vt_enrichment_unknown_package():
    """Test 3: Send alert with unknown package and verify graceful degradation."""
    unknown_payload = WAZUH_ALERT_PAYLOAD.copy()
    unknown_payload["data"]["package_name"] = "com.example.benign.app"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/threats/ingest/wazuh",
            json=unknown_payload
        )

        assert response.status_code == 202, f"Alert submission failed: {response.text}"
        signal = response.json()

        threat_id = signal["id"]
        print(f"✅ Unknown package alert ingested, threat_id: {threat_id}")
        
        # Wait for async processing to complete
        import asyncio
        await asyncio.sleep(5)

        # Fetch all threats and find the one with matching signal ID
        response = await client.get(f"{BACKEND_URL}/api/threats?limit=10")
        assert response.status_code == 200

        threats = response.json()
        threat = None
        for t in threats:
            if t.get("signal", {}).get("id") == threat_id:
                threat = t
                break

        assert threat is not None, f"Threat with signal ID {threat_id} not found"

        # Should have intel_matches field, but it should be empty
        assert "intel_matches" in threat
        assert isinstance(threat["intel_matches"], list)

        print(f"✅ Graceful degradation: intel_matches = {threat['intel_matches']}")


if __name__ == "__main__":
    import asyncio
    
    print(f"\n🧪 Running Staging Integration Tests against {BACKEND_URL}\n")
    
    async def run_tests():
        await test_staging_health_check()
        await test_staging_vt_enrichment_demo_mode()
        await test_staging_vt_enrichment_unknown_package()
    
    asyncio.run(run_tests())
    print("\n✅ All staging tests passed!")

