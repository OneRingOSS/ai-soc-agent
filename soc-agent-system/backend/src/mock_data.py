"""Mock data stores for SOC Agent System."""
from datetime import datetime, timedelta
from typing import List, Dict
import random
from models import (
    HistoricalIncident, CustomerConfig, InfraEvent, 
    NewsItem, ThreatType
)


class MockDataStore:
    """Centralized mock data store for all agents."""
    
    def __init__(self):
        """Initialize mock data stores."""
        self.historical_incidents = self._generate_historical_incidents()
        self.customer_configs = self._generate_customer_configs()
        self.infra_events = self._generate_infra_events()
        self.news_items = self._generate_news_items()
    
    def _generate_historical_incidents(self) -> List[HistoricalIncident]:
        """Generate mock historical incidents."""
        incidents = []
        customers = [
            "Acme Corp", "TechStart Inc", "Global Finance", 
            "HealthCare Plus", "RetailMax", "CryptoExchange Pro"
        ]
        resolutions = [
            "Confirmed attack - blocked IP ranges",
            "False positive - product launch traffic",
            "Configuration updated - rate limits adjusted",
            "User behavior confirmed legitimate",
            "Credential stuffing attack mitigated",
            "Bot traffic blocked at edge"
        ]
        
        for i in range(30):
            incidents.append(HistoricalIncident(
                id=f"incident_{i+1}",
                customer_name=random.choice(customers),
                threat_type=random.choice(list(ThreatType)),
                timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                resolution=random.choice(resolutions),
                was_false_positive=random.choice([True, False, False])
            ))
        
        return incidents
    
    def _generate_customer_configs(self) -> Dict[str, CustomerConfig]:
        """Generate mock customer configurations."""
        configs = {}
        customers = [
            ("Acme Corp", 100, ["RU", "CN", "KP"], "medium"),
            ("TechStart Inc", 200, ["KP"], "low"),
            ("Global Finance", 50, ["RU", "CN", "KP", "IR"], "high"),
            ("HealthCare Plus", 75, ["KP"], "medium"),
            ("RetailMax", 500, [], "low"),
            ("CryptoExchange Pro", 150, ["KP", "IR"], "high"),
            ("EduPlatform", 300, [], "low"),
            ("SocialNet Co", 250, ["KP"], "medium"),
        ]
        
        for name, rate_limit, geo, sensitivity in customers:
            configs[name] = CustomerConfig(
                customer_name=name,
                rate_limit_per_minute=rate_limit,
                geo_restrictions=geo,
                bot_detection_sensitivity=sensitivity
            )
        
        return configs
    
    def _generate_infra_events(self) -> List[InfraEvent]:
        """Generate mock infrastructure events."""
        events = []
        event_types = [
            ("deployment", "Production deployment of API v2.3.1", ["api-gateway", "auth-service"]),
            ("scaling", "Auto-scaling triggered for high traffic", ["api-gateway"]),
            ("outage", "Brief network connectivity issue in us-east-1", ["all-services"]),
            ("deployment", "Security patch applied to edge servers", ["edge-proxy"]),
            ("scaling", "Database read replicas scaled up", ["db-cluster"]),
            ("maintenance", "Scheduled maintenance on logging infrastructure", ["logging"]),
        ]
        
        for i, (event_type, desc, services) in enumerate(event_types):
            events.append(InfraEvent(
                id=f"infra_{i+1}",
                event_type=event_type,
                timestamp=datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                description=desc,
                affected_services=services
            ))
        
        return events
    
    def _generate_news_items(self) -> List[NewsItem]:
        """Generate mock news items."""
        news = [
            ("Bitcoin drops 8% amid market uncertainty", 
             "Cryptocurrency markets experience significant volatility as Bitcoin falls sharply.",
             "CryptoNews"),
            ("Major retailer announces flash sale event",
             "RetailMax competitor launches surprise 24-hour sale, expecting traffic surge.",
             "RetailWeekly"),
            ("New credential stuffing toolkit released on dark web",
             "Security researchers identify new automated attack toolkit targeting financial services.",
             "SecurityWeek"),
            ("Healthcare data breach reported at competitor",
             "Major healthcare provider reports breach affecting millions of records.",
             "HealthIT News"),
            ("Social media platform experiences global outage",
             "Competing social network down for 2 hours, users migrating to alternatives.",
             "TechCrunch"),
        ]
        
        items = []
        for i, (title, summary, source) in enumerate(news):
            items.append(NewsItem(
                id=f"news_{i+1}",
                title=title,
                summary=summary,
                published_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24)),
                source=source
            ))
        
        return items
    
    def get_similar_incidents(
        self,
        threat_type: ThreatType,
        customer_name: str
    ) -> List[HistoricalIncident]:
        """Get similar historical incidents."""
        return [
            inc for inc in self.historical_incidents
            if inc.threat_type == threat_type or inc.customer_name == customer_name
        ][:5]

    def get_customer_config(self, customer_name: str) -> CustomerConfig:
        """Get customer configuration."""
        return self.customer_configs.get(
            customer_name,
            CustomerConfig(
                customer_name=customer_name,
                rate_limit_per_minute=100,
                geo_restrictions=[],
                bot_detection_sensitivity="medium"
            )
        )

    def get_recent_infra_events(self, minutes: int = 60) -> List[InfraEvent]:
        """Get recent infrastructure events."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [e for e in self.infra_events if e.timestamp > cutoff]

    def get_relevant_news(self, keywords: List[str]) -> List[NewsItem]:
        """Get relevant news items based on keywords."""
        relevant = []
        for item in self.news_items:
            for keyword in keywords:
                if keyword.lower() in item.title.lower() or keyword.lower() in item.summary.lower():
                    relevant.append(item)
                    break
        return relevant[:3]


# Singleton instance
mock_data_store = MockDataStore()

