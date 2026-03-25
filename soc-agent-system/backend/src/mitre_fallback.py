"""Fallback MITRE ATT&CK mappings for threat types.

This module provides deterministic MITRE technique mappings when:
1. Wazuh doesn't provide MITRE hints
2. LLM doesn't generate MITRE tags
3. As a baseline for known threat patterns

All fallback tags have confidence=0.6 and source="fallback".
"""
import logging
from typing import List

from models import MitreTag, ThreatType

logger = logging.getLogger(__name__)


# Deterministic mapping: ThreatType -> List of MITRE techniques
# Focus on Mobile ATT&CK for Android threats (TA0027-TA0037)
THREAT_TYPE_TO_MITRE = {
    ThreatType.DEVICE_COMPROMISE: [
        {
            "technique_id": "T1475",
            "technique_name": "Deliver Malicious App via Authorized App Store",
            "tactic": "Initial Access",
            "tactic_id": "TA0027",
        },
        {
            "technique_id": "T1533",
            "technique_name": "Data from Local System",
            "tactic": "Collection",
            "tactic_id": "TA0035",
        },
        {
            "technique_id": "T1418",
            "technique_name": "Application Discovery",
            "tactic": "Discovery",
            "tactic_id": "TA0032",
        },
    ],
    ThreatType.BOT_TRAFFIC: [
        {
            "technique_id": "T1659",
            "technique_name": "Content Injection",
            "tactic": "Impact",
            "tactic_id": "TA0040",
        },
        {
            "technique_id": "T1498",
            "technique_name": "Network Denial of Service",
            "tactic": "Impact",
            "tactic_id": "TA0040",
        },
    ],
    ThreatType.PROXY_NETWORK: [
        {
            "technique_id": "T1090",
            "technique_name": "Proxy",
            "tactic": "Command and Control",
            "tactic_id": "TA0011",
        },
        {
            "technique_id": "T1071",
            "technique_name": "Application Layer Protocol",
            "tactic": "Command and Control",
            "tactic_id": "TA0011",
        },
    ],
    ThreatType.ANOMALY_DETECTION: [
        {
            "technique_id": "T1078",
            "technique_name": "Valid Accounts",
            "tactic": "Defense Evasion",
            "tactic_id": "TA0005",
        },
        {
            "technique_id": "T1562",
            "technique_name": "Impair Defenses",
            "tactic": "Defense Evasion",
            "tactic_id": "TA0005",
        },
    ],
    ThreatType.RATE_LIMIT_BREACH: [
        {
            "technique_id": "T1110",
            "technique_name": "Brute Force",
            "tactic": "Credential Access",
            "tactic_id": "TA0006",
        },
        {
            "technique_id": "T1499",
            "technique_name": "Endpoint Denial of Service",
            "tactic": "Impact",
            "tactic_id": "TA0040",
        },
    ],
    ThreatType.GEO_ANOMALY: [
        {
            "technique_id": "T1078",
            "technique_name": "Valid Accounts",
            "tactic": "Initial Access",
            "tactic_id": "TA0001",
        },
        {
            "technique_id": "T1535",
            "technique_name": "Unused/Unsupported Cloud Regions",
            "tactic": "Defense Evasion",
            "tactic_id": "TA0005",
        },
    ],
}


def get_fallback_mitre_tags(threat_type: ThreatType) -> List[MitreTag]:
    """
    Get fallback MITRE tags for a given threat type.
    
    Returns deterministic MITRE techniques based on threat classification.
    All tags have confidence=0.6 and source="fallback".
    
    Args:
        threat_type: The type of threat to get MITRE tags for
        
    Returns:
        List of MitreTag objects, or empty list if no mapping exists
    """
    try:
        # Get mapping for this threat type
        technique_dicts = THREAT_TYPE_TO_MITRE.get(threat_type, [])
        
        if not technique_dicts:
            logger.debug(f"No fallback MITRE mapping for threat type: {threat_type}")
            return []
        
        # Convert to MitreTag objects
        tags = []
        for tech_dict in technique_dicts:
            tag = MitreTag(
                technique_id=tech_dict["technique_id"],
                technique_name=tech_dict["technique_name"],
                tactic=tech_dict["tactic"],
                tactic_id=tech_dict["tactic_id"],
                confidence=0.6,
                source="fallback"
            )
            tags.append(tag)
        
        logger.info(f"Retrieved {len(tags)} fallback MITRE tags for {threat_type}")
        return tags
        
    except Exception as e:
        logger.warning(f"Error getting fallback MITRE tags for {threat_type}: {e}")
        return []

