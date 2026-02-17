"""
Prometheus metrics for SOC Agent System.

This module defines custom Prometheus metrics for monitoring threat analysis performance,
agent execution times, false positive scores, and other business metrics.
"""
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)

# ============================================================================
# Custom Prometheus Metrics
# ============================================================================

# Counter: Total threats processed
soc_threats_processed_total = Counter(
    'soc_threats_processed_total',
    'Total number of threats processed by the SOC system',
    ['severity', 'threat_type'],
    registry=REGISTRY
)

# Histogram: Agent execution duration
soc_agent_duration_seconds = Histogram(
    'soc_agent_duration_seconds',
    'Duration of individual agent execution in seconds',
    ['agent_name'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=REGISTRY
)

# Histogram: False positive score distribution
soc_fp_score = Histogram(
    'soc_fp_score',
    'Distribution of false positive scores (0.0 to 1.0)',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=REGISTRY
)

# Histogram: Threat processing duration by phase
soc_threat_processing_duration_seconds = Histogram(
    'soc_threat_processing_duration_seconds',
    'Duration of threat processing by phase',
    ['phase'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY
)

# Gauge: Active WebSocket connections
soc_active_websocket_connections = Gauge(
    'soc_active_websocket_connections',
    'Number of active WebSocket connections',
    registry=REGISTRY
)

# Gauge: Threats requiring human review
soc_threats_requiring_review = Gauge(
    'soc_threats_requiring_review',
    'Number of threats currently requiring human review',
    registry=REGISTRY
)


# ============================================================================
# Instrumentator Setup
# ============================================================================

def create_instrumentator() -> Instrumentator:
    """
    Create and configure the Prometheus FastAPI instrumentator.
    
    This provides automatic HTTP metrics for all FastAPI endpoints:
    - Request count
    - Request duration (histogram)
    - Requests in progress
    - Response size
    
    Returns:
        Configured Instrumentator instance
    """
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=False,
        should_respect_env_var=False,  # Always enable metrics
        should_instrument_requests_inprogress=True,
        excluded_handlers=[],  # Don't exclude any handlers
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )
    
    # Add default metrics
    instrumentator.add()
    
    logger.info("✅ Prometheus instrumentator configured")
    return instrumentator


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of current metric values.
    
    This is useful for health check endpoints or debugging.
    Returns a dict with current values of key metrics.
    
    Returns:
        Dictionary with metric summaries
    """
    try:
        # Get samples from the registry
        samples = {}
        for metric in REGISTRY.collect():
            for sample in metric.samples:
                samples[sample.name] = sample.value
        
        return {
            "threats_processed": samples.get("soc_threats_processed_total", 0),
            "active_websockets": samples.get("soc_active_websocket_connections", 0),
            "threats_requiring_review": samples.get("soc_threats_requiring_review", 0),
            "metrics_available": True
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return {
            "metrics_available": False,
            "error": str(e)
        }


# ============================================================================
# Metric Recording Helper Functions
# ============================================================================

def record_threat_processed(severity: str, threat_type: str):
    """Record that a threat was processed."""
    soc_threats_processed_total.labels(severity=severity, threat_type=threat_type).inc()


def record_agent_duration(agent_name: str, duration_seconds: float):
    """Record agent execution duration."""
    soc_agent_duration_seconds.labels(agent_name=agent_name).observe(duration_seconds)


def record_fp_score(score: float):
    """Record false positive score."""
    soc_fp_score.observe(score)


def record_processing_phase(phase: str, duration_seconds: float):
    """Record processing phase duration."""
    soc_threat_processing_duration_seconds.labels(phase=phase).observe(duration_seconds)

