"""Tests for MITRE ATT&CK tag extraction and merging."""
import sys
import pytest

sys.path.insert(0, 'src')

from models import MitreTag
from mitre_parser import extract_mitre_tags, build_wazuh_tags, merge_mitre_tags


class TestExtractMitreTags:
    """Test MITRE tag extraction from LLM output."""
    
    def test_extract_valid_single_tag(self):
        """Test extraction of single valid MITRE tag."""
        output = """
        Analysis text here.
        <MITRE_TAGS>
        [
          {
            "technique_id": "T1566.001",
            "technique_name": "Spearphishing Attachment",
            "tactic": "Initial Access",
            "tactic_id": "TA0001",
            "confidence": 0.85
          }
        ]
        </MITRE_TAGS>
        More text.
        """
        tags = extract_mitre_tags(output)
        
        assert len(tags) == 1
        assert tags[0].technique_id == "T1566.001"
        assert tags[0].technique_name == "Spearphishing Attachment"
        assert tags[0].tactic == "Initial Access"
        assert tags[0].tactic_id == "TA0001"
        assert tags[0].confidence == 0.85
        assert tags[0].source == "priority_agent"
    
    def test_extract_multiple_tags(self):
        """Test extraction of multiple MITRE tags."""
        output = """
        <MITRE_TAGS>
        [
          {"technique_id": "T1", "technique_name": "Test1", "tactic": "Tactic1", "tactic_id": "TA0001", "confidence": 0.9},
          {"technique_id": "T2", "technique_name": "Test2", "tactic": "Tactic2", "tactic_id": "TA0002", "confidence": 0.8}
        ]
        </MITRE_TAGS>
        """
        tags = extract_mitre_tags(output)
        
        assert len(tags) == 2
        assert tags[0].technique_id == "T1"
        assert tags[1].technique_id == "T2"
    
    def test_extract_no_mitre_block(self):
        """Test graceful handling when no MITRE_TAGS block present."""
        output = "Just regular analysis text without MITRE tags."
        tags = extract_mitre_tags(output)
        
        assert tags == []
    
    def test_extract_malformed_json(self):
        """Test graceful handling of malformed JSON."""
        output = "<MITRE_TAGS>[{invalid json, missing quotes}]</MITRE_TAGS>"
        tags = extract_mitre_tags(output)
        
        assert tags == []
    
    def test_extract_filters_low_confidence(self):
        """Test that tags with confidence < 0.6 are filtered out."""
        output = """
        <MITRE_TAGS>
        [
          {"technique_id": "T1", "technique_name": "Low", "tactic": "Test", "tactic_id": "TA0001", "confidence": 0.5},
          {"technique_id": "T2", "technique_name": "High", "tactic": "Test", "tactic_id": "TA0002", "confidence": 0.7}
        ]
        </MITRE_TAGS>
        """
        tags = extract_mitre_tags(output)
        
        assert len(tags) == 1
        assert tags[0].technique_id == "T2"
        assert tags[0].confidence == 0.7
    
    def test_extract_skips_malformed_entries(self):
        """Test that malformed entries are skipped without breaking extraction."""
        output = """
        <MITRE_TAGS>
        [
          {"technique_id": "T1", "tactic": "Test", "tactic_id": "TA0001", "confidence": 0.8},
          {"missing_technique_id": true},
          {"technique_id": "T2", "tactic": "Test", "tactic_id": "TA0002", "confidence": 0.9}
        ]
        </MITRE_TAGS>
        """
        tags = extract_mitre_tags(output)
        
        assert len(tags) == 2
        assert tags[0].technique_id == "T1"
        assert tags[1].technique_id == "T2"
    
    def test_extract_with_custom_source(self):
        """Test that custom source parameter is applied."""
        output = """
        <MITRE_TAGS>
        [{"technique_id": "T1", "technique_name": "Test", "tactic": "Test", "tactic_id": "TA0001", "confidence": 0.8}]
        </MITRE_TAGS>
        """
        tags = extract_mitre_tags(output, source="custom_source")
        
        assert tags[0].source == "custom_source"
    
    def test_extract_empty_array(self):
        """Test handling of empty MITRE_TAGS array."""
        output = "<MITRE_TAGS>[]</MITRE_TAGS>"
        tags = extract_mitre_tags(output)
        
        assert tags == []
    
    def test_extract_case_insensitive(self):
        """Test that tag extraction is case-insensitive."""
        output = """
        <mitre_tags>
        [{"technique_id": "T1", "technique_name": "Test", "tactic": "Test", "tactic_id": "TA0001", "confidence": 0.8}]
        </mitre_tags>
        """
        tags = extract_mitre_tags(output)

        assert len(tags) == 1
        assert tags[0].technique_id == "T1"


class TestBuildWazuhTags:
    """Test building MITRE tags from Wazuh hints."""

    def test_build_from_hints(self):
        """Test building tags from valid Wazuh hints."""
        hints = ["T1475", "T1533"]
        tags = build_wazuh_tags(hints)

        assert len(tags) == 2
        assert all(tag.source == "wazuh" for tag in tags)
        assert all(tag.confidence == 1.0 for tag in tags)
        assert tags[0].technique_id == "T1475"
        assert tags[1].technique_id == "T1533"

    def test_build_filters_invalid_ids(self):
        """Test that non-T-prefixed IDs are filtered out."""
        hints = ["T1475", "INVALID", "T1533", "123"]
        tags = build_wazuh_tags(hints)

        assert len(tags) == 2
        assert all(tag.technique_id.startswith("T") for tag in tags)

    def test_build_empty_hints(self):
        """Test handling of empty hints list."""
        tags = build_wazuh_tags([])

        assert tags == []


class TestMergeMitreTags:
    """Test merging MITRE tags from multiple sources."""

    def test_merge_wazuh_first(self):
        """Test that Wazuh tags come first in merged list."""
        wazuh_tags = [
            MitreTag(technique_id="T1", technique_name="W1", tactic="Test", tactic_id="TA0001", source="wazuh")
        ]
        priority_tags = [
            MitreTag(technique_id="T2", technique_name="P1", tactic="Test", tactic_id="TA0002", source="priority_agent")
        ]

        merged = merge_mitre_tags(wazuh_tags, priority_tags)

        assert len(merged) == 2
        assert merged[0].source == "wazuh"
        assert merged[1].source == "priority_agent"

    def test_merge_deduplicates_by_technique_id(self):
        """Test that duplicate technique_ids are removed."""
        wazuh_tags = [
            MitreTag(technique_id="T1", technique_name="W1", tactic="Test", tactic_id="TA0001", source="wazuh")
        ]
        priority_tags = [
            MitreTag(technique_id="T1", technique_name="P1", tactic="Test", tactic_id="TA0001", source="priority_agent"),
            MitreTag(technique_id="T2", technique_name="P2", tactic="Test", tactic_id="TA0002", source="priority_agent")
        ]

        merged = merge_mitre_tags(wazuh_tags, priority_tags)

        assert len(merged) == 2
        assert merged[0].source == "wazuh"  # Wazuh version kept
        assert merged[1].technique_id == "T2"

    def test_merge_caps_at_six(self):
        """Test that merged list is capped at 6 techniques."""
        wazuh_tags = [
            MitreTag(technique_id=f"T{i}", technique_name=f"W{i}", tactic="Test", tactic_id="TA0001", source="wazuh")
            for i in range(4)
        ]
        priority_tags = [
            MitreTag(technique_id=f"T{i}", technique_name=f"P{i}", tactic="Test", tactic_id="TA0001", source="priority_agent")
            for i in range(4, 10)
        ]

        merged = merge_mitre_tags(wazuh_tags, priority_tags)

        assert len(merged) == 6
        assert all(tag.technique_id in [f"T{i}" for i in range(6)] for tag in merged)

    def test_merge_empty_lists(self):
        """Test merging with empty lists."""
        merged = merge_mitre_tags([], [])

        assert merged == []

    def test_merge_only_wazuh(self):
        """Test merging with only Wazuh tags."""
        wazuh_tags = [
            MitreTag(technique_id="T1", technique_name="W1", tactic="Test", tactic_id="TA0001", source="wazuh")
        ]

        merged = merge_mitre_tags(wazuh_tags, [])

        assert len(merged) == 1
        assert merged[0].source == "wazuh"

    def test_merge_only_priority(self):
        """Test merging with only PriorityAgent tags."""
        priority_tags = [
            MitreTag(technique_id="T1", technique_name="P1", tactic="Test", tactic_id="TA0001", source="priority_agent")
        ]

        merged = merge_mitre_tags([], priority_tags)

        assert len(merged) == 1
        assert merged[0].source == "priority_agent"

