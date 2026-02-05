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
    INFO = "INFO"


class ThreatStatus(str, Enum):
    """Status of threat analysis."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class ResponseActionType(str, Enum):
    """Types of automated response actions."""
    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    CHALLENGE = "challenge"
    WHITELIST = "whitelist"
    MONITOR = "monitor"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"
    NONE = "none"


class ResponseUrgency(str, Enum):
    """Urgency level for response actions."""
    IMMEDIATE = "immediate"
    URGENT = "urgent"
    NORMAL = "normal"
    LOW = "low"


class TimelineEventType(str, Enum):
    """Types of events in investigation timeline."""
    DETECTION = "detection"
    ENRICHMENT = "enrichment"
    ANALYSIS = "analysis"
    CORRELATION = "correlation"
    DECISION = "decision"
    ACTION = "action"
    ESCALATION = "escalation"


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
    data_sources_consulted: List[str] = Field(default_factory=list)


# ============================================================================
# FALSE POSITIVE SCORING
# ============================================================================

class FalsePositiveIndicator(BaseModel):
    """Individual indicator contributing to FP score."""
    indicator: str
    weight: float = Field(ge=-1.0, le=1.0)  # Negative = likely real threat
    description: str
    source: str  # Which agent/analyzer identified this


class FalsePositiveScore(BaseModel):
    """Comprehensive false positive analysis."""
    score: float = Field(ge=0.0, le=1.0)  # 0 = definitely real, 1 = definitely FP
    confidence: float = Field(ge=0.0, le=1.0)
    indicators: List[FalsePositiveIndicator] = Field(default_factory=list)
    historical_fp_rate: Optional[float] = None  # FP rate for similar threats
    similar_resolved_as_fp: int = 0  # Count of similar threats resolved as FP
    similar_resolved_as_real: int = 0  # Count of similar threats confirmed real
    recommendation: str = ""  # "likely_false_positive", "likely_real_threat", "needs_review"
    explanation: str = ""


# ============================================================================
# RESPONSE ACTIONS
# ============================================================================

class ResponseAction(BaseModel):
    """A recommended or executed response action."""
    action_type: ResponseActionType
    urgency: ResponseUrgency
    target: str  # IP, user, endpoint, etc.
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    auto_executable: bool = False  # Can be auto-executed without human approval
    requires_approval: bool = True
    estimated_impact: str = ""  # "Low", "Medium", "High"
    rollback_possible: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ResponsePlan(BaseModel):
    """Complete response plan with multiple actions."""
    primary_action: ResponseAction
    secondary_actions: List[ResponseAction] = Field(default_factory=list)
    escalation_path: List[str] = Field(default_factory=list)  # Team/person escalation order
    sla_minutes: int = 60  # Time to respond
    auto_escalate_after_minutes: int = 30
    notes: str = ""


# ============================================================================
# INVESTIGATION TIMELINE
# ============================================================================

class TimelineEvent(BaseModel):
    """Single event in the investigation timeline."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: TimelineEventType
    title: str
    description: str
    source: str  # Agent name, system, or data source
    data: Dict[str, Any] = Field(default_factory=dict)
    severity: Optional[ThreatSeverity] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class InvestigationTimeline(BaseModel):
    """Complete investigation timeline."""
    events: List[TimelineEvent] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: int = 0

    def add_event(self, event: TimelineEvent):
        """Add event to timeline and sort by timestamp."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


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
    status: ThreatStatus = ThreatStatus.COMPLETED
    severity: ThreatSeverity
    executive_summary: str
    mitre_tactics: List[MITRETactic] = Field(default_factory=list)
    mitre_techniques: List[MITRETechnique] = Field(default_factory=list)
    customer_narrative: str
    agent_analyses: Dict[str, AgentAnalysis] = Field(default_factory=dict)

    # NEW: Enhanced analysis features
    false_positive_score: Optional[FalsePositiveScore] = None
    response_plan: Optional[ResponsePlan] = None
    investigation_timeline: Optional[InvestigationTimeline] = None

    # Metadata
    total_processing_time_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    requires_human_review: bool = False
    review_reason: Optional[str] = None

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
    severity: ThreatSeverity = ThreatSeverity.MEDIUM
    timestamp: datetime
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolution: str
    resolved_as: str = "inconclusive"  # "true_positive", "false_positive", "inconclusive"
    was_false_positive: bool = False
    resolution_notes: str = ""
    indicators: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class CustomerConfig(BaseModel):
    """Customer-specific configuration."""
    customer_name: str
    customer_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    tier: str = "standard"  # "standard", "premium", "enterprise"
    rate_limit_per_minute: int
    rate_limit_rpm: int = 1000  # Alias for compatibility
    geo_restrictions: List[str]
    bot_detection_sensitivity: str
    bot_protection_enabled: bool = True
    auto_block_enabled: bool = False
    escalation_contacts: List[str] = Field(default_factory=list)
    whitelist_ips: List[str] = Field(default_factory=list)
    custom_rules: Dict[str, Any] = Field(default_factory=dict)


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

