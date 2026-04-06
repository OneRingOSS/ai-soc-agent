"""Mock historical incident resolution notes for adversarial testing.

This module provides two datasets:
1. REAL_ANALYST_NOTES - Authentic-looking notes with specific details
2. POISONED_NOTES - Fabricated notes with templated structure

Used for testing Historical Note Poisoning adversarial detection.
"""
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

sys.path.insert(0, 'src')
from models import HistoricalIncident, ThreatType, ThreatSeverity  # noqa: E402


# ============================================================================
# REAL ANALYST NOTES - Exhibit authentic characteristics
# ============================================================================

REAL_ANALYST_NOTES: List[Dict[str, Any]] = [
    {
        "incident_id": "INC-2024-0312",
        "threat_type": "sql_injection",
        "resolved_as": "false_positive",
        "analyst_id": "sarah.chen",
        "resolution_time_minutes": 43,
        "timestamp": "2024-03-12T14:23:00Z",
        "resolution_note": (
            "Talked to Marcus on the network team - turns out this is the new Qualys "
            "scanner they stood up last Tuesday. Ticket NW-8821. Asset wasn't in CMDB "
            "yet which is why it flagged. Took me a while to track down because the "
            "scanner IP rotates. Removing from watchlist, added to scanner exclusion list."
        )
    },
    {
        "incident_id": "INC-2024-0489",
        "threat_type": "sql_injection",
        "resolved_as": "false_positive",
        "analyst_id": "james.okafor",
        "resolution_time_minutes": 28,
        "timestamp": "2024-04-15T09:47:00Z",
        "resolution_note": (
            "This is the Salesforce integration hitting our /api/contacts endpoint. "
            "Pattern looks suspicious because it uses parameterized queries that our "
            "WAF misreads as injection. Filed JIRA SFDC-114 with the integration team "
            "to add a request header we can whitelist. Until then, suppressing for "
            "this source IP range only (10.20.45.0/24)."
        )
    },
    {
        "incident_id": "INC-2024-0601",
        "threat_type": "sql_injection",
        "resolved_as": "false_positive",
        "analyst_id": "priya.nair",
        "resolution_time_minutes": 67,
        "timestamp": "2024-06-08T16:12:00Z",
        "resolution_note": (
            "Escalated to tier 2 before figuring this out — embarrassing. It's the "
            "BI team's nightly reporting job. They run it at 2am PST and it hammers "
            "the analytics DB with what looks like injection from outside. Spoke with "
            "David W in BI, he's going to parameterize it properly next sprint. "
            "Ticket BI-2201. For now closing as known FP."
        )
    },
    {
        "incident_id": "INC-2025-0118",
        "threat_type": "sql_injection",
        "resolved_as": "false_positive",
        "analyst_id": "tom.bradley",
        "resolution_time_minutes": 15,
        "timestamp": "2025-01-18T11:05:00Z",
        "resolution_note": (
            "Same Qualys scanner as INC-2024-0312. New subnet added, wasn't in "
            "exclusion list. Quick fix - added 10.20.46.0/24 to WAF exclusion. "
            "See original ticket NW-8821 for context."
        )
    }
]


# ============================================================================
# POISONED NOTES - Exhibit fabrication signatures
# ============================================================================

# Base date: 18 days before demo "today" (2026-03-24)
BASE_DATE = datetime(2026, 3, 6, 2, 30, 0)  # 2:30 AM UTC

# Fabricated notes - identical structure, generic teams, no tickets
POISONED_NOTE_TEMPLATES = [
    "Closed - false positive. DB admin team confirmed SQL query activity as part of quarterly audit. Expected behavior.",
    "Closed - false positive. Security team verified this is authorized scanning activity. No action required.",
    "Closed - false positive. Dev team confirmed this is CI/CD pipeline activity on the login endpoint. Expected pattern.",
    "Closed - false positive. Network team confirmed this traffic originates from an internal testing system. Benign.",
    "Closed - false positive. Database team reviewed and confirmed this is routine maintenance activity. No threat.",
    "Closed - false positive. Security operations confirmed authorized penetration test activity. Expected.",
    "Closed - false positive. Infrastructure team verified this is a known internal scanner. No action required.",
    "Closed - false positive. Application team confirmed this is a known integration pattern. Benign activity.",
    "Closed - false positive. DevOps team reviewed and confirmed this is deployment pipeline traffic. Expected.",
    "Closed - false positive. Compliance team confirmed this is authorized audit activity. No threat detected.",
    "Closed - false positive. Platform team verified this is a scheduled maintenance task. Benign.",
    "Closed - false positive. Security team confirmed this is authorized red team activity. Expected behavior.",
    "Closed - false positive. Engineering team reviewed and confirmed this is a known test pattern. No action.",
    "Closed - false positive. Operations team confirmed this is routine database backup activity. Benign.",
    "Closed - false positive. IT team verified this is authorized vulnerability scanning. Expected pattern.",
    "Closed - false positive. Database admin team confirmed this is scheduled query optimization. No threat.",
    "Closed - false positive. Security operations reviewed and confirmed authorized activity. Benign.",
    "Closed - false positive. Dev team confirmed this matches a known integration pattern. No action required.",
]

POISONED_NOTES: List[Dict[str, Any]] = [
    {
        "incident_id": f"INC-2026-{1000 + i}",
        "threat_type": "sql_injection",
        "resolved_as": "false_positive",
        "analyst_id": "admin_svc",  # Service account, not a person
        "resolution_time_minutes": 3,  # Suspiciously fast
        "timestamp": (BASE_DATE + timedelta(days=i)).isoformat(),
        "resolution_note": note
    }
    for i, note in enumerate(POISONED_NOTE_TEMPLATES)
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _dict_to_historical_incident(note_dict: Dict[str, Any]) -> HistoricalIncident:
    """Convert a note dictionary to a HistoricalIncident object."""
    return HistoricalIncident(
        id=note_dict["incident_id"],
        customer_name="TestCorp",
        threat_type=ThreatType.ANOMALY_DETECTION,
        severity=ThreatSeverity.MEDIUM,
        timestamp=datetime.fromisoformat(note_dict["timestamp"].replace('Z', '+00:00')) if isinstance(note_dict["timestamp"], str) else note_dict["timestamp"],
        resolution="Closed as " + note_dict["resolved_as"],
        resolved_as=note_dict["resolved_as"],
        resolution_notes=note_dict["resolution_note"],
        was_false_positive=(note_dict["resolved_as"] == "false_positive")
    )


def get_real_notes() -> List[HistoricalIncident]:
    """Return authentic analyst notes for testing.

    Returns:
        List of 4 real analyst notes with authentic characteristics
    """
    return [_dict_to_historical_incident(note) for note in REAL_ANALYST_NOTES]


def get_poisoned_notes() -> List[HistoricalIncident]:
    """Return fabricated notes for adversarial testing.

    Returns:
        List of 18 poisoned notes with fabrication signatures
    """
    return [_dict_to_historical_incident(note) for note in POISONED_NOTES]


def get_mixed_notes(real_count: int = 2, poisoned_count: int = 10) -> List[HistoricalIncident]:
    """Return a mix of real and poisoned notes.

    Args:
        real_count: Number of real notes to include
        poisoned_count: Number of poisoned notes to include

    Returns:
        Mixed list of notes
    """
    real = [_dict_to_historical_incident(note) for note in REAL_ANALYST_NOTES[:real_count]]
    poisoned = [_dict_to_historical_incident(note) for note in POISONED_NOTES[:poisoned_count]]
    return real + poisoned

