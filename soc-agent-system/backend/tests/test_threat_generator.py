"""Tests for threat generator."""
import pytest
import sys
sys.path.insert(0, 'src')

from threat_generator import ThreatGenerator
from models import ThreatType


def test_threat_generator_initialization():
    """Test threat generator can be initialized."""
    generator = ThreatGenerator()
    assert generator is not None


def test_generate_random_threat(threat_generator_seeded):
    """Test random threat generation."""
    signal = threat_generator_seeded.generate_random_threat()

    assert signal is not None
    assert signal.threat_type in ThreatType
    assert signal.customer_name in ThreatGenerator.CUSTOMERS
    assert signal.metadata is not None
    assert isinstance(signal.metadata, dict)


def test_generate_bot_traffic(threat_generator_seeded):
    """Test bot traffic threat generation."""
    signal = threat_generator_seeded.generate_bot_traffic()

    assert signal.threat_type == ThreatType.BOT_TRAFFIC
    assert "source_ip" in signal.metadata
    assert "request_count" in signal.metadata
    assert "user_agent" in signal.metadata


def test_generate_proxy_network(threat_generator_seeded):
    """Test proxy network threat generation."""
    signal = threat_generator_seeded.generate_proxy_network()

    assert signal.threat_type == ThreatType.PROXY_NETWORK
    assert "proxy_ips" in signal.metadata
    assert "geographic_spread" in signal.metadata


def test_generate_device_compromise(threat_generator_seeded):
    """Test device compromise threat generation."""
    signal = threat_generator_seeded.generate_device_compromise()

    assert signal.threat_type == ThreatType.DEVICE_COMPROMISE
    assert "device_id" in signal.metadata
    assert "compromise_indicators" in signal.metadata


def test_generate_anomaly_detection(threat_generator_seeded):
    """Test anomaly detection threat generation."""
    signal = threat_generator_seeded.generate_anomaly_detection()

    assert signal.threat_type == ThreatType.ANOMALY_DETECTION
    assert "baseline_comparison" in signal.metadata
    assert "anomaly_score" in signal.metadata
    assert "deviations" in signal.metadata


def test_generate_rate_limit_breach(threat_generator_seeded):
    """Test rate limit breach threat generation."""
    signal = threat_generator_seeded.generate_rate_limit_breach()

    assert signal.threat_type == ThreatType.RATE_LIMIT_BREACH
    assert "actual_rate" in signal.metadata
    assert "configured_limit" in signal.metadata


def test_generate_geo_anomaly(threat_generator_seeded):
    """Test geo anomaly threat generation."""
    signal = threat_generator_seeded.generate_geo_anomaly()

    assert signal.threat_type == ThreatType.GEO_ANOMALY
    assert "location_1" in signal.metadata
    assert "location_2" in signal.metadata
    assert "time_delta_minutes" in signal.metadata


def test_generate_threat_by_type(threat_generator_seeded):
    """Test generating threat by specific type."""
    signal = threat_generator_seeded.generate_threat_by_type(ThreatType.BOT_TRAFFIC)
    
    assert signal.threat_type == ThreatType.BOT_TRAFFIC


def test_generate_scenario_crypto_surge(threat_generator_seeded):
    """Test crypto surge scenario."""
    signal = threat_generator_seeded.generate_scenario_threat("crypto_surge")
    
    assert "CryptoExchange" in signal.customer_name
    assert signal.threat_type == ThreatType.RATE_LIMIT_BREACH


def test_generate_scenario_bot_attack(threat_generator_seeded):
    """Test bot attack scenario."""
    signal = threat_generator_seeded.generate_scenario_threat("bot_attack")
    
    assert signal.threat_type == ThreatType.BOT_TRAFFIC


def test_generate_scenario_geo_impossible(threat_generator_seeded):
    """Test impossible travel scenario."""
    signal = threat_generator_seeded.generate_scenario_threat("geo_impossible")
    
    assert signal.threat_type == ThreatType.GEO_ANOMALY


def test_generate_scenario_invalid():
    """Test invalid scenario returns random threat."""
    generator = ThreatGenerator()
    signal = generator.generate_scenario_threat("invalid_scenario")
    
    assert signal is not None
    assert signal.threat_type in ThreatType


def test_deterministic_generation():
    """Test that seeded generator produces deterministic results."""
    # Generate multiple threats with same seed to verify determinism
    gen1 = ThreatGenerator(seed=42)
    threats1 = [gen1.generate_random_threat() for _ in range(5)]

    gen2 = ThreatGenerator(seed=42)
    threats2 = [gen2.generate_random_threat() for _ in range(5)]

    # All threats should match
    for t1, t2 in zip(threats1, threats2):
        assert t1.threat_type == t2.threat_type
        assert t1.customer_name == t2.customer_name

