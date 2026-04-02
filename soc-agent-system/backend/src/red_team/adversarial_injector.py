"""Adversarial Injector - Simulates adversarial manipulation attacks.

Phase 1: Context Agent attack vector simulation.
Phase 2: Historical Agent attack vector simulation.
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta

from models import ThreatSignal, ThreatType

logger = logging.getLogger(__name__)


class AdversarialInjector:
    """Inject adversarial attack scenarios for testing detection capabilities.

    Phase 1: Context Agent attack simulation.
    Phase 2: Historical Agent attack simulation.
    """
    
    # Attack tool User-Agents for crafting malicious signals
    ATTACK_TOOL_USER_AGENTS = [
        "sqlmap/1.5.12",
        "Nikto/2.1.6",
        "Nmap Scripting Engine",
        "Burp Suite Professional v2.1",
        "Metasploit Framework v6.0",
        "w3af/1.6.54",
        "OWASP ZAP/2.11.0"
    ]
    
    # Benign-looking User-Agents to mask attacks
    BENIGN_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0"
    ]
    
    # Private IP ranges for geo-IP mismatch scenarios
    PRIVATE_IPS = [
        "10.0.1.50",
        "192.168.1.100",
        "172.16.0.10"
    ]
    
    # Public IPs for legitimate scenarios
    PUBLIC_IPS = [
        "203.0.113.50",
        "198.51.100.25",
        "8.8.8.8"
    ]
    
    # Public geo-locations
    PUBLIC_GEOLOCATIONS = [
        "San Francisco, CA",
        "New York, NY",
        "London, UK",
        "Tokyo, Japan",
        "Sydney, Australia"
    ]
    
    def __init__(self):
        """Initialize the adversarial injector."""
        pass
    
    def inject_context_contradiction_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.DEVICE_COMPROMISE
    ) -> ThreatSignal:
        """Inject a Context Agent contradiction attack.
        
        Scenario: Compromised customer device sends signal with:
        - Benign-looking metadata (trusted IP, normal UA, low volume)
        - Malicious payload that Priority Agent will detect
        
        This tests if the detector catches the contradiction between:
        - Context Agent: "benign, trusted source"
        - Priority Agent: "CRITICAL attack detected"
        
        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            
        Returns:
            ThreatSignal with contradictory indicators
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                # BENIGN metadata (Context will say "trusted")
                "source_ip": "203.0.113.50",  # Public IP, no geo mismatch
                "user_agent": self.BENIGN_USER_AGENTS[0],
                "request_count": 10,  # Low volume
                "geo_location": "",  # No geo to avoid mismatch
                
                # MALICIOUS payload (Priority will detect)
                "compromise_indicators": [
                    "sql_injection_detected",
                    "unauthorized_admin_access",
                    "data_exfiltration_attempt"
                ],
                "attack_signature": "MITRE T1190 - Exploit Public-Facing Application",
                "severity_score": 0.95
            }
        )
    
    def inject_geo_ip_mismatch_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC
    ) -> ThreatSignal:
        """Inject a geo-IP mismatch attack.
        
        Scenario: Signal claims to be from public location but uses private IP.
        This is impossible and indicates metadata manipulation.
        
        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            
        Returns:
            ThreatSignal with geo-IP mismatch
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PRIVATE_IPS[0],  # Private IP
                "geo_location": self.PUBLIC_GEOLOCATIONS[0],  # Public geo
                "user_agent": self.BENIGN_USER_AGENTS[1],
                "request_count": 50
            }
        )
    
    def inject_attack_tool_ua_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC,
        attack_tool_index: int = 0
    ) -> ThreatSignal:
        """Inject an attack tool User-Agent attack.
        
        Scenario: Signal uses known attack tool User-Agent.
        This indicates automated attack tooling.
        
        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            attack_tool_index: Index into ATTACK_TOOL_USER_AGENTS list
            
        Returns:
            ThreatSignal with attack tool User-Agent
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[0],
                "user_agent": self.ATTACK_TOOL_USER_AGENTS[attack_tool_index],
                "request_count": 100,
                "geo_location": ""
            }
        )

    def inject_high_volume_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.RATE_LIMIT_BREACH,
        request_count: int = 5000
    ) -> ThreatSignal:
        """Inject a high request volume attack.

        Scenario: Signal shows suspiciously high request volume.
        This is anomalous for "normal" traffic.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            request_count: Number of requests (default: 5000)

        Returns:
            ThreatSignal with high request volume
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[1],
                "user_agent": self.BENIGN_USER_AGENTS[2],
                "request_count": request_count,
                "geo_location": ""
            }
        )

    def inject_multi_anomaly_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.DEVICE_COMPROMISE
    ) -> ThreatSignal:
        """Inject a multi-anomaly attack.

        Scenario: Signal has multiple anomalies:
        - Geo-IP mismatch
        - Attack tool User-Agent
        - High request volume

        This should result in high risk score.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            ThreatSignal with multiple anomalies
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PRIVATE_IPS[1],  # Private IP
                "geo_location": self.PUBLIC_GEOLOCATIONS[1],  # Public geo
                "user_agent": self.ATTACK_TOOL_USER_AGENTS[1],  # Attack tool
                "request_count": 3000  # High volume
            }
        )

    def inject_combined_contradiction_and_anomaly_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.DEVICE_COMPROMISE
    ) -> ThreatSignal:
        """Inject a combined contradiction + anomaly attack.

        Scenario: Signal has multiple anomalies:
        - Geo-IP mismatch (private IP + public location)
        - Attack tool User-Agent (sqlmap)
        - Context-Priority contradiction (benign metadata + malicious payload)

        This should result in high risk score.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            ThreatSignal with both contradiction and multiple anomalies
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                # ANOMALY 1: Geo-IP mismatch
                "source_ip": self.PRIVATE_IPS[0],  # Private IP
                "geo_location": self.PUBLIC_GEOLOCATIONS[0],  # Public geo (mismatch!)
                "request_count": 15,

                # ANOMALY 2: Attack tool User-Agent
                "user_agent": self.ATTACK_TOOL_USER_AGENTS[0],  # sqlmap

                # MALICIOUS payload (Priority will detect - creates contradiction)
                "compromise_indicators": [
                    "critical_vulnerability_exploit",
                    "privilege_escalation",
                    "lateral_movement"
                ],
                "attack_signature": "MITRE T1068 - Exploitation for Privilege Escalation",
                "severity_score": 0.98
            }
        )

    def inject_clean_signal(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC
    ) -> ThreatSignal:
        """Inject a clean signal with no anomalies or contradictions.

        This is used for testing that the detector doesn't produce false positives.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            ThreatSignal with no adversarial indicators
        """
        return ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[0],  # Public IP
                "user_agent": self.BENIGN_USER_AGENTS[0],  # Benign UA
                "request_count": 25,  # Normal volume
                "geo_location": ""  # No geo to avoid mismatch
            }
        )

    # ========================================================================
    # PHASE 2: Historical Agent Attack Scenarios
    # ========================================================================

    def inject_historical_high_fp_rate_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC,
        fp_rate: float = 0.90
    ) -> Dict[str, Any]:
        """Inject a Historical Agent high FP rate attack.

        Scenario: Historical data shows suspiciously high false positive rate.
        This suggests the historical database has been poisoned to mark
        real attacks as false positives.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            fp_rate: False positive rate (default: 0.90 = 90%)

        Returns:
            Dict with signal and poisoned historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[0],
                "user_agent": self.BENIGN_USER_AGENTS[0],
                "request_count": 50
            }
        )

        # Poisoned historical data
        total_incidents = 30
        fp_count = int(total_incidents * fp_rate)

        historical_data = {
            "similar_incidents": total_incidents,
            "false_positive_count": fp_count,
            "false_positive_rate": fp_rate,
            "pattern": "Suspiciously high FP rate suggests data poisoning",
            "analysis_hint": f"Found {total_incidents} similar incidents with {fp_rate*100:.0f}% FP rate. Likely benign."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "high_fp_rate"
        }

    def inject_historical_high_incident_count_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC,
        incident_count: int = 50
    ) -> Dict[str, Any]:
        """Inject a Historical Agent high incident count attack.

        Scenario: Historical data shows suspiciously high number of similar incidents.
        This suggests automated poisoning of the historical database.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            incident_count: Number of similar incidents (default: 50)

        Returns:
            Dict with signal and poisoned historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[1],
                "user_agent": self.BENIGN_USER_AGENTS[1],
                "request_count": 75
            }
        )

        historical_data = {
            "similar_incidents": incident_count,
            "false_positive_count": int(incident_count * 0.7),
            "false_positive_rate": 0.7,
            "pattern": "Suspiciously high incident count",
            "analysis_hint": f"Found {incident_count} similar incidents. Pattern suggests benign activity."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "high_incident_count"
        }

    def inject_historical_temporal_clustering_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC,
        cluster_count: int = 15,
        time_window_hours: int = 1
    ) -> Dict[str, Any]:
        """Inject a Historical Agent temporal clustering attack.

        Scenario: Historical data shows many similar incidents in short time window.
        This suggests coordinated automated poisoning attack.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate
            cluster_count: Number of incidents in cluster (default: 15)
            time_window_hours: Time window in hours (default: 1)

        Returns:
            Dict with signal and poisoned historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[2],
                "user_agent": self.BENIGN_USER_AGENTS[2],
                "request_count": 100
            }
        )

        # Generate timestamps for clustered incidents
        now = datetime.now()
        timestamps = [
            (now - timedelta(minutes=i*4)).isoformat()
            for i in range(cluster_count)
        ]

        historical_data = {
            "similar_incidents": cluster_count,
            "false_positive_count": int(cluster_count * 0.8),
            "false_positive_rate": 0.8,
            "temporal_clustering": True,
            "cluster_timestamps": timestamps,
            "time_window_hours": time_window_hours,
            "pattern": f"{cluster_count} incidents in {time_window_hours} hour(s) - temporal clustering detected",
            "analysis_hint": f"Found {cluster_count} similar incidents in past {time_window_hours} hour(s). Likely false positive pattern."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "temporal_clustering"
        }

    def inject_historical_note_poisoning_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.ANOMALY_DETECTION
    ) -> Dict[str, Any]:
        """Inject a Historical Note Poisoning attack.

        Scenario: Attacker has poisoned the historical incident database with
        fabricated resolution notes over 18 days. All notes claim "false positive"
        with identical structure, generic team references, and no specific details.

        This attack is designed to demonstrate LLM-based semantic reasoning:
        - Rule-based systems CANNOT detect fabricated free-text notes
        - LLMs CAN detect linguistic patterns, domain inconsistencies, and plausibility

        The attack signal itself is clean (no metadata anomalies), but the
        historical context contains 18 fabricated notes that an LLM can identify
        as suspicious.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate (default: ANOMALY_DETECTION)

        Returns:
            Dict with:
                - signal: Clean ThreatSignal (no metadata anomalies)
                - historical_context: Dict with poisoned resolution notes
                - attack_type: "historical_note_poisoning"
        """
        from adversarial_mock_data.historical_notes import get_poisoned_notes

        # Clean signal - no structured field anomalies
        # This forces the detector to rely on semantic analysis of notes
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": "198.51.100.45",  # Public IP (no geo mismatch)
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",  # Benign UA
                "request_count": 12,  # Normal volume
                "payload": "SELECT * FROM users WHERE id=1 OR 1=1--"  # SQL injection payload
            }
        )

        # Poisoned historical context with fabricated notes
        poisoned_notes = get_poisoned_notes()

        historical_context = {
            "similar_incidents": poisoned_notes,
            "historical_fp_rate": 1.0,  # 18/18 = 100% false positive rate
            "incident_count": len(poisoned_notes),
            "pattern": "All similar SQL injection incidents marked as false positive",
            "analysis_hint": f"Found {len(poisoned_notes)} similar incidents, all resolved as false positive. Likely benign."
        }

        return {
            "signal": signal,
            "historical_context": historical_context,
            "attack_type": "historical_note_poisoning"
        }

    def inject_historical_multi_anomaly_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC
    ) -> Dict[str, Any]:
        """Inject a Historical Agent multi-anomaly attack.

        Scenario: Historical data has multiple anomalies:
        - High FP rate (90%)
        - High incident count (40)
        - Temporal clustering (12 incidents in 6 hours)

        This should result in high risk score.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            Dict with signal and poisoned historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[0],
                "user_agent": self.BENIGN_USER_AGENTS[0],
                "request_count": 60
            }
        )

        # Generate timestamps for clustered incidents
        now = datetime.now()
        cluster_count = 12
        timestamps = [
            (now - timedelta(minutes=i*30)).isoformat()
            for i in range(cluster_count)
        ]

        historical_data = {
            "similar_incidents": 40,
            "false_positive_count": 36,  # 90% FP rate
            "false_positive_rate": 0.90,
            "temporal_clustering": True,
            "cluster_timestamps": timestamps,
            "time_window_hours": 6,
            "pattern": "Multiple anomalies: high FP rate, high incident count, temporal clustering",
            "analysis_hint": "Found 40 similar incidents with 90% FP rate. 12 incidents in past 6 hours."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "multi_anomaly"
        }

    def inject_historical_priority_contradiction_attack(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.DEVICE_COMPROMISE
    ) -> Dict[str, Any]:
        """Inject a Historical-Priority contradiction attack.

        Scenario: Historical Agent says "likely benign/FP" but Priority Agent
        detects a CRITICAL attack. This contradiction suggests data poisoning.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            Dict with signal and poisoned historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[1],
                "user_agent": self.BENIGN_USER_AGENTS[1],
                "request_count": 30,

                # MALICIOUS payload (Priority will detect CRITICAL)
                "compromise_indicators": [
                    "ransomware_detected",
                    "data_encryption_in_progress",
                    "command_and_control_communication"
                ],
                "attack_signature": "MITRE T1486 - Data Encrypted for Impact",
                "severity_score": 0.98
            }
        )

        # Poisoned historical data suggesting benign
        historical_data = {
            "similar_incidents": 25,
            "false_positive_count": 24,  # 96% FP rate
            "false_positive_rate": 0.96,
            "pattern": "Historical data poisoned to suggest benign",
            "analysis_hint": "Found 25 similar incidents. All false positives. Likely benign."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "historical_priority_contradiction"
        }

    def inject_historical_clean_data(
        self,
        customer_name: str = "TestCorp",
        threat_type: ThreatType = ThreatType.BOT_TRAFFIC
    ) -> Dict[str, Any]:
        """Inject clean Historical data with no poisoning.

        This is used for testing that the detector doesn't produce false positives.

        Args:
            customer_name: Customer name for the signal
            threat_type: Type of threat to simulate

        Returns:
            Dict with signal and clean historical data
        """
        signal = ThreatSignal(
            customer_name=customer_name,
            threat_type=threat_type,
            metadata={
                "source_ip": self.PUBLIC_IPS[0],
                "user_agent": self.BENIGN_USER_AGENTS[0],
                "request_count": 20
            }
        )

        # Clean historical data
        historical_data = {
            "similar_incidents": 3,
            "false_positive_count": 1,  # 33% FP rate - normal
            "false_positive_rate": 0.33,
            "pattern": "Normal historical pattern",
            "analysis_hint": "Found 3 similar incidents. 2 confirmed attacks, 1 false positive. Normal pattern."
        }

        return {
            "signal": signal,
            "historical_data": historical_data,
            "attack_type": "clean"
        }

