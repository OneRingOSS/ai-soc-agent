"""Health check endpoints for Kubernetes liveness and readiness probes."""
import time
import logging
from typing import Dict, Any, Optional

from agents.coordinator import CoordinatorAgent

logger = logging.getLogger(__name__)

# Track application startup time
_startup_time = time.time()

# Track readiness state
_coordinator: Optional[CoordinatorAgent] = None


def set_coordinator(coordinator: CoordinatorAgent):
    """
    Set the coordinator instance for readiness checks.
    
    This should be called during application startup after the coordinator
    is initialized.
    
    Args:
        coordinator: The initialized CoordinatorAgent instance
    """
    global _coordinator
    _coordinator = coordinator
    logger.info("✅ Coordinator registered for health checks")


def get_uptime_seconds() -> float:
    """
    Get application uptime in seconds.
    
    Returns:
        Uptime in seconds since application start
    """
    return time.time() - _startup_time


def check_liveness() -> Dict[str, Any]:
    """
    Liveness check - returns healthy if process is running.
    
    This is used for Kubernetes liveness probes. It should be fast (<5ms)
    and always return healthy if the process is alive.
    
    Returns:
        Dictionary with status, version, and uptime
    """
    return {
        "status": "healthy",
        "version": "2.0",
        "uptime_seconds": round(get_uptime_seconds(), 2)
    }


def check_readiness() -> tuple[Dict[str, Any], int]:
    """
    Readiness check - returns ready only when all components are initialized.
    
    This is used for Kubernetes readiness probes. It checks that:
    - Coordinator is initialized
    - All 5 agents are available
    - All 3 analyzers are loaded
    
    Returns:
        Tuple of (response_dict, status_code)
        - 200 if ready
        - 503 if not ready
    """
    components = {
        "coordinator": False,
        "agents": {
            "historical": False,
            "config": False,
            "devops": False,
            "context": False,
            "priority": False
        },
        "analyzers": {
            "fp": False,
            "response": False,
            "timeline": False
        }
    }
    
    # Check if coordinator is initialized
    if _coordinator is None:
        return {
            "status": "not_ready",
            "reason": "Coordinator not initialized",
            "components": components
        }, 503
    
    # Coordinator is initialized
    components["coordinator"] = True
    
    # Check agents
    try:
        components["agents"]["historical"] = _coordinator.historical_agent is not None
        components["agents"]["config"] = _coordinator.config_agent is not None
        components["agents"]["devops"] = _coordinator.devops_agent is not None
        components["agents"]["context"] = _coordinator.context_agent is not None
        components["agents"]["priority"] = _coordinator.priority_agent is not None
    except AttributeError:
        pass
    
    # Check analyzers
    try:
        components["analyzers"]["fp"] = _coordinator.fp_analyzer is not None
        components["analyzers"]["response"] = _coordinator.response_engine is not None
        components["analyzers"]["timeline"] = _coordinator.timeline_builder is not None
    except AttributeError:
        pass
    
    # Determine if all components are ready
    all_agents_ready = all(components["agents"].values())
    all_analyzers_ready = all(components["analyzers"].values())
    all_ready = components["coordinator"] and all_agents_ready and all_analyzers_ready
    
    if all_ready:
        return {
            "status": "ready",
            "components": components
        }, 200
    else:
        # Find which component is not ready
        not_ready = []
        if not components["coordinator"]:
            not_ready.append("coordinator")
        for agent, ready in components["agents"].items():
            if not ready:
                not_ready.append(f"agent:{agent}")
        for analyzer, ready in components["analyzers"].items():
            if not ready:
                not_ready.append(f"analyzer:{analyzer}")
        
        return {
            "status": "not_ready",
            "reason": f"Components not ready: {', '.join(not_ready)}",
            "components": components
        }, 503

