"""
Locust load testing suite for SOC Agent System.

Three user classes simulate different traffic patterns:
- SteadyStateUser: Normal SOC operations (weight=5)
- BurstAttackUser: Attack spike simulation (weight=2)
- MixedRealisticUser: Weighted realistic distribution (weight=3)

Usage:
    locust -f locustfile.py --host=http://localhost:8000
"""

import random

from locust import HttpUser, between, task

# Valid threat types (matches ThreatType enum in backend)
ALL_THREAT_TYPES = [
    "bot_traffic",
    "proxy_network",
    "device_compromise",
    "anomaly_detection",
    "rate_limit_breach",
    "geo_anomaly",
]

# Valid scenario names (matches threat_generator scenarios)
ALL_SCENARIOS = [
    "crypto_surge",
    "bot_attack",
    "geo_impossible",
    "critical_threat",
]

# Attack-oriented threat types for burst simulation
ATTACK_THREAT_TYPES = [
    "bot_traffic",
    "rate_limit_breach",
]

# Weighted distribution for realistic traffic
# 30% bot_traffic, 20% rate_limit_breach, 15% anomaly_detection,
# 15% proxy_network, 10% geo_anomaly, 10% device_compromise
REALISTIC_THREAT_WEIGHTS = [
    ("bot_traffic", 30),
    ("rate_limit_breach", 20),
    ("anomaly_detection", 15),
    ("proxy_network", 15),
    ("geo_anomaly", 10),
    ("device_compromise", 10),
]

REALISTIC_THREAT_POPULATION = []
for _threat_type, _weight in REALISTIC_THREAT_WEIGHTS:
    REALISTIC_THREAT_POPULATION.extend([_threat_type] * _weight)


class SteadyStateUser(HttpUser):
    """Simulates normal SOC operations with uniform random threat types.

    Weight: 5 (most common user type)
    Wait: 2-5 seconds between requests
    Behavior: Triggers random threat types from all 6 valid types
    """

    weight = 5
    wait_time = between(2, 5)

    @task(5)
    def trigger_random_threat(self):
        """Trigger a random threat type."""
        chosen_type = random.choice(ALL_THREAT_TYPES)
        self.client.post(
            "/api/threats/trigger",
            json={"threat_type": chosen_type},
            name="/api/threats/trigger [steady]",
        )

    @task(2)
    def get_threats_list(self):
        """Check the threats list (read traffic)."""
        self.client.get("/api/threats", name="/api/threats [list]")

    @task(1)
    def health_check(self):
        """Check the health endpoint."""
        self.client.get("/", name="/ [health]")


class BurstAttackUser(HttpUser):
    """Simulates an attack spike with rapid-fire requests.

    Weight: 2 (less common, but high intensity)
    Wait: 0.1-0.5 seconds between requests (rapid fire)
    Behavior: Only bot_traffic and rate_limit_breach types
    """

    weight = 2
    wait_time = between(0.1, 0.5)

    @task(8)
    def trigger_attack_threat(self):
        """Trigger attack-oriented threat types rapidly."""
        chosen_type = random.choice(ATTACK_THREAT_TYPES)
        self.client.post(
            "/api/threats/trigger",
            json={"threat_type": chosen_type},
            name="/api/threats/trigger [burst]",
        )

    @task(1)
    def get_threats_list(self):
        """Check the threats list during attack."""
        self.client.get("/api/threats", name="/api/threats [list]")

    @task(1)
    def health_check(self):
        """Check health during attack."""
        self.client.get("/", name="/ [health]")


class MixedRealisticUser(HttpUser):
    """Simulates realistic SOC traffic with weighted threat distribution.

    Weight: 3 (moderate frequency)
    Wait: 1-3 seconds between requests
    Behavior: Weighted distribution across all threat types,
              occasionally uses predefined scenarios
    """

    weight = 3
    wait_time = between(1, 3)

    @task(6)
    def trigger_weighted_threat(self):
        """Trigger a threat type based on realistic weighted distribution."""
        chosen_type = random.choice(REALISTIC_THREAT_POPULATION)
        self.client.post(
            "/api/threats/trigger",
            json={"threat_type": chosen_type},
            name="/api/threats/trigger [mixed]",
        )

    @task(2)
    def trigger_scenario(self):
        """Trigger a predefined scenario."""
        chosen_scenario = random.choice(ALL_SCENARIOS)
        self.client.post(
            "/api/threats/trigger",
            json={"scenario": chosen_scenario},
            name="/api/threats/trigger [scenario]",
        )

    @task(1)
    def get_threats_list(self):
        """Check the threats list."""
        self.client.get("/api/threats", name="/api/threats [list]")

    @task(1)
    def health_check(self):
        """Check the health endpoint."""
        self.client.get("/", name="/ [health]")

