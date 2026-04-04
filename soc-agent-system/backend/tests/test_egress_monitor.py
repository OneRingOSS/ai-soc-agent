"""
Unit tests for egress_monitor.py (Tier 3A)
Tests egress violation recording, retrieval, and AdversarialDetector integration
"""

import pytest
import time
import sys
sys.path.insert(0, 'src')

from security.egress_monitor import (
    record_egress_violation,
    get_recent_violations,
    has_recent_violations,
    clear_violations,
    EgressViolation
)


class TestEgressMonitoring:
    """Test egress violation tracking"""
    
    def setup_method(self):
        """Clear violations before each test"""
        clear_violations()
    
    def test_record_and_retrieve_violation(self):
        """Test basic record and retrieve"""
        violation = EgressViolation(
            timestamp=time.time(),
            source_pod="soc-backend-abc123",
            attempted_destination="169.254.169.254:80",  # AWS IMDS
            blocked_by="network_policy"
        )
        
        record_egress_violation(violation)
        
        violations = get_recent_violations()
        assert len(violations) == 1
        assert violations[0].attempted_destination == "169.254.169.254:80"
        assert violations[0].blocked_by == "network_policy"
    
    def test_multiple_violations_sorted(self):
        """Test violations are sorted by timestamp descending"""
        now = time.time()
        
        v1 = EgressViolation(
            timestamp=now - 100,
            source_pod="pod1",
            attempted_destination="dest1",
            blocked_by="netpol"
        )
        v2 = EgressViolation(
            timestamp=now,
            source_pod="pod2",
            attempted_destination="dest2",
            blocked_by="netpol"
        )
        v3 = EgressViolation(
            timestamp=now - 50,
            source_pod="pod3",
            attempted_destination="dest3",
            blocked_by="netpol"
        )
        
        record_egress_violation(v1)
        record_egress_violation(v2)
        record_egress_violation(v3)
        
        violations = get_recent_violations()
        assert len(violations) == 3
        # Should be sorted by timestamp descending (most recent first)
        assert violations[0].source_pod == "pod2"  # now
        assert violations[1].source_pod == "pod3"  # now - 50
        assert violations[2].source_pod == "pod1"  # now - 100
    
    def test_since_timestamp_filter(self):
        """Test filtering by timestamp"""
        now = time.time()
        
        old_violation = EgressViolation(
            timestamp=now - 7200,  # 2 hours ago
            source_pod="old_pod",
            attempted_destination="dest1",
            blocked_by="netpol"
        )
        recent_violation = EgressViolation(
            timestamp=now - 60,  # 1 minute ago
            source_pod="recent_pod",
            attempted_destination="dest2",
            blocked_by="netpol"
        )
        
        record_egress_violation(old_violation)
        record_egress_violation(recent_violation)
        
        # Get violations from last hour only
        violations = get_recent_violations(since_timestamp=now - 3600)
        assert len(violations) == 1
        assert violations[0].source_pod == "recent_pod"
    
    def test_max_count_limit(self):
        """Test max_count parameter"""
        now = time.time()
        
        # Record 10 violations
        for i in range(10):
            v = EgressViolation(
                timestamp=now - i,
                source_pod=f"pod{i}",
                attempted_destination="dest",
                blocked_by="netpol"
            )
            record_egress_violation(v)
        
        violations = get_recent_violations(max_count=5)
        assert len(violations) == 5
    
    def test_has_recent_violations(self):
        """Test has_recent_violations helper"""
        assert not has_recent_violations()

        # Record a violation in the past (2 seconds ago)
        violation = EgressViolation(
            timestamp=time.time() - 2,
            source_pod="pod1",
            attempted_destination="dest1",
            blocked_by="netpol"
        )
        record_egress_violation(violation)

        assert has_recent_violations(threshold_seconds=3600)  # Should find it
        assert not has_recent_violations(threshold_seconds=1)  # 1-second window too short
    
    def test_clear_violations(self):
        """Test clearing violations"""
        violation = EgressViolation(
            timestamp=time.time(),
            source_pod="pod1",
            attempted_destination="dest1",
            blocked_by="netpol"
        )
        record_egress_violation(violation)
        
        assert len(get_recent_violations()) == 1
        clear_violations()
        assert len(get_recent_violations()) == 0


class TestEgressViolationModel:
    """Test EgressViolation Pydantic model"""
    
    def test_valid_violation(self):
        """Test creating valid violation"""
        v = EgressViolation(
            timestamp=time.time(),
            source_pod="soc-backend-abc",
            attempted_destination="malicious.example.com:443",
            blocked_by="network_policy",
            metadata={"rule": "deny-all-egress"}
        )
        assert v.source_pod == "soc-backend-abc"
        assert v.metadata["rule"] == "deny-all-egress"
    
    def test_optional_metadata(self):
        """Test metadata is optional"""
        v = EgressViolation(
            timestamp=time.time(),
            source_pod="pod",
            attempted_destination="dest",
            blocked_by="firewall"
        )
        assert v.metadata is None
