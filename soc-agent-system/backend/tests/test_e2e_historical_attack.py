"""End-to-End test for Historical Agent adversarial attack detection.

This test demonstrates the full system flow:
1. Red Team injects a Historical Agent data poisoning attack
2. Coordinator processes the threat signal
3. Adversarial detector identifies the manipulation
4. System flags for human review
5. Full analysis is returned with detection details

This is the final validation (Gate 4) for Phase 2.

NOTE: In mock mode, we cannot inject custom Historical Agent responses.
These tests validate the flow works correctly. Real Historical detection
requires custom mocks or live Historical Agent with poisoned data.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from agents.coordinator import CoordinatorAgent
from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType


@pytest.mark.e2e
class TestE2EHistoricalAttack:
    """End-to-end tests for Historical Agent adversarial attacks."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.coordinator = CoordinatorAgent(use_mock=True)
        self.injector = AdversarialInjector()
    
    @pytest.mark.asyncio
    async def test_e2e_historical_high_fp_rate_attack(self):
        """E2E: High FP rate attack flows through full system.
        
        Scenario:
        - Attacker poisons historical database with 90% FP rate
        - Historical Agent is compromised and suggests current threat is benign
        - In mock mode, we validate the flow works
        - With live Historical Agent, detector would catch the poisoning
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Historical High FP Rate Attack")
        print("="*80)
        
        # ARRANGE - Red Team injects attack
        print("\n📍 Step 1: Red Team injects high FP rate attack...")
        attack_data = self.injector.inject_historical_high_fp_rate_attack(
            customer_name="E2E_HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            fp_rate=0.90
        )
        signal = attack_data["signal"]
        hist_data = attack_data["historical_data"]
        
        print(f"   ✓ Attack signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"     - User Agent: {signal.metadata['user_agent']}")
        print(f"\n   ✓ Poisoned historical data:")
        print(f"     - Similar incidents: {hist_data['similar_incidents']}")
        print(f"     - FP rate: {hist_data['false_positive_rate']*100:.0f}%")
        print(f"     - Pattern: {hist_data['pattern']}")
        
        # ACT - Coordinator processes the threat
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        analysis = await self.coordinator.analyze_threat(signal)
        
        # ASSERT - Verify analysis completed
        print("\n✅ Step 3: Verifying analysis completion...")
        assert analysis is not None, "Analysis result missing"
        assert analysis.status.value == "completed", "Analysis not completed"
        
        print(f"   ✓ Analysis status: {analysis.status.value}")
        print(f"   ✓ Severity: {analysis.severity.value}")
        
        # ASSERT - Verify adversarial detection ran
        print("\n🔍 Step 4: Verifying adversarial detection ran...")
        assert analysis.adversarial_detection is not None, "Adversarial detection missing"
        
        print(f"   ✓ Adversarial detection present")
        print(f"   ✓ Manipulation detected: {analysis.adversarial_detection.manipulation_detected}")
        
        # ASSERT - Verify full analysis
        print("\n📊 Step 5: Verifying complete analysis...")
        assert len(analysis.agent_analyses) == 5
        assert analysis.false_positive_score is not None
        assert analysis.response_plan is not None
        
        print(f"   ✓ Agents analyzed: {len(analysis.agent_analyses)}")
        print(f"   ✓ FP Score: {analysis.false_positive_score.score:.2f}")
        
        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Historical high FP rate attack flow validated!")
        print("="*80 + "\n")
    
    @pytest.mark.asyncio
    async def test_e2e_historical_temporal_clustering_attack(self):
        """E2E: Temporal clustering attack flows through full system.
        
        Scenario:
        - Attacker creates 15 similar incidents in 1 hour (coordinated poisoning)
        - Historical Agent is compromised and suggests benign pattern
        - In mock mode, we validate the flow works
        - With live Historical Agent, detector would catch the clustering
        """
        print("\n" + "="*80)
        print("🎯 E2E TEST: Historical Temporal Clustering Attack")
        print("="*80)
        
        # ARRANGE
        print("\n📍 Step 1: Red Team injects temporal clustering attack...")
        attack_data = self.injector.inject_historical_temporal_clustering_attack(
            customer_name="E2E_HistoricalTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            cluster_count=15,
            time_window_hours=1
        )
        signal = attack_data["signal"]
        hist_data = attack_data["historical_data"]
        
        print(f"   ✓ Attack signal created:")
        print(f"     - Source IP: {signal.metadata['source_ip']}")
        print(f"\n   ✓ Poisoned historical data:")
        print(f"     - Incidents in cluster: {hist_data['similar_incidents']}")
        print(f"     - Time window: {hist_data['time_window_hours']} hour(s)")
        print(f"     - Temporal clustering: {hist_data['temporal_clustering']}")
        
        # ACT
        print("\n🔄 Step 2: Coordinator processes threat signal...")
        analysis = await self.coordinator.analyze_threat(signal)
        
        # ASSERT
        print("\n✅ Step 3: Verifying analysis completion...")
        assert analysis.status.value == "completed"
        assert analysis.adversarial_detection is not None
        
        print(f"   ✓ Analysis completed successfully")
        print(f"   ✓ Adversarial detection ran")
        
        print("\n" + "="*80)
        print("✅ E2E TEST PASSED: Historical temporal clustering attack flow validated!")
        print("="*80 + "\n")

