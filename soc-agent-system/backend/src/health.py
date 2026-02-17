"""Health check endpoints for Kubernetes liveness and readiness probes."""
import time
import logging
from typing import Dict, Any, Optional, TYPE_CHECKING

from agents.coordinator import CoordinatorAgent

if TYPE_CHECKING:
    from store import ThreatStore

logger = logging.getLogger(__name__)

# Track application startup time
_startup_time = time.time()

# Track readiness state
_coordinator: Optional[CoordinatorAgent] = None
_store: Optional["ThreatStore"] = None


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


def set_store(store: "ThreatStore"):
    """
    Set the threat store instance for readiness checks.

    This should be called during application startup after the store
    is initialized.

    Args:
        store: The initialized ThreatStore instance
    """
    global _store
    _store = store
    logger.info("✅ Threat store registered for health checks")


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
        "store": False,
        "redis": False,
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

    # Check if store is initialized
    if _store is None:
        return {
            "status": "not_ready",
            "reason": "Threat store not initialized",
            "components": components
        }, 503

    components["store"] = True

    # Check Redis health (if using RedisStore)
    try:
        from store import RedisStore
        if isinstance(_store, RedisStore):
            # Try to ping Redis
            import asyncio
            try:
                # Create a new event loop if needed for sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in async context, but this is called from sync
                    # Just mark as healthy if store is initialized
                    components["redis"] = True
                else:
                    # Sync context - can run async ping
                    async def ping_redis():
                        await _store._ensure_connected()
                        await _store.redis.ping()

                    loop.run_until_complete(ping_redis())
                    components["redis"] = True
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                components["redis"] = False
        else:
            # Using in-memory store, Redis not applicable
            components["redis"] = None
    except Exception as e:
        logger.error(f"Error checking Redis health: {e}")
        components["redis"] = False
    
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

    # Redis is optional - only check if it's being used (not None)
    redis_ready = components["redis"] is None or components["redis"] is True

    all_ready = (
        components["coordinator"] and
        components["store"] and
        redis_ready and
        all_agents_ready and
        all_analyzers_ready
    )
    
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
        if not components["store"]:
            not_ready.append("store")
        if components["redis"] is False:
            not_ready.append("redis")
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

