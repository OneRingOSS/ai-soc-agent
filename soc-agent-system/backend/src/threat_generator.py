"""Threat signal generator - simulates inference engine output."""
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from models import ThreatSignal, ThreatType


class ThreatGenerator:
    """Generates realistic threat signals for demo purposes."""
    
    CUSTOMERS = [
        "Acme Corp", "TechStart Inc", "Global Finance", "HealthCare Plus",
        "RetailMax", "CryptoExchange Pro", "EduPlatform", "SocialNet Co"
    ]
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        "Python-requests/2.31.0",
        "curl/7.68.0",
        "Suspicious-Bot/1.0",
        "Mozilla/5.0 (Linux; Android 10) Mobile Chrome/120.0.0.0"
    ]
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize threat generator with optional seed for testing."""
        if seed is not None:
            random.seed(seed)
        
        self.threat_generators = {
            ThreatType.BOT_TRAFFIC: self.generate_bot_traffic,
            ThreatType.PROXY_NETWORK: self.generate_proxy_network,
            ThreatType.DEVICE_COMPROMISE: self.generate_device_compromise,
            ThreatType.ANOMALY_DETECTION: self.generate_anomaly_detection,
            ThreatType.RATE_LIMIT_BREACH: self.generate_rate_limit_breach,
            ThreatType.GEO_ANOMALY: self.generate_geo_anomaly,
        }
    
    def generate_random_threat(self) -> ThreatSignal:
        """Generate a random threat signal."""
        threat_type = random.choice(list(ThreatType))
        return self.generate_threat_by_type(threat_type)
    
    def generate_threat_by_type(self, threat_type: ThreatType) -> ThreatSignal:
        """Generate threat signal of specific type."""
        generator_func = self.threat_generators[threat_type]
        return generator_func()
    
    def generate_scenario_threat(self, scenario: str) -> ThreatSignal:
        """Generate threat signal for a specific scenario."""
        scenarios = {
            "crypto_surge": self._scenario_crypto_surge,
            "bot_attack": self._scenario_bot_attack,
            "geo_impossible": self._scenario_geo_impossible,
            "critical_threat": self._scenario_critical_threat,
        }

        if scenario in scenarios:
            return scenarios[scenario]()
        else:
            # Fallback to random threat
            return self.generate_random_threat()
    
    def _scenario_crypto_surge(self) -> ThreatSignal:
        """Crypto exchange experiencing surge during market volatility."""
        return ThreatSignal(
            threat_type=ThreatType.RATE_LIMIT_BREACH,
            customer_name="CryptoExchange Pro",
            metadata={
                "source_ip": self._random_ip(),
                "user_agent": random.choice(self.USER_AGENTS),
                "configured_limit": 150,
                "actual_rate": 850,
                "breach_duration_seconds": 300,
                "endpoint": "/api/trade",
                "user_id": f"user_{random.randint(1000, 9999)}",
                "breach_factor": 5.7,
                "context": "Bitcoin market volatility"
            }
        )
    
    def _scenario_bot_attack(self) -> ThreatSignal:
        """Retail site under bot attack."""
        return ThreatSignal(
            threat_type=ThreatType.BOT_TRAFFIC,
            customer_name="RetailMax",
            metadata={
                "source_ip": self._random_ip(),
                "user_agent": "Suspicious-Bot/1.0",
                "request_count": 3500,
                "requests_per_second": 150,
                "endpoints_targeted": ["/api/checkout", "/api/inventory"],
                "detection_confidence": 0.97,
                "behavioral_patterns": ["uniform_timing", "automated_retry_logic"],
                "context": "Flash sale event"
            }
        )
    
    def _scenario_geo_impossible(self) -> ThreatSignal:
        """Impossible travel detected."""
        return ThreatSignal(
            threat_type=ThreatType.GEO_ANOMALY,
            customer_name="Global Finance",
            metadata={
                "user_id": f"user_{random.randint(1000, 9999)}",
                "location_1": {
                    "city": "New York, US",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat()
                },
                "location_2": {
                    "city": "Tokyo, Japan",
                    "latitude": 35.6762,
                    "longitude": 139.6503,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "time_delta_minutes": 10,
                "distance_km": 10850,
                "impossible_travel_detected": True,
                "confidence": 0.99
            }
        )

    def _scenario_critical_threat(self) -> ThreatSignal:
        """Critical multi-vector attack requiring immediate review."""
        return ThreatSignal(
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name="HealthCare Plus",
            metadata={
                "device_id": f"device_{random.randint(100000, 999999)}",
                "source_ip": self._random_ip(),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "compromise_indicators": [
                    "unauthorized_admin_access",
                    "data_exfiltration_detected",
                    "malware_signature_match",
                    "lateral_movement_attempt",
                    "privilege_escalation"
                ],
                "severity_score": 9.8,
                "affected_systems": ["patient_records_db", "billing_system", "admin_portal"],
                "data_accessed": ["PHI", "PII", "financial_records"],
                "exfiltration_volume_mb": 2500,
                "attack_duration_minutes": 45,
                "persistence_mechanisms": ["scheduled_task", "registry_modification"],
                "c2_communication_detected": True,
                "c2_server": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "requires_immediate_action": True,
                "compliance_impact": "HIPAA violation risk",
                "context": "Active APT campaign targeting healthcare sector"
            }
        )

    def generate_bot_traffic(self) -> ThreatSignal:
        """Generate bot traffic threat signal."""
        return ThreatSignal(
            threat_type=ThreatType.BOT_TRAFFIC,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "source_ip": self._random_ip(),
                "user_agent": "Suspicious-Bot/1.0",
                "request_count": random.randint(500, 5000),
                "requests_per_second": random.randint(50, 200),
                "endpoints_targeted": ["/api/login", "/api/checkout", "/api/account"],
                "detection_confidence": round(random.uniform(0.85, 0.99), 2),
                "behavioral_patterns": [
                    "uniform_timing",
                    "automated_retry_logic",
                    "suspicious_user_agent"
                ]
            }
        )

    def generate_proxy_network(self) -> ThreatSignal:
        """Generate proxy network threat signal."""
        proxy_ips = [self._random_ip() for _ in range(random.randint(5, 20))]
        return ThreatSignal(
            threat_type=ThreatType.PROXY_NETWORK,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "proxy_ips": proxy_ips,
                "proxy_count": len(proxy_ips),
                "user_agent": random.choice(self.USER_AGENTS),
                "shared_fingerprint": f"fp_{random.randint(10000, 99999)}",
                "geographic_spread": ["US", "CA", "UK", "DE", "FR"],
                "detection_method": "device_fingerprint_correlation",
                "confidence_score": round(random.uniform(0.75, 0.95), 2)
            }
        )

    def generate_device_compromise(self) -> ThreatSignal:
        """Generate device compromise threat signal."""
        return ThreatSignal(
            threat_type=ThreatType.DEVICE_COMPROMISE,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "device_id": f"device_{random.randint(100000, 999999)}",
                "source_ip": self._random_ip(),
                "user_agent": random.choice(self.USER_AGENTS),
                "compromise_indicators": [
                    "rooted_device",
                    "debugger_detected",
                    "tampered_sdk"
                ],
                "risk_score": round(random.uniform(0.7, 0.95), 2),
                "first_seen": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat(),
                "attempt_count": random.randint(10, 100)
            }
        )

    def generate_anomaly_detection(self) -> ThreatSignal:
        """Generate anomaly detection threat signal."""
        return ThreatSignal(
            threat_type=ThreatType.ANOMALY_DETECTION,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "user_id": f"user_{random.randint(1000, 9999)}",
                "source_ip": self._random_ip(),
                "anomaly_score": round(random.uniform(0.8, 0.99), 2),
                "deviations": [
                    "unusual_access_time",
                    "atypical_location",
                    "abnormal_request_pattern"
                ],
                "baseline_comparison": {
                    "typical_requests_per_hour": 50,
                    "current_requests_per_hour": 500,
                    "deviation_percentage": 900
                },
                "ml_model_version": "v2.3.1"
            }
        )

    def generate_rate_limit_breach(self) -> ThreatSignal:
        """Generate rate limit breach threat signal."""
        return ThreatSignal(
            threat_type=ThreatType.RATE_LIMIT_BREACH,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "source_ip": self._random_ip(),
                "user_agent": random.choice(self.USER_AGENTS),
                "configured_limit": 100,
                "actual_rate": random.randint(300, 1000),
                "breach_duration_seconds": random.randint(30, 600),
                "endpoint": random.choice(["/api/search", "/api/data", "/api/login"]),
                "user_id": f"user_{random.randint(1000, 9999)}",
                "breach_factor": round(random.uniform(3.0, 10.0), 1)
            }
        )

    def generate_geo_anomaly(self) -> ThreatSignal:
        """Generate geographic anomaly threat signal."""
        locations = [
            ("New York, US", 40.7128, -74.0060),
            ("London, UK", 51.5074, -0.1278),
            ("Tokyo, Japan", 35.6762, 139.6503),
            ("Sydney, Australia", -33.8688, 151.2093),
            ("Moscow, Russia", 55.7558, 37.6173)
        ]
        loc1, loc2 = random.sample(locations, 2)

        return ThreatSignal(
            threat_type=ThreatType.GEO_ANOMALY,
            customer_name=random.choice(self.CUSTOMERS),
            metadata={
                "user_id": f"user_{random.randint(1000, 9999)}",
                "location_1": {
                    "city": loc1[0],
                    "latitude": loc1[1],
                    "longitude": loc1[2],
                    "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat()
                },
                "location_2": {
                    "city": loc2[0],
                    "latitude": loc2[1],
                    "longitude": loc2[2],
                    "timestamp": datetime.utcnow().isoformat()
                },
                "time_delta_minutes": 5,
                "distance_km": random.randint(5000, 15000),
                "impossible_travel_detected": True,
                "confidence": round(random.uniform(0.85, 0.99), 2)
            }
        )

    def _random_ip(self) -> str:
        """Generate random IP address."""
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}." \
               f"{random.randint(0, 255)}.{random.randint(1, 255)}"


# Singleton instance
threat_generator = ThreatGenerator()

