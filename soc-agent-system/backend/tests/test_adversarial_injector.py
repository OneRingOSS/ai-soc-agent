"""Unit tests for AdversarialInjector - Context and Historical Agent attack scenarios.

Phase 1B: Test Context Agent injector logic.
Phase 2B: Test Historical Agent injector logic.
"""
import pytest
import sys
sys.path.insert(0, 'src')

from red_team.adversarial_injector import AdversarialInjector
from models import ThreatType


class TestAdversarialInjector:
    """Unit tests for Context Agent adversarial injection."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.injector = AdversarialInjector()
    
    # ========================================================================
    # Test 1: Context Contradiction Attack
    # ========================================================================
    def test_inject_context_contradiction_attack(self):
        """Test that contradiction attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_context_contradiction_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )
        
        # Assert - Signal structure
        assert signal.customer_name == "TestCorp"
        assert signal.threat_type == ThreatType.DEVICE_COMPROMISE
        assert signal.metadata is not None
        
        # Assert - Benign metadata (Context will say "trusted")
        assert signal.metadata["source_ip"] == "203.0.113.50"  # Public IP
        assert "Mozilla" in signal.metadata["user_agent"]  # Benign UA
        assert signal.metadata["request_count"] == 10  # Low volume
        
        # Assert - Malicious payload (Priority will detect)
        assert "compromise_indicators" in signal.metadata
        assert len(signal.metadata["compromise_indicators"]) > 0
        assert "attack_signature" in signal.metadata
        assert signal.metadata["severity_score"] > 0.9
    
    # ========================================================================
    # Test 2: Geo-IP Mismatch Attack
    # ========================================================================
    def test_inject_geo_ip_mismatch_attack(self):
        """Test that geo-IP mismatch attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_geo_ip_mismatch_attack(
            customer_name="GeoTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )
        
        # Assert
        assert signal.customer_name == "GeoTestCorp"
        assert signal.threat_type == ThreatType.BOT_TRAFFIC
        
        # Assert - Private IP with public geo-location
        source_ip = signal.metadata["source_ip"]
        geo_location = signal.metadata["geo_location"]
        
        assert self._is_private_ip(source_ip)
        assert geo_location != ""
        assert "," in geo_location  # Should have city, state/country format
    
    # ========================================================================
    # Test 3: Attack Tool User-Agent Attack
    # ========================================================================
    def test_inject_attack_tool_ua_attack(self):
        """Test that attack tool UA attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_attack_tool_ua_attack(
            customer_name="UATestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            attack_tool_index=0
        )
        
        # Assert
        assert signal.customer_name == "UATestCorp"
        assert signal.threat_type == ThreatType.BOT_TRAFFIC
        
        # Assert - Attack tool User-Agent
        user_agent = signal.metadata["user_agent"]
        assert any(tool.lower() in user_agent.lower() for tool in [
            "sqlmap", "nikto", "nmap", "burp", "metasploit", "w3af", "zap"
        ])
    
    # ========================================================================
    # Test 4: High Volume Attack
    # ========================================================================
    def test_inject_high_volume_attack(self):
        """Test that high volume attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_high_volume_attack(
            customer_name="VolumeTestCorp",
            threat_type=ThreatType.RATE_LIMIT_BREACH,
            request_count=5000
        )
        
        # Assert
        assert signal.customer_name == "VolumeTestCorp"
        assert signal.threat_type == ThreatType.RATE_LIMIT_BREACH
        assert signal.metadata["request_count"] == 5000
        assert signal.metadata["request_count"] > 1000  # Threshold for anomaly
    
    # ========================================================================
    # Test 5: Multi-Anomaly Attack
    # ========================================================================
    def test_inject_multi_anomaly_attack(self):
        """Test that multi-anomaly attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_multi_anomaly_attack(
            customer_name="MultiTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )
        
        # Assert
        assert signal.customer_name == "MultiTestCorp"
        
        # Assert - Multiple anomalies present
        # 1. Geo-IP mismatch
        assert self._is_private_ip(signal.metadata["source_ip"])
        assert signal.metadata["geo_location"] != ""
        
        # 2. Attack tool User-Agent
        user_agent = signal.metadata["user_agent"]
        assert any(tool.lower() in user_agent.lower() for tool in [
            "sqlmap", "nikto", "nmap", "burp", "metasploit"
        ])
        
        # 3. High volume
        assert signal.metadata["request_count"] > 1000
    
    # ========================================================================
    # Test 6: Combined Contradiction and Anomaly Attack
    # ========================================================================
    def test_inject_combined_attack(self):
        """Test that combined attack signal is created correctly."""
        
        # Act
        signal = self.injector.inject_combined_contradiction_and_anomaly_attack(
            customer_name="CombinedTestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )
        
        # Assert
        assert signal.customer_name == "CombinedTestCorp"
        
        # Assert - Benign metadata (for contradiction)
        assert not self._is_private_ip(signal.metadata["source_ip"])
        assert signal.metadata["request_count"] < 100
        
        # Assert - Attack tool UA (anomaly)
        user_agent = signal.metadata["user_agent"]
        assert any(tool.lower() in user_agent.lower() for tool in [
            "sqlmap", "nikto", "nmap", "burp", "metasploit"
        ])
        
        # Assert - Malicious payload (for contradiction)
        assert "compromise_indicators" in signal.metadata
        assert "attack_signature" in signal.metadata

    # ========================================================================
    # Test 7: Clean Signal (No Anomalies)
    # ========================================================================
    def test_inject_clean_signal(self):
        """Test that clean signal has no adversarial indicators."""

        # Act
        signal = self.injector.inject_clean_signal(
            customer_name="CleanTestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )

        # Assert
        assert signal.customer_name == "CleanTestCorp"
        assert signal.threat_type == ThreatType.BOT_TRAFFIC

        # Assert - No anomalies
        # 1. Public IP (no geo mismatch)
        assert not self._is_private_ip(signal.metadata["source_ip"])

        # 2. Benign User-Agent
        user_agent = signal.metadata["user_agent"]
        assert "Mozilla" in user_agent
        assert not any(tool.lower() in user_agent.lower() for tool in [
            "sqlmap", "nikto", "nmap", "burp", "metasploit"
        ])

        # 3. Normal volume
        assert signal.metadata["request_count"] < 1000

        # 4. No geo-location (to avoid mismatch)
        assert signal.metadata["geo_location"] == ""

    # ========================================================================
    # Test 8: Different Attack Tool User-Agents
    # ========================================================================
    def test_inject_different_attack_tools(self):
        """Test that different attack tool indices produce different UAs."""

        # Act
        signal1 = self.injector.inject_attack_tool_ua_attack(attack_tool_index=0)
        signal2 = self.injector.inject_attack_tool_ua_attack(attack_tool_index=1)
        signal3 = self.injector.inject_attack_tool_ua_attack(attack_tool_index=2)

        # Assert - Different User-Agents
        ua1 = signal1.metadata["user_agent"]
        ua2 = signal2.metadata["user_agent"]
        ua3 = signal3.metadata["user_agent"]

        assert ua1 != ua2
        assert ua2 != ua3
        assert ua1 != ua3

        # All should be attack tools
        for ua in [ua1, ua2, ua3]:
            assert any(tool.lower() in ua.lower() for tool in [
                "sqlmap", "nikto", "nmap", "burp", "metasploit", "w3af", "zap"
            ])

    # ========================================================================
    # Test 9: Custom Request Count
    # ========================================================================
    def test_inject_custom_request_count(self):
        """Test that custom request count is applied correctly."""

        # Act
        signal1 = self.injector.inject_high_volume_attack(request_count=2000)
        signal2 = self.injector.inject_high_volume_attack(request_count=10000)

        # Assert
        assert signal1.metadata["request_count"] == 2000
        assert signal2.metadata["request_count"] == 10000

    # ========================================================================
    # Test 10: Signal Metadata Completeness
    # ========================================================================
    def test_signal_metadata_completeness(self):
        """Test that all signals have required metadata fields."""

        # Act - Create all signal types
        signals = [
            self.injector.inject_context_contradiction_attack(),
            self.injector.inject_geo_ip_mismatch_attack(),
            self.injector.inject_attack_tool_ua_attack(),
            self.injector.inject_high_volume_attack(),
            self.injector.inject_multi_anomaly_attack(),
            self.injector.inject_combined_contradiction_and_anomaly_attack(),
            self.injector.inject_clean_signal()
        ]

        # Assert - All signals have required fields
        for signal in signals:
            assert signal.customer_name is not None
            assert signal.threat_type is not None
            assert signal.metadata is not None
            assert "source_ip" in signal.metadata
            assert "user_agent" in signal.metadata
            assert "request_count" in signal.metadata
            assert signal.id is not None  # Auto-generated
            assert signal.timestamp is not None  # Auto-generated

    # ========================================================================
    # Helper Methods
    # ========================================================================
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private range."""
        return (
            ip.startswith("10.") or
            ip.startswith("192.168.") or
            ip.startswith("172.16.") or
            ip.startswith("172.17.") or
            ip.startswith("172.18.") or
            ip.startswith("172.19.") or
            ip.startswith("172.20.") or
            ip.startswith("172.21.") or
            ip.startswith("172.22.") or
            ip.startswith("172.23.") or
            ip.startswith("172.24.") or
            ip.startswith("172.25.") or
            ip.startswith("172.26.") or
            ip.startswith("172.27.") or
            ip.startswith("172.28.") or
            ip.startswith("172.29.") or
            ip.startswith("172.30.") or
            ip.startswith("172.31.")
        )


class TestHistoricalAgentInjector:
    """Unit tests for Historical Agent adversarial injection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.injector = AdversarialInjector()

    # ========================================================================
    # Test 1: High FP Rate Attack
    # ========================================================================
    def test_inject_historical_high_fp_rate_attack(self):
        """Test that high FP rate attack is created correctly."""

        # Act
        result = self.injector.inject_historical_high_fp_rate_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            fp_rate=0.90
        )

        # Assert - Structure
        assert "signal" in result
        assert "historical_data" in result
        assert "attack_type" in result
        assert result["attack_type"] == "high_fp_rate"

        # Assert - Signal
        signal = result["signal"]
        assert signal.customer_name == "TestCorp"
        assert signal.threat_type == ThreatType.BOT_TRAFFIC

        # Assert - Historical data
        hist = result["historical_data"]
        assert hist["false_positive_rate"] == 0.90
        assert hist["false_positive_rate"] > 0.8  # Above threshold
        assert hist["similar_incidents"] > 0
        assert hist["false_positive_count"] == int(hist["similar_incidents"] * 0.90)

    # ========================================================================
    # Test 2: High Incident Count Attack
    # ========================================================================
    def test_inject_historical_high_incident_count_attack(self):
        """Test that high incident count attack is created correctly."""

        # Act
        result = self.injector.inject_historical_high_incident_count_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            incident_count=50
        )

        # Assert
        assert result["attack_type"] == "high_incident_count"

        hist = result["historical_data"]
        assert hist["similar_incidents"] == 50
        assert hist["similar_incidents"] > 20  # Above threshold
        assert hist["false_positive_count"] > 0
        assert hist["false_positive_rate"] > 0

    # ========================================================================
    # Test 3: Temporal Clustering Attack
    # ========================================================================
    def test_inject_historical_temporal_clustering_attack(self):
        """Test that temporal clustering attack is created correctly."""

        # Act
        result = self.injector.inject_historical_temporal_clustering_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC,
            cluster_count=15,
            time_window_hours=1
        )

        # Assert
        assert result["attack_type"] == "temporal_clustering"

        hist = result["historical_data"]
        assert hist["similar_incidents"] == 15
        assert hist["similar_incidents"] > 10  # Above threshold
        assert hist["temporal_clustering"] is True
        assert "cluster_timestamps" in hist
        assert len(hist["cluster_timestamps"]) == 15
        assert hist["time_window_hours"] == 1

    # ========================================================================
    # Test 4: Multi-Anomaly Attack
    # ========================================================================
    def test_inject_historical_multi_anomaly_attack(self):
        """Test that multi-anomaly attack is created correctly."""

        # Act
        result = self.injector.inject_historical_multi_anomaly_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )

        # Assert
        assert result["attack_type"] == "multi_anomaly"

        hist = result["historical_data"]
        # Should have all three anomalies
        assert hist["false_positive_rate"] >= 0.8  # High FP rate
        assert hist["similar_incidents"] > 20  # High incident count
        assert hist["temporal_clustering"] is True  # Temporal clustering
        assert "cluster_timestamps" in hist
        assert len(hist["cluster_timestamps"]) > 10

    # ========================================================================
    # Test 5: Historical-Priority Contradiction Attack
    # ========================================================================
    def test_inject_historical_priority_contradiction_attack(self):
        """Test that Historical-Priority contradiction attack is created correctly."""

        # Act
        result = self.injector.inject_historical_priority_contradiction_attack(
            customer_name="TestCorp",
            threat_type=ThreatType.DEVICE_COMPROMISE
        )

        # Assert
        assert result["attack_type"] == "historical_priority_contradiction"

        # Signal should have malicious indicators (for Priority Agent)
        signal = result["signal"]
        assert "compromise_indicators" in signal.metadata
        assert len(signal.metadata["compromise_indicators"]) > 0
        assert signal.metadata["severity_score"] > 0.9

        # Historical data should suggest benign (contradiction)
        hist = result["historical_data"]
        assert hist["false_positive_rate"] > 0.8
        assert "benign" in hist["analysis_hint"].lower() or "false positive" in hist["analysis_hint"].lower()

    # ========================================================================
    # Test 6: Clean Historical Data
    # ========================================================================
    def test_inject_historical_clean_data(self):
        """Test that clean historical data is created correctly."""

        # Act
        result = self.injector.inject_historical_clean_data(
            customer_name="TestCorp",
            threat_type=ThreatType.BOT_TRAFFIC
        )

        # Assert
        assert result["attack_type"] == "clean"

        hist = result["historical_data"]
        # Should have normal values (no anomalies)
        assert hist["false_positive_rate"] < 0.8  # Below threshold
        assert hist["similar_incidents"] < 20  # Below threshold
        assert "temporal_clustering" not in hist or hist["temporal_clustering"] is False

    # ========================================================================
    # Test 7: Verify All Methods Return Correct Structure
    # ========================================================================
    def test_all_historical_methods_return_dict_with_required_keys(self):
        """Test that all Historical injection methods return correct structure."""

        methods = [
            self.injector.inject_historical_high_fp_rate_attack,
            self.injector.inject_historical_high_incident_count_attack,
            self.injector.inject_historical_temporal_clustering_attack,
            self.injector.inject_historical_multi_anomaly_attack,
            self.injector.inject_historical_priority_contradiction_attack,
            self.injector.inject_historical_clean_data
        ]

        for method in methods:
            result = method()

            # All should return dict with these keys
            assert isinstance(result, dict)
            assert "signal" in result
            assert "historical_data" in result
            assert "attack_type" in result

            # Signal should be ThreatSignal
            from models import ThreatSignal
            assert isinstance(result["signal"], ThreatSignal)

            # Historical data should be dict
            assert isinstance(result["historical_data"], dict)

