"""Tests for MITRE ATT&CK fallback mappings."""
import sys
import pytest

sys.path.insert(0, 'src')

from models import ThreatType
from mitre_fallback import get_fallback_mitre_tags, THREAT_TYPE_TO_MITRE


class TestFallbackMitreTags:
    """Test fallback MITRE tag retrieval."""
    
    def test_device_compromise_fallback(self):
        """Test fallback tags for DEVICE_COMPROMISE."""
        tags = get_fallback_mitre_tags(ThreatType.DEVICE_COMPROMISE)
        
        assert len(tags) == 3
        assert all(tag.source == "fallback" for tag in tags)
        assert all(tag.confidence == 0.6 for tag in tags)
        
        # Check specific techniques
        technique_ids = [tag.technique_id for tag in tags]
        assert "T1475" in technique_ids  # Deliver Malicious App
        assert "T1533" in technique_ids  # Data from Local System
        assert "T1418" in technique_ids  # Application Discovery
    
    def test_bot_traffic_fallback(self):
        """Test fallback tags for BOT_TRAFFIC."""
        tags = get_fallback_mitre_tags(ThreatType.BOT_TRAFFIC)

        assert len(tags) == 2
        assert all(tag.source == "fallback" for tag in tags)

        technique_ids = [tag.technique_id for tag in tags]
        assert "T1659" in technique_ids  # Content Injection
        assert "T1498" in technique_ids  # Network Denial of Service

    def test_proxy_network_fallback(self):
        """Test fallback tags for PROXY_NETWORK."""
        tags = get_fallback_mitre_tags(ThreatType.PROXY_NETWORK)

        assert len(tags) == 2
        assert all(tag.source == "fallback" for tag in tags)

        technique_ids = [tag.technique_id for tag in tags]
        assert "T1090" in technique_ids  # Proxy
        assert "T1071" in technique_ids  # Application Layer Protocol

    def test_anomaly_detection_fallback(self):
        """Test fallback tags for ANOMALY_DETECTION."""
        tags = get_fallback_mitre_tags(ThreatType.ANOMALY_DETECTION)

        assert len(tags) == 2
        assert all(tag.source == "fallback" for tag in tags)

        technique_ids = [tag.technique_id for tag in tags]
        assert "T1078" in technique_ids  # Valid Accounts
        assert "T1562" in technique_ids  # Impair Defenses

    def test_rate_limit_breach_fallback(self):
        """Test fallback tags for RATE_LIMIT_BREACH."""
        tags = get_fallback_mitre_tags(ThreatType.RATE_LIMIT_BREACH)

        assert len(tags) == 2
        assert all(tag.source == "fallback" for tag in tags)

        technique_ids = [tag.technique_id for tag in tags]
        assert "T1110" in technique_ids  # Brute Force
        assert "T1499" in technique_ids  # Endpoint Denial of Service

    def test_geo_anomaly_fallback(self):
        """Test fallback tags for GEO_ANOMALY."""
        tags = get_fallback_mitre_tags(ThreatType.GEO_ANOMALY)

        assert len(tags) == 2
        assert all(tag.source == "fallback" for tag in tags)

        technique_ids = [tag.technique_id for tag in tags]
        assert "T1078" in technique_ids  # Valid Accounts
        assert "T1535" in technique_ids  # Unused/Unsupported Cloud Regions
    
    def test_all_tags_have_required_fields(self):
        """Test that all fallback tags have required fields."""
        for threat_type in ThreatType:
            tags = get_fallback_mitre_tags(threat_type)
            
            for tag in tags:
                assert tag.technique_id is not None
                assert tag.technique_id.startswith("T")
                assert tag.technique_name is not None
                assert tag.tactic is not None
                assert tag.tactic_id is not None
                assert tag.tactic_id.startswith("TA")
                assert tag.confidence == 0.6
                assert tag.source == "fallback"
    
    def test_mobile_attack_tactics(self):
        """Test that DEVICE_COMPROMISE uses Mobile ATT&CK tactics."""
        tags = get_fallback_mitre_tags(ThreatType.DEVICE_COMPROMISE)

        # Mobile ATT&CK tactics are TA0027-TA0037
        for tag in tags:
            tactic_num = int(tag.tactic_id[2:])  # Extract number from TA0027
            assert 27 <= tactic_num <= 41, f"Expected Mobile ATT&CK tactic, got {tag.tactic_id}"

    def test_all_threat_types_mapped(self):
        """Test that all ThreatType enum values have mappings."""
        for threat_type in ThreatType:
            tags = get_fallback_mitre_tags(threat_type)

            # All threat types should have at least one mapping
            assert len(tags) > 0, f"No fallback mapping for {threat_type}"
            assert isinstance(tags, list)
    
    def test_mapping_table_structure(self):
        """Test that the mapping table has correct structure."""
        for threat_type, techniques in THREAT_TYPE_TO_MITRE.items():
            assert isinstance(techniques, list)
            assert len(techniques) > 0
            
            for tech in techniques:
                assert "technique_id" in tech
                assert "technique_name" in tech
                assert "tactic" in tech
                assert "tactic_id" in tech
                assert tech["technique_id"].startswith("T")
                assert tech["tactic_id"].startswith("TA")

