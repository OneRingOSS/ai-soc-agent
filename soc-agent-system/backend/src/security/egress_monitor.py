"""
Egress violation monitoring for Tier 3A.
Tracks attempted unauthorized outbound connections blocked by NetworkPolicy.
Feeds into AdversarialDetector for infrastructure vs historical contradiction analysis.

Attack scenario: Historical Agent says "benign" but NetworkPolicy blocks suspicious egress.
This is a strong signal of historical note poisoning (insider attempting to suppress detection).
"""

import time
import logging
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# In-memory store (production would use Redis or persistent storage)
_violation_store: List["EgressViolation"] = []


class EgressViolation(BaseModel):
    """Represents a blocked egress attempt detected by NetworkPolicy."""
    timestamp: float
    source_pod: str
    attempted_destination: str
    blocked_by: str  # e.g., "network_policy", "firewall", "dns_blacklist"
    metadata: Optional[dict] = None


def record_egress_violation(violation: EgressViolation) -> None:
    """
    Record an egress violation from infrastructure telemetry.
    
    Called by:
    - Webhook endpoint when K8s NetworkPolicy audit logs arrive
    - DevOps agent when analyzing infrastructure telemetry
    - Network monitoring systems
    
    Args:
        violation: The egress violation details
    """
    _violation_store.append(violation)
    logger.warning(
        f"[EGRESS_VIOLATION] {violation.source_pod} attempted {violation.attempted_destination} "
        f"(blocked by {violation.blocked_by})"
    )


def get_recent_violations(
    since_timestamp: Optional[float] = None,
    max_count: int = 100
) -> List[EgressViolation]:
    """
    Get recent egress violations for contradiction analysis.
    
    Args:
        since_timestamp: Only return violations after this Unix timestamp
        max_count: Maximum number of violations to return
    
    Returns:
        List of egress violations, most recent first
    """
    if since_timestamp is None:
        since_timestamp = time.time() - 3600  # Default: last hour
    
    recent = [
        v for v in _violation_store
        if v.timestamp >= since_timestamp
    ]
    
    # Sort by timestamp descending (most recent first)
    recent.sort(key=lambda v: v.timestamp, reverse=True)
    
    return recent[:max_count]


def has_recent_violations(threshold_seconds: int = 3600) -> bool:
    """
    Check if there are any recent egress violations.
    
    Used by AdversarialDetector to determine if infrastructure contradicts
    Historical Agent's "benign" assessment.
    
    Args:
        threshold_seconds: Consider violations within this time window
    
    Returns:
        True if there are violations within the threshold, False otherwise
    """
    cutoff = time.time() - threshold_seconds
    return any(v.timestamp >= cutoff for v in _violation_store)


def clear_violations() -> None:
    """Clear all recorded violations (for testing)."""
    _violation_store.clear()
