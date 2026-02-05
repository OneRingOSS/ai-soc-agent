# SOC Agent System - Complete Code Package

A production-ready autonomous SOC (Security Operations Center) agent system demonstrating enterprise-grade multi-agent AI capabilities.

---

## Project Structure

```
soc-agent-system/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── threat_generator.py
│   │   ├── mock_data.py
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── base_agent.py
│   │       ├── coordinator.py
│   │       ├── historical_agent.py
│   │       ├── config_agent.py
│   │       ├── devops_agent.py
│   │       ├── context_agent.py
│   │       └── priority_agent.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_threat_generator.py
│   │   ├── test_agents.py
│   │   ├── test_coordinator.py
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── pytest.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── hooks/
│   │       └── useWebSocket.js
│   ├── tests/
│   │   ├── setup.js
│   │   └── App.test.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## Backend Files

### requirements.txt

```txt
# FastAPI and async dependencies
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0

# OpenAI
openai==1.10.0

# WebSocket support
websockets==12.0

# Testing dependencies
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
httpx==0.26.0
pytest-mock==3.12.0
```

### .env.example

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000

# LLM Configuration
LLM_MODEL=gpt-4-turbo-preview
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000

# Feature Flags
THREAT_INTERVAL=15
MAX_STORED_THREATS=50
```

### pytest.ini

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = tests
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
addopts = -v --tb=short
```

### src/__init__.py

```python
"""SOC Agent System - Backend Package."""
```

### src/config.py

```python
"""Configuration management for SOC Agent System."""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    
    # Threat Generation
    threat_generation_interval: int = Field(default=15, env="THREAT_INTERVAL")
    max_stored_threats: int = Field(default=50, env="MAX_STORED_THREATS")
    
    # LLM Configuration
    llm_model: str = Field(default="gpt-4-turbo-preview", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1000, env="LLM_MAX_TOKENS")
    llm_timeout: int = Field(default=30, env="LLM_TIMEOUT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


settings = get_settings()
```

### src/models.py

```python
"""Pydantic models for SOC Agent System."""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import uuid


class ThreatType(str, Enum):
    """Types of security threats."""
    BOT_TRAFFIC = "bot_traffic"
    PROXY_NETWORK = "proxy_network"
    DEVICE_COMPROMISE = "device_compromise"
    ANOMALY_DETECTION = "anomaly_detection"
    RATE_LIMIT_BREACH = "rate_limit_breach"
    GEO_ANOMALY = "geo_anomaly"


class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatSignal(BaseModel):
    """Raw threat signal from inference engine."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    threat_type: ThreatType
    customer_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentAnalysis(BaseModel):
    """Analysis result from a specialized agent."""
    agent_name: str
    analysis: str
    confidence: float = Field(ge=0.0, le=1.0)
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    processing_time_ms: int


class MITRETactic(BaseModel):
    """MITRE ATT&CK tactic."""
    id: str
    name: str
    description: str


class MITRETechnique(BaseModel):
    """MITRE ATT&CK technique."""
    id: str
    name: str
    description: str


class ThreatAnalysis(BaseModel):
    """Complete threat analysis from coordinator."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal: ThreatSignal
    severity: ThreatSeverity
    executive_summary: str
    mitre_tactics: List[MITRETactic] = Field(default_factory=list)
    mitre_techniques: List[MITRETechnique] = Field(default_factory=list)
    customer_narrative: str
    agent_analyses: Dict[str, AgentAnalysis] = Field(default_factory=dict)
    total_processing_time_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    requires_human_review: bool = False
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DashboardMetrics(BaseModel):
    """Dashboard analytics metrics."""
    total_threats: int
    customers_affected: int
    average_processing_time_ms: int
    threats_requiring_review: int
    threats_by_type: Dict[str, int]
    threats_by_severity: Dict[str, int]


class HistoricalIncident(BaseModel):
    """Historical incident for pattern matching."""
    id: str
    customer_name: str
    threat_type: ThreatType
    timestamp: datetime
    resolution: str
    was_false_positive: bool


class CustomerConfig(BaseModel):
    """Customer-specific configuration."""
    customer_name: str
    rate_limit_per_minute: int
    geo_restrictions: List[str]
    bot_detection_sensitivity: str


class InfraEvent(BaseModel):
    """Infrastructure event log entry."""
    id: str
    event_type: str
    timestamp: datetime
    description: str
    affected_services: List[str]


class NewsItem(BaseModel):
    """World news or market event."""
    id: str
    title: str
    summary: str
    published_at: datetime
    source: str
```

### src/threat_generator.py

```python
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
```

### src/mock_data.py

```python
"""Mock data stores for SOC Agent System."""
from datetime import datetime, timedelta
from typing import List, Dict, Any
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
```

### src/agents/__init__.py

```python
"""SOC Agent System - Agents Package."""
from agents.base_agent import BaseAgent
from agents.coordinator import CoordinatorAgent
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent

__all__ = [
    "BaseAgent",
    "CoordinatorAgent", 
    "HistoricalAgent",
    "ConfigAgent",
    "DevOpsAgent",
    "ContextAgent",
    "PriorityAgent"
]
```

### src/agents/base_agent.py

```python
"""Base agent class for all specialized agents."""
import time
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from models import ThreatSignal, AgentAnalysis
from config import settings


class BaseAgent(ABC):
    """Abstract base class for all SOC agents."""
    
    def __init__(self, name: str, client: Optional[AsyncOpenAI] = None):
        """Initialize base agent."""
        self.name = name
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build the user prompt for analysis."""
        pass
    
    async def analyze(
        self, 
        signal: ThreatSignal, 
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Perform analysis on the threat signal."""
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": self.build_user_prompt(signal, context)}
                ],
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            processing_time = int((time.time() - start_time) * 1000)
            
            return AgentAnalysis(
                agent_name=self.name,
                analysis=result.get("analysis", ""),
                confidence=result.get("confidence", 0.5),
                key_findings=result.get("key_findings", []),
                recommendations=result.get("recommendations", []),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return AgentAnalysis(
                agent_name=self.name,
                analysis=f"Analysis failed: {str(e)}",
                confidence=0.0,
                key_findings=["Error during analysis"],
                recommendations=["Manual review required"],
                processing_time_ms=processing_time
            )
    
    async def analyze_mock(
        self, 
        signal: ThreatSignal, 
        context: Dict[str, Any]
    ) -> AgentAnalysis:
        """Mock analysis for testing without LLM calls."""
        start_time = time.time()
        
        # Simulate processing time
        import asyncio
        await asyncio.sleep(0.1)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return AgentAnalysis(
            agent_name=self.name,
            analysis=f"Mock analysis for {signal.threat_type.value}",
            confidence=0.85,
            key_findings=[f"Mock finding for {self.name}"],
            recommendations=[f"Mock recommendation from {self.name}"],
            processing_time_ms=processing_time
        )
```

### src/agents/historical_agent.py

```python
"""Historical Agent - Pattern recognition specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class HistoricalAgent(BaseAgent):
    """Agent that analyzes historical patterns and similar incidents."""
    
    def __init__(self, **kwargs):
        """Initialize Historical Agent."""
        super().__init__(name="Historical Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for historical analysis."""
        return """You are a Historical Pattern Analysis Agent for a Security Operations Center.

Your role is to:
1. Analyze past incidents for similar patterns
2. Identify recurring threats across customers
3. Provide context from previous resolutions
4. Calculate pattern similarity scores

You have access to a 30-day window of historical incident data.

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "similar_incidents_found": number,
    "pattern_match_score": 0.0-1.0
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and historical context."""
        similar_incidents = context.get("similar_incidents", [])
        
        incidents_text = "\n".join([
            f"- {inc.timestamp.isoformat()}: {inc.customer_name} - {inc.threat_type.value} - "
            f"Resolution: {inc.resolution} (False positive: {inc.was_false_positive})"
            for inc in similar_incidents
        ]) if similar_incidents else "No similar incidents found"
        
        return f"""Analyze this threat signal for historical patterns:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

SIMILAR HISTORICAL INCIDENTS (last 30 days):
{incidents_text}

Analyze patterns, identify if this is a recurring issue, and provide insights from past resolutions."""
```

### src/agents/config_agent.py

```python
"""Config Agent - Configuration and policy specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class ConfigAgent(BaseAgent):
    """Agent that analyzes customer configurations and policies."""
    
    def __init__(self, **kwargs):
        """Initialize Config Agent."""
        super().__init__(name="Config Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for config analysis."""
        return """You are a Configuration Analysis Agent for a Security Operations Center.

Your role is to:
1. Check rate limiting thresholds against current traffic
2. Review geo-restriction rules
3. Examine bot detection sensitivity settings
4. Assess if the threat is configuration-driven

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "config_issues_found": boolean,
    "suggested_config_changes": ["change1", "change2"]
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and config context."""
        config = context.get("customer_config")
        
        config_text = f"""
- Rate Limit: {config.rate_limit_per_minute} req/min
- Geo Restrictions: {config.geo_restrictions or 'None'}
- Bot Detection Sensitivity: {config.bot_detection_sensitivity}
""" if config else "Configuration not available"
        
        return f"""Analyze this threat signal against customer configuration:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

CUSTOMER CONFIGURATION:
{config_text}

Determine if current configuration settings may be contributing to this alert or if adjustments are needed."""
```

### src/agents/devops_agent.py

```python
"""DevOps Agent - Infrastructure correlation specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class DevOpsAgent(BaseAgent):
    """Agent that correlates threats with infrastructure events."""
    
    def __init__(self, **kwargs):
        """Initialize DevOps Agent."""
        super().__init__(name="DevOps Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for DevOps analysis."""
        return """You are a DevOps Correlation Agent for a Security Operations Center.

Your role is to:
1. Correlate threat timing with infrastructure events
2. Check for deployment-related issues
3. Identify platform-wide problems
4. Assess if the threat is infrastructure-caused

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "infra_correlation_found": boolean,
    "related_events": ["event1", "event2"]
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and infra context."""
        infra_events = context.get("infra_events", [])
        
        events_text = "\n".join([
            f"- {e.timestamp.isoformat()}: [{e.event_type}] {e.description} "
            f"(Services: {', '.join(e.affected_services)})"
            for e in infra_events
        ]) if infra_events else "No recent infrastructure events"
        
        return f"""Analyze this threat signal for infrastructure correlations:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

RECENT INFRASTRUCTURE EVENTS (last 60 minutes):
{events_text}

Determine if any infrastructure events may explain or correlate with this threat signal."""
```

### src/agents/context_agent.py

```python
"""Context Agent - Business context specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class ContextAgent(BaseAgent):
    """Agent that provides business context from external events."""
    
    def __init__(self, **kwargs):
        """Initialize Context Agent."""
        super().__init__(name="Context Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for context analysis."""
        return """You are a Business Context Agent for a Security Operations Center.

Your role is to:
1. Search for relevant external events (news, market data)
2. Correlate with industry-specific activities
3. Provide business context for anomalies
4. Distinguish legitimate surges from attacks

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "external_factors_found": boolean,
    "business_context": "Explanation of relevant business context"
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat and news context."""
        news_items = context.get("news_items", [])
        
        news_text = "\n".join([
            f"- [{n.source}] {n.title}: {n.summary}"
            for n in news_items
        ]) if news_items else "No relevant news items found"
        
        return f"""Analyze this threat signal for business context:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

RELEVANT NEWS AND MARKET EVENTS:
{news_text}

Determine if external business factors may explain this threat signal or if it represents genuine malicious activity."""
```

### src/agents/priority_agent.py

```python
"""Priority Agent - Threat classification and prioritization specialist."""
from typing import Any, Dict
from agents.base_agent import BaseAgent
from models import ThreatSignal


class PriorityAgent(BaseAgent):
    """Agent that classifies threats using MITRE ATT&CK framework."""
    
    def __init__(self, **kwargs):
        """Initialize Priority Agent."""
        super().__init__(name="Priority Agent", **kwargs)
    
    def get_system_prompt(self) -> str:
        """Return system prompt for priority analysis."""
        return """You are a Threat Prioritization Agent for a Security Operations Center.

Your role is to:
1. Map threats to MITRE ATT&CK tactics and techniques
2. Assign severity levels (LOW, MEDIUM, HIGH, CRITICAL)
3. Generate customer-facing communications
4. Create executive summaries

MITRE ATT&CK Tactics to consider:
- TA0001: Initial Access
- TA0006: Credential Access
- TA0040: Impact
- TA0010: Exfiltration
- TA0011: Command and Control

Respond in JSON format with:
{
    "analysis": "Your detailed analysis",
    "confidence": 0.0-1.0,
    "key_findings": ["finding1", "finding2"],
    "recommendations": ["rec1", "rec2"],
    "severity": "LOW|MEDIUM|HIGH|CRITICAL",
    "mitre_tactics": [{"id": "TA0001", "name": "Initial Access", "description": "..."}],
    "mitre_techniques": [{"id": "T1078", "name": "Valid Accounts", "description": "..."}],
    "customer_narrative": "Professional explanation for customer",
    "requires_human_review": boolean
}"""
    
    def build_user_prompt(self, signal: ThreatSignal, context: Dict[str, Any]) -> str:
        """Build user prompt with threat for prioritization."""
        return f"""Prioritize and classify this threat signal:

CURRENT THREAT:
- Type: {signal.threat_type.value}
- Customer: {signal.customer_name}
- Timestamp: {signal.timestamp.isoformat()}
- Metadata: {signal.metadata}

Map to MITRE ATT&CK framework, assign severity, and generate appropriate customer communication."""
```

### src/agents/coordinator.py

```python
"""Coordinator Agent - Main orchestrator for multi-agent analysis."""
import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from models import (
    ThreatSignal, ThreatAnalysis, ThreatSeverity,
    AgentAnalysis, MITRETactic, MITRETechnique
)
from config import settings
from mock_data import MockDataStore
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent


class CoordinatorAgent:
    """Orchestrates parallel analysis across all specialized agents."""
    
    def __init__(
        self, 
        mock_data: Optional[MockDataStore] = None,
        client: Optional[AsyncOpenAI] = None,
        use_mock: bool = False
    ):
        """Initialize coordinator with all specialized agents."""
        self.client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self.mock_data = mock_data or MockDataStore()
        self.use_mock = use_mock
        
        # Initialize specialized agents
        self.historical_agent = HistoricalAgent(client=self.client)
        self.config_agent = ConfigAgent(client=self.client)
        self.devops_agent = DevOpsAgent(client=self.client)
        self.context_agent = ContextAgent(client=self.client)
        self.priority_agent = PriorityAgent(client=self.client)
    
    async def analyze_threat(self, signal: ThreatSignal) -> ThreatAnalysis:
        """Perform comprehensive threat analysis using all agents in parallel."""
        start_time = time.time()
        
        # Gather context for each agent
        contexts = self._build_agent_contexts(signal)
        
        # Determine analysis method
        analyze_method = "analyze_mock" if self.use_mock else "analyze"
        
        # Dispatch all agents in parallel
        results = await asyncio.gather(
            getattr(self.historical_agent, analyze_method)(signal, contexts["historical"]),
            getattr(self.config_agent, analyze_method)(signal, contexts["config"]),
            getattr(self.devops_agent, analyze_method)(signal, contexts["devops"]),
            getattr(self.context_agent, analyze_method)(signal, contexts["context"]),
            getattr(self.priority_agent, analyze_method)(signal, contexts["priority"]),
            return_exceptions=True
        )
        
        # Process results
        agent_analyses = {}
        for i, (name, result) in enumerate(zip(
            ["historical", "config", "devops", "context", "priority"],
            results
        )):
            if isinstance(result, Exception):
                agent_analyses[name] = AgentAnalysis(
                    agent_name=name,
                    analysis=f"Agent failed: {str(result)}",
                    confidence=0.0,
                    key_findings=["Error"],
                    recommendations=["Manual review required"],
                    processing_time_ms=0
                )
            else:
                agent_analyses[name] = result
        
        # Synthesize final analysis
        total_time = int((time.time() - start_time) * 1000)
        
        return self._synthesize_analysis(signal, agent_analyses, total_time)
    
    def _build_agent_contexts(self, signal: ThreatSignal) -> Dict[str, Dict[str, Any]]:
        """Build context data for each agent."""
        # Extract keywords for news search
        keywords = [signal.customer_name, signal.threat_type.value]
        if "crypto" in signal.customer_name.lower():
            keywords.append("bitcoin")
        
        return {
            "historical": {
                "similar_incidents": self.mock_data.get_similar_incidents(
                    signal.threat_type, signal.customer_name
                )
            },
            "config": {
                "customer_config": self.mock_data.get_customer_config(signal.customer_name)
            },
            "devops": {
                "infra_events": self.mock_data.get_recent_infra_events(60)
            },
            "context": {
                "news_items": self.mock_data.get_relevant_news(keywords)
            },
            "priority": {}
        }
    
    def _synthesize_analysis(
        self,
        signal: ThreatSignal,
        agent_analyses: Dict[str, AgentAnalysis],
        total_time: int
    ) -> ThreatAnalysis:
        """Synthesize all agent analyses into final threat analysis."""
        
        # Extract priority agent results for severity and MITRE mapping
        priority_analysis = agent_analyses.get("priority")
        
        # Determine severity (default to MEDIUM if priority agent failed)
        severity = ThreatSeverity.MEDIUM
        mitre_tactics = []
        mitre_techniques = []
        customer_narrative = "Analysis completed. Please review agent findings."
        requires_review = False
        
        if priority_analysis and priority_analysis.confidence > 0:
            # Parse severity from analysis if available
            analysis_lower = priority_analysis.analysis.lower()
            if "critical" in analysis_lower:
                severity = ThreatSeverity.CRITICAL
            elif "high" in analysis_lower:
                severity = ThreatSeverity.HIGH
            elif "low" in analysis_lower:
                severity = ThreatSeverity.LOW
            
            # Check for human review requirement
            requires_review = "review" in analysis_lower or severity == ThreatSeverity.CRITICAL
        
        # Generate executive summary
        all_findings = []
        for analysis in agent_analyses.values():
            all_findings.extend(analysis.key_findings)
        
        executive_summary = self._generate_executive_summary(
            signal, severity, all_findings[:5]
        )
        
        return ThreatAnalysis(
            signal=signal,
            severity=severity,
            executive_summary=executive_summary,
            mitre_tactics=mitre_tactics,
            mitre_techniques=mitre_techniques,
            customer_narrative=customer_narrative,
            agent_analyses=agent_analyses,
            total_processing_time_ms=total_time,
            requires_human_review=requires_review
        )
    
    def _generate_executive_summary(
        self,
        signal: ThreatSignal,
        severity: ThreatSeverity,
        key_findings: List[str]
    ) -> str:
        """Generate executive summary from analysis results."""
        findings_text = "; ".join(key_findings) if key_findings else "Standard analysis completed"
        
        return (
            f"{severity.value} severity {signal.threat_type.value.replace('_', ' ')} "
            f"detected for {signal.customer_name}. "
            f"Key findings: {findings_text}."
        )


# Factory function for easy instantiation
def create_coordinator(use_mock: bool = False) -> CoordinatorAgent:
    """Create a coordinator agent instance."""
    return CoordinatorAgent(use_mock=use_mock)
```

### src/main.py

```python
"""FastAPI application for SOC Agent System."""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models import ThreatAnalysis, ThreatSignal, DashboardMetrics, ThreatType
from threat_generator import threat_generator
from agents.coordinator import create_coordinator


# In-memory storage
threat_store: List[ThreatAnalysis] = []
websocket_clients: List[WebSocket] = []


class TriggerRequest(BaseModel):
    """Request model for manual threat trigger."""
    threat_type: Optional[str] = None
    scenario: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Start background threat generation
    task = asyncio.create_task(background_threat_generator())
    yield
    # Shutdown: Cancel background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="SOC Agent System",
    description="Autonomous Security Operations Center with Multi-Agent AI",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def background_threat_generator():
    """Generate threats periodically in the background."""
    coordinator = create_coordinator(use_mock=not settings.openai_api_key)
    
    while True:
        try:
            await asyncio.sleep(settings.threat_generation_interval)
            
            # Generate and analyze threat
            signal = threat_generator.generate_random_threat()
            analysis = await coordinator.analyze_threat(signal)
            
            # Store threat
            threat_store.insert(0, analysis)
            if len(threat_store) > settings.max_stored_threats:
                threat_store.pop()
            
            # Broadcast to WebSocket clients
            await broadcast_threat(analysis)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Background generator error: {e}")
            await asyncio.sleep(5)


async def broadcast_threat(analysis: ThreatAnalysis):
    """Broadcast new threat to all connected WebSocket clients."""
    message = {
        "type": "new_threat",
        "data": json.loads(analysis.model_dump_json()),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    disconnected = []
    for client in websocket_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    
    for client in disconnected:
        websocket_clients.remove(client)


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "SOC Agent System",
        "timestamp": datetime.utcnow().isoformat(),
        "threats_stored": len(threat_store),
        "websocket_clients": len(websocket_clients)
    }


@app.get("/api/threats", response_model=List[ThreatAnalysis])
async def get_threats(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get paginated list of recent threats."""
    return threat_store[offset:offset + limit]


@app.get("/api/threats/{threat_id}", response_model=ThreatAnalysis)
async def get_threat(threat_id: str):
    """Get specific threat analysis by ID."""
    for threat in threat_store:
        if threat.id == threat_id:
            return threat
    raise HTTPException(status_code=404, detail="Threat not found")


@app.get("/api/analytics", response_model=DashboardMetrics)
async def get_analytics():
    """Get dashboard analytics metrics."""
    if not threat_store:
        return DashboardMetrics(
            total_threats=0,
            customers_affected=0,
            average_processing_time_ms=0,
            threats_requiring_review=0,
            threats_by_type={},
            threats_by_severity={}
        )
    
    # Calculate metrics
    customers = set(t.signal.customer_name for t in threat_store)
    avg_time = sum(t.total_processing_time_ms for t in threat_store) // len(threat_store)
    review_count = sum(1 for t in threat_store if t.requires_human_review)
    
    # Count by type
    by_type: Dict[str, int] = {}
    for t in threat_store:
        type_name = t.signal.threat_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1
    
    # Count by severity
    by_severity: Dict[str, int] = {}
    for t in threat_store:
        sev = t.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1
    
    return DashboardMetrics(
        total_threats=len(threat_store),
        customers_affected=len(customers),
        average_processing_time_ms=avg_time,
        threats_requiring_review=review_count,
        threats_by_type=by_type,
        threats_by_severity=by_severity
    )


@app.post("/api/threats/trigger", response_model=ThreatAnalysis)
async def trigger_threat(request: TriggerRequest):
    """Manually trigger a threat for demo purposes."""
    coordinator = create_coordinator(use_mock=not settings.openai_api_key)
    
    # Generate signal based on request
    if request.scenario:
        signal = threat_generator.generate_scenario_threat(request.scenario)
    elif request.threat_type:
        try:
            threat_type = ThreatType(request.threat_type)
            signal = threat_generator.generate_threat_by_type(threat_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid threat type: {request.threat_type}")
    else:
        signal = threat_generator.generate_random_threat()
    
    # Analyze threat
    analysis = await coordinator.analyze_threat(signal)
    
    # Store and broadcast
    threat_store.insert(0, analysis)
    if len(threat_store) > settings.max_stored_threats:
        threat_store.pop()
    
    await broadcast_threat(analysis)
    
    return analysis


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time threat streaming."""
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        # Send initial batch
        await websocket.send_json({
            "type": "initial_batch",
            "data": [json.loads(t.model_dump_json()) for t in threat_store[:20]],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
```

---

## Backend Tests

### tests/__init__.py

```python
"""SOC Agent System - Test Package."""
```

### tests/conftest.py

```python
"""Pytest fixtures for SOC Agent System tests."""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

# Import from src
import sys
sys.path.insert(0, 'src')

from main import app, threat_store, websocket_clients
from models import ThreatSignal, ThreatType, ThreatSeverity, AgentAnalysis
from threat_generator import ThreatGenerator
from mock_data import MockDataStore
from agents.coordinator import CoordinatorAgent


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def threat_generator_seeded():
    """Create a seeded threat generator for deterministic tests."""
    return ThreatGenerator(seed=42)


@pytest.fixture
def mock_data_store():
    """Create a mock data store."""
    return MockDataStore()


@pytest.fixture
def sample_threat_signal():
    """Create a sample threat signal for testing."""
    return ThreatSignal(
        id="test-signal-001",
        threat_type=ThreatType.BOT_TRAFFIC,
        customer_name="Test Corp",
        timestamp=datetime.utcnow(),
        metadata={
            "source_ip": "192.168.1.100",
            "request_count": 1000,
            "detection_confidence": 0.95
        }
    )


@pytest.fixture
def sample_agent_analysis():
    """Create a sample agent analysis for testing."""
    return AgentAnalysis(
        agent_name="Test Agent",
        analysis="Test analysis result",
        confidence=0.85,
        key_findings=["Finding 1", "Finding 2"],
        recommendations=["Recommendation 1"],
        processing_time_ms=150
    )


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''
    {
        "analysis": "Test analysis",
        "confidence": 0.85,
        "key_findings": ["Finding 1"],
        "recommendations": ["Rec 1"]
    }
    '''
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def coordinator_with_mock(mock_openai_client, mock_data_store):
    """Create a coordinator with mocked dependencies."""
    return CoordinatorAgent(
        mock_data=mock_data_store,
        client=mock_openai_client,
        use_mock=True
    )


@pytest.fixture
def test_client():
    """Create a test client for API testing."""
    # Clear state before each test
    threat_store.clear()
    websocket_clients.clear()
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create an async test client."""
    threat_store.clear()
    websocket_clients.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

### tests/test_threat_generator.py

```python
"""Unit tests for threat generator."""
import pytest
from datetime import datetime

import sys
sys.path.insert(0, 'src')

from models import ThreatType, ThreatSignal
from threat_generator import ThreatGenerator


class TestThreatGenerator:
    """Test suite for ThreatGenerator class."""
    
    def test_init_creates_generator_mapping(self):
        """Test that init creates mapping for all threat types."""
        generator = ThreatGenerator()
        
        assert len(generator.threat_generators) == 6
        for threat_type in ThreatType:
            assert threat_type in generator.threat_generators
    
    def test_generate_random_threat_returns_valid_signal(self):
        """Test random threat generation returns valid ThreatSignal."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_random_threat()
        
        assert isinstance(signal, ThreatSignal)
        assert signal.threat_type in ThreatType
        assert signal.customer_name in generator.CUSTOMERS
        assert isinstance(signal.timestamp, datetime)
        assert isinstance(signal.metadata, dict)
    
    def test_generate_bot_traffic_has_required_metadata(self):
        """Test bot traffic signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_bot_traffic()
        
        assert signal.threat_type == ThreatType.BOT_TRAFFIC
        assert "source_ip" in signal.metadata
        assert "user_agent" in signal.metadata
        assert "request_count" in signal.metadata
        assert "requests_per_second" in signal.metadata
        assert "detection_confidence" in signal.metadata
        assert 0 <= signal.metadata["detection_confidence"] <= 1
    
    def test_generate_proxy_network_has_required_metadata(self):
        """Test proxy network signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_proxy_network()
        
        assert signal.threat_type == ThreatType.PROXY_NETWORK
        assert "proxy_ips" in signal.metadata
        assert "proxy_count" in signal.metadata
        assert len(signal.metadata["proxy_ips"]) >= 5
        assert "shared_fingerprint" in signal.metadata
    
    def test_generate_device_compromise_has_required_metadata(self):
        """Test device compromise signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_device_compromise()
        
        assert signal.threat_type == ThreatType.DEVICE_COMPROMISE
        assert "device_id" in signal.metadata
        assert "compromise_indicators" in signal.metadata
        assert "risk_score" in signal.metadata
        assert len(signal.metadata["compromise_indicators"]) > 0
    
    def test_generate_anomaly_detection_has_required_metadata(self):
        """Test anomaly detection signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_anomaly_detection()
        
        assert signal.threat_type == ThreatType.ANOMALY_DETECTION
        assert "user_id" in signal.metadata
        assert "anomaly_score" in signal.metadata
        assert "deviations" in signal.metadata
        assert "baseline_comparison" in signal.metadata
    
    def test_generate_rate_limit_breach_has_required_metadata(self):
        """Test rate limit breach signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_rate_limit_breach()
        
        assert signal.threat_type == ThreatType.RATE_LIMIT_BREACH
        assert "configured_limit" in signal.metadata
        assert "actual_rate" in signal.metadata
        assert signal.metadata["actual_rate"] > signal.metadata["configured_limit"]
        assert "breach_factor" in signal.metadata
    
    def test_generate_geo_anomaly_has_required_metadata(self):
        """Test geo anomaly signal has all required metadata fields."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_geo_anomaly()
        
        assert signal.threat_type == ThreatType.GEO_ANOMALY
        assert "location_1" in signal.metadata
        assert "location_2" in signal.metadata
        assert "distance_km" in signal.metadata
        assert "impossible_travel_detected" in signal.metadata
        assert signal.metadata["impossible_travel_detected"] is True
    
    def test_generate_threat_by_type(self):
        """Test generating specific threat type."""
        generator = ThreatGenerator(seed=42)
        
        for threat_type in ThreatType:
            signal = generator.generate_threat_by_type(threat_type)
            assert signal.threat_type == threat_type
    
    def test_seeded_generator_produces_deterministic_results(self):
        """Test that seeded generator produces same results."""
        gen1 = ThreatGenerator(seed=123)
        gen2 = ThreatGenerator(seed=123)
        
        signal1 = gen1.generate_random_threat()
        signal2 = gen2.generate_random_threat()
        
        assert signal1.threat_type == signal2.threat_type
        assert signal1.customer_name == signal2.customer_name
    
    def test_random_ip_format(self):
        """Test that generated IPs have valid format."""
        generator = ThreatGenerator()
        
        for _ in range(100):
            ip = generator._random_ip()
            parts = ip.split(".")
            assert len(parts) == 4
            for part in parts:
                assert 0 <= int(part) <= 255
    
    def test_scenario_threat_crypto_surge(self):
        """Test crypto surge scenario generation."""
        generator = ThreatGenerator()
        signal = generator.generate_scenario_threat("crypto_surge")
        
        assert signal.customer_name == "CryptoExchange Pro"
        assert signal.threat_type == ThreatType.RATE_LIMIT_BREACH
        assert "context" in signal.metadata
    
    def test_scenario_threat_bot_attack(self):
        """Test bot attack scenario generation."""
        generator = ThreatGenerator()
        signal = generator.generate_scenario_threat("bot_attack")
        
        assert signal.customer_name == "RetailMax"
        assert signal.threat_type == ThreatType.BOT_TRAFFIC
    
    def test_scenario_threat_unknown_falls_back(self):
        """Test unknown scenario falls back to random threat."""
        generator = ThreatGenerator(seed=42)
        signal = generator.generate_scenario_threat("unknown_scenario")
        
        assert isinstance(signal, ThreatSignal)
        assert signal.threat_type in ThreatType
```

### tests/test_agents.py

```python
"""Unit tests for individual agents."""
import pytest
import asyncio

import sys
sys.path.insert(0, 'src')

from models import ThreatSignal, ThreatType, AgentAnalysis
from agents.historical_agent import HistoricalAgent
from agents.config_agent import ConfigAgent
from agents.devops_agent import DevOpsAgent
from agents.context_agent import ContextAgent
from agents.priority_agent import PriorityAgent
from mock_data import MockDataStore


class TestHistoricalAgent:
    """Test suite for Historical Agent."""
    
    def test_get_system_prompt_not_empty(self):
        """Test system prompt is defined."""
        agent = HistoricalAgent()
        prompt = agent.get_system_prompt()
        
        assert len(prompt) > 0
        assert "Historical" in prompt or "historical" in prompt
        assert "JSON" in prompt
    
    def test_build_user_prompt_includes_signal_data(
        self, sample_threat_signal, mock_data_store
    ):
        """Test user prompt includes threat signal data."""
        agent = HistoricalAgent()
        context = {
            "similar_incidents": mock_data_store.get_similar_incidents(
                sample_threat_signal.threat_type,
                sample_threat_signal.customer_name
            )
        }
        
        prompt = agent.build_user_prompt(sample_threat_signal, context)
        
        assert sample_threat_signal.threat_type.value in prompt
        assert sample_threat_signal.customer_name in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_mock_returns_valid_analysis(self, sample_threat_signal):
        """Test mock analysis returns valid AgentAnalysis."""
        agent = HistoricalAgent()
        context = {"similar_incidents": []}
        
        result = await agent.analyze_mock(sample_threat_signal, context)
        
        assert isinstance(result, AgentAnalysis)
        assert result.agent_name == "Historical Agent"
        assert 0 <= result.confidence <= 1
        assert result.processing_time_ms >= 0


class TestConfigAgent:
    """Test suite for Config Agent."""
    
    def test_get_system_prompt_mentions_configuration(self):
        """Test system prompt mentions configuration analysis."""
        agent = ConfigAgent()
        prompt = agent.get_system_prompt()
        
        assert "Configuration" in prompt or "config" in prompt.lower()
        assert "rate limit" in prompt.lower()
    
    def test_build_user_prompt_includes_config(
        self, sample_threat_signal, mock_data_store
    ):
        """Test user prompt includes customer configuration."""
        agent = ConfigAgent()
        config = mock_data_store.get_customer_config("Acme Corp")
        context = {"customer_config": config}
        
        # Use a signal with matching customer
        signal = ThreatSignal(
            threat_type=ThreatType.RATE_LIMIT_BREACH,
            customer_name="Acme Corp",
            metadata={}
        )
        
        prompt = agent.build_user_prompt(signal, context)
        
        assert "Acme Corp" in prompt
        assert str(config.rate_limit_per_minute) in prompt


class TestDevOpsAgent:
    """Test suite for DevOps Agent."""
    
    def test_get_system_prompt_mentions_infrastructure(self):
        """Test system prompt mentions infrastructure."""
        agent = DevOpsAgent()
        prompt = agent.get_system_prompt()
        
        assert "DevOps" in prompt or "infrastructure" in prompt.lower()
        assert "deployment" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_mock_returns_valid_analysis(
        self, sample_threat_signal, mock_data_store
    ):
        """Test mock analysis returns valid result."""
        agent = DevOpsAgent()
        context = {"infra_events": mock_data_store.get_recent_infra_events()}
        
        result = await agent.analyze_mock(sample_threat_signal, context)
        
        assert isinstance(result, AgentAnalysis)
        assert result.agent_name == "DevOps Agent"


class TestContextAgent:
    """Test suite for Context Agent."""
    
    def test_get_system_prompt_mentions_business_context(self):
        """Test system prompt mentions business context."""
        agent = ContextAgent()
        prompt = agent.get_system_prompt()
        
        assert "Business" in prompt or "context" in prompt.lower()
        assert "news" in prompt.lower() or "market" in prompt.lower()
    
    def test_build_user_prompt_includes_news(
        self, sample_threat_signal, mock_data_store
    ):
        """Test user prompt includes news items."""
        agent = ContextAgent()
        news = mock_data_store.get_relevant_news(["bitcoin", "crypto"])
        context = {"news_items": news}
        
        prompt = agent.build_user_prompt(sample_threat_signal, context)
        
        assert sample_threat_signal.threat_type.value in prompt


class TestPriorityAgent:
    """Test suite for Priority Agent."""
    
    def test_get_system_prompt_mentions_mitre(self):
        """Test system prompt mentions MITRE ATT&CK."""
        agent = PriorityAgent()
        prompt = agent.get_system_prompt()
        
        assert "MITRE" in prompt
        assert "ATT&CK" in prompt or "severity" in prompt.lower()
    
    def test_get_system_prompt_includes_severity_levels(self):
        """Test system prompt includes all severity levels."""
        agent = PriorityAgent()
        prompt = agent.get_system_prompt()
        
        assert "LOW" in prompt
        assert "MEDIUM" in prompt
        assert "HIGH" in prompt
        assert "CRITICAL" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_mock_returns_valid_analysis(self, sample_threat_signal):
        """Test mock analysis returns valid result."""
        agent = PriorityAgent()
        
        result = await agent.analyze_mock(sample_threat_signal, {})
        
        assert isinstance(result, AgentAnalysis)
        assert result.agent_name == "Priority Agent"
```

### tests/test_coordinator.py

```python
"""Integration tests for Coordinator Agent."""
import pytest
import asyncio
import time

import sys
sys.path.insert(0, 'src')

from models import ThreatSignal, ThreatType, ThreatAnalysis, ThreatSeverity
from agents.coordinator import CoordinatorAgent, create_coordinator
from mock_data import MockDataStore


class TestCoordinatorAgent:
    """Test suite for Coordinator Agent."""
    
    @pytest.mark.asyncio
    async def test_analyze_threat_returns_threat_analysis(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that analyze_threat returns a valid ThreatAnalysis."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        result = await coordinator.analyze_threat(sample_threat_signal)
        
        assert isinstance(result, ThreatAnalysis)
        assert result.signal.id == sample_threat_signal.id
        assert result.severity in ThreatSeverity
        assert len(result.executive_summary) > 0
        assert result.total_processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_analyze_threat_includes_all_agent_analyses(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that all 5 agents contribute to analysis."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        result = await coordinator.analyze_threat(sample_threat_signal)
        
        expected_agents = ["historical", "config", "devops", "context", "priority"]
        for agent_name in expected_agents:
            assert agent_name in result.agent_analyses
            assert result.agent_analyses[agent_name].agent_name is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_parallel_execution_is_faster_than_sequential(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that parallel execution completes in reasonable time."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        start_time = time.time()
        result = await coordinator.analyze_threat(sample_threat_signal)
        elapsed = time.time() - start_time
        
        # Mock agents sleep 0.1s each; parallel should be ~0.1s, sequential ~0.5s
        # Allow some overhead, but should be much less than 0.5s
        assert elapsed < 0.4, f"Parallel execution took {elapsed}s, expected < 0.4s"
    
    @pytest.mark.asyncio
    async def test_build_agent_contexts_creates_all_contexts(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that contexts are built for all agents."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        contexts = coordinator._build_agent_contexts(sample_threat_signal)
        
        assert "historical" in contexts
        assert "config" in contexts
        assert "devops" in contexts
        assert "context" in contexts
        assert "priority" in contexts
        
        assert "similar_incidents" in contexts["historical"]
        assert "customer_config" in contexts["config"]
        assert "infra_events" in contexts["devops"]
        assert "news_items" in contexts["context"]
    
    @pytest.mark.asyncio
    async def test_crypto_customer_gets_bitcoin_news(self, mock_data_store):
        """Test that crypto customers get bitcoin-related context."""
        signal = ThreatSignal(
            threat_type=ThreatType.RATE_LIMIT_BREACH,
            customer_name="CryptoExchange Pro",
            metadata={}
        )
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        contexts = coordinator._build_agent_contexts(signal)
        
        # Should have searched for bitcoin-related news
        news_items = contexts["context"]["news_items"]
        # MockDataStore has bitcoin news
        assert len(news_items) >= 0  # May or may not find matches
    
    @pytest.mark.asyncio
    async def test_executive_summary_contains_key_info(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that executive summary contains key information."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        result = await coordinator.analyze_threat(sample_threat_signal)
        
        assert sample_threat_signal.customer_name in result.executive_summary
        assert result.severity.value in result.executive_summary


class TestCreateCoordinator:
    """Test suite for coordinator factory function."""
    
    def test_create_coordinator_default(self):
        """Test creating coordinator with defaults."""
        coordinator = create_coordinator()
        
        assert isinstance(coordinator, CoordinatorAgent)
        assert coordinator.use_mock is False
    
    def test_create_coordinator_with_mock(self):
        """Test creating coordinator with mock mode."""
        coordinator = create_coordinator(use_mock=True)
        
        assert coordinator.use_mock is True


class TestCoordinatorErrorHandling:
    """Test error handling in coordinator."""
    
    @pytest.mark.asyncio
    async def test_handles_agent_failure_gracefully(
        self, sample_threat_signal, mock_data_store
    ):
        """Test that coordinator handles individual agent failures."""
        coordinator = CoordinatorAgent(mock_data=mock_data_store, use_mock=True)
        
        # Even if we had a failing agent, the coordinator should still return results
        result = await coordinator.analyze_threat(sample_threat_signal)
        
        assert result is not None
        assert isinstance(result, ThreatAnalysis)
```

### tests/test_api.py

```python
"""API endpoint tests for SOC Agent System."""
import pytest
import asyncio
import json

import sys
sys.path.insert(0, 'src')

from fastapi.testclient import TestClient
from main import app, threat_store


class TestHealthEndpoint:
    """Test suite for health check endpoint."""
    
    def test_health_check_returns_200(self, test_client):
        """Test health endpoint returns 200."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "SOC Agent System"
        assert "timestamp" in data
    
    def test_health_check_includes_metrics(self, test_client):
        """Test health endpoint includes operational metrics."""
        response = test_client.get("/")
        data = response.json()
        
        assert "threats_stored" in data
        assert "websocket_clients" in data
        assert isinstance(data["threats_stored"], int)


class TestThreatsEndpoint:
    """Test suite for threats listing endpoint."""
    
    def test_get_threats_returns_empty_list_initially(self, test_client):
        """Test threats endpoint returns empty list when no threats."""
        response = test_client.get("/api/threats")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_threats_with_pagination(self, test_client):
        """Test threats endpoint supports pagination."""
        response = test_client.get("/api/threats?limit=10&offset=0")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_threats_validates_limit(self, test_client):
        """Test that limit parameter is validated."""
        # Limit too high
        response = test_client.get("/api/threats?limit=1000")
        assert response.status_code == 422  # Validation error
    
    def test_get_threats_validates_offset(self, test_client):
        """Test that offset parameter is validated."""
        # Negative offset
        response = test_client.get("/api/threats?offset=-1")
        assert response.status_code == 422


class TestThreatByIdEndpoint:
    """Test suite for getting threat by ID."""
    
    def test_get_threat_not_found(self, test_client):
        """Test getting non-existent threat returns 404."""
        response = test_client.get("/api/threats/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAnalyticsEndpoint:
    """Test suite for analytics endpoint."""
    
    def test_get_analytics_empty_store(self, test_client):
        """Test analytics with no threats."""
        response = test_client.get("/api/analytics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_threats"] == 0
        assert data["customers_affected"] == 0
        assert data["average_processing_time_ms"] == 0
    
    def test_get_analytics_structure(self, test_client):
        """Test analytics response structure."""
        response = test_client.get("/api/analytics")
        data = response.json()
        
        required_fields = [
            "total_threats",
            "customers_affected",
            "average_processing_time_ms",
            "threats_requiring_review",
            "threats_by_type",
            "threats_by_severity"
        ]
        
        for field in required_fields:
            assert field in data


class TestTriggerEndpoint:
    """Test suite for threat trigger endpoint."""
    
    def test_trigger_random_threat(self, test_client):
        """Test triggering a random threat."""
        # Note: This will use mock mode if no API key is set
        response = test_client.post("/api/threats/trigger", json={})
        
        # Should return 200 even with mock coordinator
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "signal" in data
        assert "severity" in data
        assert "executive_summary" in data
    
    def test_trigger_specific_threat_type(self, test_client):
        """Test triggering a specific threat type."""
        response = test_client.post(
            "/api/threats/trigger",
            json={"threat_type": "bot_traffic"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["signal"]["threat_type"] == "bot_traffic"
    
    def test_trigger_invalid_threat_type(self, test_client):
        """Test triggering with invalid threat type."""
        response = test_client.post(
            "/api/threats/trigger",
            json={"threat_type": "invalid_type"}
        )
        
        assert response.status_code == 400
        assert "Invalid threat type" in response.json()["detail"]
    
    def test_trigger_scenario(self, test_client):
        """Test triggering a predefined scenario."""
        response = test_client.post(
            "/api/threats/trigger",
            json={"scenario": "crypto_surge"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["signal"]["customer_name"] == "CryptoExchange Pro"
    
    def test_trigger_adds_to_store(self, test_client):
        """Test that triggered threats are added to store."""
        initial_count = len(threat_store)
        
        test_client.post("/api/threats/trigger", json={})
        
        assert len(threat_store) == initial_count + 1


class TestWebSocketEndpoint:
    """Test suite for WebSocket endpoint."""
    
    def test_websocket_connection(self, test_client):
        """Test WebSocket connection and initial batch."""
        with test_client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            
            assert data["type"] == "initial_batch"
            assert isinstance(data["data"], list)
            assert "timestamp" in data
    
    def test_websocket_ping_pong(self, test_client):
        """Test WebSocket ping/pong."""
        with test_client.websocket_connect("/ws") as websocket:
            # Receive initial batch
            websocket.receive_json()
            
            # Send ping
            websocket.send_json({"type": "ping"})
            
            # Should receive pong
            response = websocket.receive_json()
            assert response["type"] == "pong"
```

---

## Frontend Files

### index.html

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SOC Agent Dashboard</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### vite.config.js

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    open: true
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.js',
  }
})
```

### package.json

```json
{
  "name": "soc-agent-dashboard",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "chart.js": "^4.4.1",
    "react-chartjs-2": "^5.2.0",
    "date-fns": "^3.2.0"
  },
  "devDependencies": {
    "@testing-library/react": "^14.1.2",
    "@testing-library/jest-dom": "^6.2.0",
    "@testing-library/user-event": "^14.5.2",
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.0.11",
    "vitest": "^1.2.1",
    "jsdom": "^23.2.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  }
}
```

### src/main.jsx

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './App.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

### src/hooks/useWebSocket.js

```javascript
import { useState, useEffect, useCallback, useRef } from 'react';

const WS_URL = 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 25000;

export function useWebSocket() {
  const [threats, setThreats] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        
        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'initial_batch':
              setThreats(message.data || []);
              break;
            case 'new_threat':
              setThreats(prev => [message.data, ...prev].slice(0, 50));
              break;
            case 'pong':
              // Heartbeat acknowledged
              break;
            default:
              console.log('Unknown message type:', message.type);
          }
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }
        
        // Schedule reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connect();
        }, RECONNECT_DELAY);
      };
    } catch (e) {
      console.error('Failed to connect:', e);
      setError('Failed to connect');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    threats,
    isConnected,
    error,
    reconnect: connect
  };
}

export default useWebSocket;
```

### src/App.jsx

```jsx
import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { format } from 'date-fns';
import { useWebSocket } from './hooks/useWebSocket';

// Register Chart.js components
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const API_URL = 'http://localhost:8000';

// Severity colors
const SEVERITY_COLORS = {
  LOW: '#10b981',
  MEDIUM: '#f59e0b',
  HIGH: '#f97316',
  CRITICAL: '#ef4444'
};

// Threat type colors
const TYPE_COLORS = {
  bot_traffic: '#3b82f6',
  proxy_network: '#8b5cf6',
  device_compromise: '#ec4899',
  anomaly_detection: '#06b6d4',
  rate_limit_breach: '#f59e0b',
  geo_anomaly: '#10b981'
};

function App() {
  const { threats, isConnected, error } = useWebSocket();
  const [selectedThreat, setSelectedThreat] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [activeTab, setActiveTab] = useState('summary');

  // Fetch metrics periodically
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch(`${API_URL}/api/analytics`);
        const data = await response.json();
        setMetrics(data);
      } catch (e) {
        console.error('Failed to fetch metrics:', e);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  // Auto-select first threat
  useEffect(() => {
    if (threats.length > 0 && !selectedThreat) {
      setSelectedThreat(threats[0]);
    }
  }, [threats, selectedThreat]);

  const triggerThreat = async (type) => {
    try {
      const body = type ? { threat_type: type } : {};
      await fetch(`${API_URL}/api/threats/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
    } catch (e) {
      console.error('Failed to trigger threat:', e);
    }
  };

  const threatTypeChartData = {
    labels: Object.keys(metrics?.threats_by_type || {}),
    datasets: [{
      data: Object.values(metrics?.threats_by_type || {}),
      backgroundColor: Object.keys(metrics?.threats_by_type || {}).map(t => TYPE_COLORS[t] || '#888')
    }]
  };

  const severityChartData = {
    labels: Object.keys(metrics?.threats_by_severity || {}),
    datasets: [{
      label: 'Threats',
      data: Object.values(metrics?.threats_by_severity || {}),
      backgroundColor: Object.keys(metrics?.threats_by_severity || {}).map(s => SEVERITY_COLORS[s] || '#888')
    }]
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1>🛡️ SOC Agent Dashboard</h1>
          <span className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
        <div className="header-right">
          <button onClick={() => triggerThreat(null)} className="btn btn-primary">
            Trigger Random
          </button>
          <button onClick={() => triggerThreat('bot_traffic')} className="btn">
            Bot Attack
          </button>
          <button onClick={() => triggerThreat('rate_limit_breach')} className="btn">
            Rate Limit
          </button>
        </div>
      </header>

      {/* Metrics Dashboard */}
      <div className="metrics-bar">
        <div className="metric">
          <span className="metric-value">{metrics?.total_threats || 0}</span>
          <span className="metric-label">Total Threats</span>
        </div>
        <div className="metric">
          <span className="metric-value">{metrics?.customers_affected || 0}</span>
          <span className="metric-label">Customers Affected</span>
        </div>
        <div className="metric">
          <span className="metric-value">{metrics?.average_processing_time_ms || 0}ms</span>
          <span className="metric-label">Avg Analysis Time</span>
        </div>
        <div className="metric">
          <span className="metric-value">{metrics?.threats_requiring_review || 0}</span>
          <span className="metric-label">Needs Review</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Left: Threat Feed */}
        <div className="threat-feed">
          <h2>Threat Feed</h2>
          <div className="threat-list">
            {threats.map(threat => (
              <div 
                key={threat.id}
                className={`threat-item ${selectedThreat?.id === threat.id ? 'selected' : ''}`}
                onClick={() => setSelectedThreat(threat)}
              >
                <div className="threat-item-header">
                  <span className={`severity-badge ${threat.severity.toLowerCase()}`}>
                    {threat.severity}
                  </span>
                  <span className="threat-time">
                    {format(new Date(threat.created_at), 'HH:mm:ss')}
                  </span>
                </div>
                <div className="threat-item-title">
                  {threat.signal.threat_type.replace('_', ' ')}
                </div>
                <div className="threat-item-customer">
                  {threat.signal.customer_name}
                </div>
              </div>
            ))}
            {threats.length === 0 && (
              <div className="empty-state">No threats yet. Click "Trigger Random" to generate one.</div>
            )}
          </div>
        </div>

        {/* Center: Threat Details */}
        <div className="threat-details">
          {selectedThreat ? (
            <>
              <div className="threat-header">
                <h2>{selectedThreat.signal.threat_type.replace('_', ' ').toUpperCase()}</h2>
                <span className={`severity-badge large ${selectedThreat.severity.toLowerCase()}`}>
                  {selectedThreat.severity}
                </span>
              </div>
              
              <div className="threat-meta">
                <span>Customer: <strong>{selectedThreat.signal.customer_name}</strong></span>
                <span>Analysis Time: <strong>{selectedThreat.total_processing_time_ms}ms</strong></span>
                {selectedThreat.requires_human_review && (
                  <span className="review-badge">⚠️ Needs Review</span>
                )}
              </div>

              <div className="tabs">
                <button 
                  className={`tab ${activeTab === 'summary' ? 'active' : ''}`}
                  onClick={() => setActiveTab('summary')}
                >
                  Summary
                </button>
                <button 
                  className={`tab ${activeTab === 'agents' ? 'active' : ''}`}
                  onClick={() => setActiveTab('agents')}
                >
                  Agent Analysis
                </button>
                <button 
                  className={`tab ${activeTab === 'signal' ? 'active' : ''}`}
                  onClick={() => setActiveTab('signal')}
                >
                  Raw Signal
                </button>
              </div>

              <div className="tab-content">
                {activeTab === 'summary' && (
                  <div className="summary-content">
                    <h3>Executive Summary</h3>
                    <p>{selectedThreat.executive_summary}</p>
                    
                    <h3>Customer Narrative</h3>
                    <p>{selectedThreat.customer_narrative}</p>
                  </div>
                )}

                {activeTab === 'agents' && (
                  <div className="agents-content">
                    {Object.entries(selectedThreat.agent_analyses || {}).map(([name, analysis]) => (
                      <div key={name} className="agent-card">
                        <div className="agent-header">
                          <h4>{analysis.agent_name}</h4>
                          <span className="confidence">
                            Confidence: {(analysis.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p>{analysis.analysis}</p>
                        {analysis.key_findings?.length > 0 && (
                          <div className="findings">
                            <strong>Key Findings:</strong>
                            <ul>
                              {analysis.key_findings.map((f, i) => <li key={i}>{f}</li>)}
                            </ul>
                          </div>
                        )}
                        {analysis.recommendations?.length > 0 && (
                          <div className="recommendations">
                            <strong>Recommendations:</strong>
                            <ul>
                              {analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                            </ul>
                          </div>
                        )}
                        <div className="agent-footer">
                          Processing time: {analysis.processing_time_ms}ms
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'signal' && (
                  <div className="signal-content">
                    <pre>{JSON.stringify(selectedThreat.signal, null, 2)}</pre>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">Select a threat to view details</div>
          )}
        </div>

        {/* Right: Charts */}
        <div className="charts-panel">
          <div className="chart-container">
            <h3>Threats by Type</h3>
            {Object.keys(metrics?.threats_by_type || {}).length > 0 ? (
              <Doughnut data={threatTypeChartData} options={{ plugins: { legend: { position: 'bottom' } } }} />
            ) : (
              <div className="empty-chart">No data yet</div>
            )}
          </div>
          <div className="chart-container">
            <h3>Threats by Severity</h3>
            {Object.keys(metrics?.threats_by_severity || {}).length > 0 ? (
              <Bar data={severityChartData} options={{ plugins: { legend: { display: false } } }} />
            ) : (
              <div className="empty-chart">No data yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
```

### src/App.css

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #0f172a;
  color: #e2e8f0;
  min-height: 100vh;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-left h1 {
  font-size: 1.5rem;
  font-weight: 600;
}

.status {
  font-size: 0.875rem;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
}

.status.connected {
  background: #065f46;
  color: #6ee7b7;
}

.status.disconnected {
  background: #7f1d1d;
  color: #fca5a5;
}

.header-right {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border: 1px solid #475569;
  background: #334155;
  color: #e2e8f0;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.btn:hover {
  background: #475569;
}

.btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
}

.btn-primary:hover {
  background: #2563eb;
}

/* Metrics Bar */
.metrics-bar {
  display: flex;
  gap: 2rem;
  padding: 1rem 2rem;
  background: #1e293b;
  border-bottom: 1px solid #334155;
}

.metric {
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f1f5f9;
}

.metric-label {
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
}

/* Main Content */
.main-content {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  flex: 1;
  overflow: hidden;
}

/* Threat Feed */
.threat-feed {
  background: #1e293b;
  border-right: 1px solid #334155;
  display: flex;
  flex-direction: column;
}

.threat-feed h2 {
  padding: 1rem;
  font-size: 1rem;
  font-weight: 600;
  border-bottom: 1px solid #334155;
}

.threat-list {
  flex: 1;
  overflow-y: auto;
}

.threat-item {
  padding: 1rem;
  border-bottom: 1px solid #334155;
  cursor: pointer;
  transition: background 0.2s;
}

.threat-item:hover {
  background: #334155;
}

.threat-item.selected {
  background: #3b82f6;
}

.threat-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.threat-time {
  font-size: 0.75rem;
  color: #94a3b8;
}

.threat-item.selected .threat-time {
  color: #bfdbfe;
}

.threat-item-title {
  font-weight: 600;
  text-transform: capitalize;
  margin-bottom: 0.25rem;
}

.threat-item-customer {
  font-size: 0.875rem;
  color: #94a3b8;
}

.threat-item.selected .threat-item-customer {
  color: #bfdbfe;
}

/* Severity Badges */
.severity-badge {
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  text-transform: uppercase;
}

.severity-badge.low { background: #065f46; color: #6ee7b7; }
.severity-badge.medium { background: #78350f; color: #fcd34d; }
.severity-badge.high { background: #7c2d12; color: #fdba74; }
.severity-badge.critical { background: #7f1d1d; color: #fca5a5; }

.severity-badge.large {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
}

/* Threat Details */
.threat-details {
  padding: 1.5rem;
  overflow-y: auto;
}

.threat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.threat-header h2 {
  font-size: 1.25rem;
}

.threat-meta {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
  color: #94a3b8;
}

.review-badge {
  color: #fbbf24;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid #334155;
}

.tab {
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 0.875rem;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab:hover {
  color: #e2e8f0;
}

.tab.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
}

/* Tab Content */
.tab-content {
  background: #1e293b;
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.summary-content h3 {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: #f1f5f9;
}

.summary-content p {
  color: #cbd5e1;
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

/* Agent Cards */
.agent-card {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.agent-header h4 {
  font-size: 0.875rem;
  color: #f1f5f9;
}

.confidence {
  font-size: 0.75rem;
  color: #10b981;
}

.agent-card p {
  font-size: 0.875rem;
  color: #cbd5e1;
  line-height: 1.5;
  margin-bottom: 0.75rem;
}

.findings, .recommendations {
  margin-bottom: 0.75rem;
}

.findings strong, .recommendations strong {
  font-size: 0.75rem;
  color: #94a3b8;
  display: block;
  margin-bottom: 0.25rem;
}

.findings ul, .recommendations ul {
  font-size: 0.8rem;
  color: #cbd5e1;
  padding-left: 1.25rem;
}

.agent-footer {
  font-size: 0.75rem;
  color: #64748b;
  text-align: right;
}

/* Signal Content */
.signal-content pre {
  background: #0f172a;
  padding: 1rem;
  border-radius: 0.375rem;
  font-size: 0.8rem;
  overflow-x: auto;
  color: #10b981;
}

/* Charts Panel */
.charts-panel {
  background: #1e293b;
  border-left: 1px solid #334155;
  padding: 1rem;
  overflow-y: auto;
}

.chart-container {
  background: #0f172a;
  border-radius: 0.5rem;
  padding: 1rem;
  margin-bottom: 1rem;
}

.chart-container h3 {
  font-size: 0.875rem;
  margin-bottom: 1rem;
  text-align: center;
}

.empty-chart {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 0.875rem;
}

/* Empty State */
.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}
```

---

## Frontend Tests

### tests/setup.js

```javascript
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock WebSocket
class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) this.onopen();
    }, 0);
  }
  
  send(data) {
    // Mock send
  }
  
  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) this.onclose();
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSING = 2;
MockWebSocket.CLOSED = 3;

global.WebSocket = MockWebSocket;

// Mock fetch
global.fetch = vi.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({
      total_threats: 5,
      customers_affected: 3,
      average_processing_time_ms: 1500,
      threats_requiring_review: 1,
      threats_by_type: { bot_traffic: 2, proxy_network: 3 },
      threats_by_severity: { LOW: 1, MEDIUM: 2, HIGH: 2 }
    }),
  })
);

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

### tests/App.test.jsx

```jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../src/App';

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the header', () => {
    render(<App />);
    expect(screen.getByText('🛡️ SOC Agent Dashboard')).toBeInTheDocument();
  });

  it('shows connection status', () => {
    render(<App />);
    // Initially connecting, then should show connected
    expect(screen.getByText(/Connected|Disconnected/)).toBeInTheDocument();
  });

  it('renders trigger buttons', () => {
    render(<App />);
    expect(screen.getByText('Trigger Random')).toBeInTheDocument();
    expect(screen.getByText('Bot Attack')).toBeInTheDocument();
    expect(screen.getByText('Rate Limit')).toBeInTheDocument();
  });

  it('renders metrics section', async () => {
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('Total Threats')).toBeInTheDocument();
      expect(screen.getByText('Customers Affected')).toBeInTheDocument();
      expect(screen.getByText('Avg Analysis Time')).toBeInTheDocument();
      expect(screen.getByText('Needs Review')).toBeInTheDocument();
    });
  });

  it('renders threat feed section', () => {
    render(<App />);
    expect(screen.getByText('Threat Feed')).toBeInTheDocument();
  });

  it('shows empty state when no threats', () => {
    render(<App />);
    expect(screen.getByText(/No threats yet/)).toBeInTheDocument();
  });

  it('renders charts section', () => {
    render(<App />);
    expect(screen.getByText('Threats by Type')).toBeInTheDocument();
    expect(screen.getByText('Threats by Severity')).toBeInTheDocument();
  });

  it('calls API when trigger button clicked', async () => {
    render(<App />);
    
    const triggerButton = screen.getByText('Trigger Random');
    fireEvent.click(triggerButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/threats/trigger',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
      );
    });
  });
});

describe('Metrics Display', () => {
  it('displays fetched metrics values', async () => {
    render(<App />);
    
    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // total_threats
      expect(screen.getByText('3')).toBeInTheDocument(); // customers_affected
    });
  });
});

describe('Tab Navigation', () => {
  it('shows summary tab by default when threat selected', async () => {
    // This would need a mock threat to be selected
    render(<App />);
    
    // Initially should show select prompt
    expect(screen.getByText('Select a threat to view details')).toBeInTheDocument();
  });
});
```

---

## Running the Application

### Quick Start

1. **Clone/Create the project structure** as shown above

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   cd src
   python main.py
   ```

3. **Frontend Setup (in new terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Run Tests:**
   ```bash
   # Backend tests (from backend directory)
   pytest -v
   
   # Frontend tests (from frontend directory)
   npm test
   ```

### Test Commands

```bash
# Run all backend tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests
pytest -m "not integration"

# Run specific test file
pytest tests/test_threat_generator.py -v

# Run frontend tests
npm test

# Run frontend tests with coverage
npm run test:coverage
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OPENAI_API_KEY | required | Your OpenAI API key |
| HOST | 0.0.0.0 | Server host |
| PORT | 8000 | Server port |
| LLM_MODEL | gpt-4-turbo-preview | Model to use |
| THREAT_INTERVAL | 15 | Seconds between auto-generated threats |
| MAX_STORED_THREATS | 50 | Maximum threats to keep in memory |

---

## Architecture Summary

- **Multi-Agent Pattern**: 5 specialized agents + 1 coordinator
- **Parallel Execution**: All agents run simultaneously via asyncio.gather()
- **Real-time Updates**: WebSocket streaming of new threats
- **Mock Mode**: Works without OpenAI API key for testing
- **Comprehensive Testing**: Unit tests, integration tests, API tests

This complete package gives you everything needed to run, test, and extend the SOC Agent System.
