"""FastAPI application for SOC Agent System."""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models import ThreatAnalysis, DashboardMetrics, ThreatType
from threat_generator import threat_generator
from agents.coordinator import create_coordinator
from logger import setup_json_logging, get_logger
from telemetry import init_telemetry, instrument_fastapi
from metrics import create_instrumentator, soc_active_websocket_connections
from health import check_liveness, check_readiness, set_coordinator, set_store
from store import create_store, ThreatStore
from wazuh_translator import (
    translate_wazuh_alert,
    InvalidWazuhAlertError,
    UnsupportedWazuhAlertError,
    WazuhValidationError
)
from security.egress_monitor import (  # Tier 3A
    record_egress_violation,
    get_recent_violations,
    EgressViolation
)

# Configure structured JSON logging
setup_json_logging("INFO")

logger = get_logger(__name__)


def build_redis_url() -> str:
    """
    Construct Redis URL from environment variables.
    Mirrors the OPENAI_API_KEY pattern: read from env, never hardcode.

    Priority:
    1. REDIS_URL if it already contains credentials (for backward compat)
    2. REDIS_PASSWORD + base REDIS_URL (preferred for K8s + local parity)
    3. Plain REDIS_URL with no auth (local dev default)
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_password = os.getenv("REDIS_PASSWORD", "").strip()

    if redis_password and "://" in redis_url:
        # Inject password: redis://localhost:6379 -> redis://:password@localhost:6379
        if "@" not in redis_url:
            scheme, rest = redis_url.split("://", 1)
            redis_url = f"{scheme}://:{redis_password}@{rest}"

    return redis_url


# Threat store (Redis or in-memory fallback)
threat_store: Optional[ThreatStore] = None
intel_cache = None  # Intel feed cache for VT enrichment
websocket_clients: List[WebSocket] = []


class TriggerRequest(BaseModel):
    """Request model for manual threat trigger."""
    threat_type: Optional[str] = None
    scenario: Optional[str] = None
    # Adversarial demo support
    adversarial_scenario: Optional[str] = None  # "note_poisoning_bypass", "note_poisoning_catch", etc.
    adversarial_detector_enabled: Optional[bool] = None  # Override detector state


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global threat_store, intel_cache

    logger.info("🚀 SOC Agent System starting up...")
    use_mock = settings.should_use_mock()
    if settings.force_mock_mode.lower() in ("1", "true"):
        logger.info("   Mode: MOCK (forced via FORCE_MOCK_MODE)")
    else:
        logger.info(f"   Mode: {'MOCK (no OpenAI API)' if use_mock else 'LIVE (OpenAI API enabled)'}")
    logger.info(f"   Host: {settings.host}:{settings.port}")
    logger.info(f"   CORS Origins: {settings.cors_origins}")

    # Initialize OpenTelemetry
    logger.info("   Initializing OpenTelemetry...")
    init_telemetry()

    # Initialize threat store (Redis or in-memory fallback)
    # Use build_redis_url() to inject REDIS_PASSWORD from env (Tier 1F)
    redis_url = build_redis_url()
    # Mask password in logs: redis://:pass@host -> redis://***@host
    if "@" in redis_url:
        scheme_and_auth, host_part = redis_url.split("@", 1)
        masked_url = f"{scheme_and_auth.split(':')[0]}://***@{host_part}"
    else:
        masked_url = redis_url
    logger.info(f"   Initializing threat store (Redis URL: {masked_url})...")
    threat_store = await create_store(redis_url, settings.max_stored_threats)
    set_store(threat_store)

    # Initialize intel cache for VT enrichment (Wave 5)
    logger.info("   Initializing intel cache for threat intelligence...")
    from intel_cache import IntelFeedCache
    intel_cache = IntelFeedCache()  # Uses REDIS_HOST/REDIS_PORT from env

    # Seed demo data if in DEMO_MODE
    import os
    if os.getenv("DEMO_MODE", "false").lower() == "true":
        logger.info("   Seeding demo intel data (DEMO_MODE=true)...")
        await intel_cache.seed_demo_cache()

    # Initialize coordinator for health checks
    logger.info("   Initializing coordinator for health checks...")
    coordinator = create_coordinator(
        use_mock=settings.should_use_mock(),
        intel_cache=intel_cache
    )
    set_coordinator(coordinator)

    # Startup: Conditionally start background threat generation
    task = None
    if settings.enable_auto_threat_generation:
        logger.info("   Starting background threat generator...")
        task = asyncio.create_task(background_threat_generator())
    else:
        logger.info("   Background threat generation disabled (use demo/test scripts or /api/threats/trigger)")

    logger.info("✅ SOC Agent System ready!\n")

    yield

    # Shutdown: Cancel background task and close store
    logger.info("🛑 SOC Agent System shutting down...")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if threat_store:
        await threat_store.close()

    # Intel cache uses Redis connection pool - no explicit close needed

    logger.info("✅ Shutdown complete")


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

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app)

# Initialize Prometheus metrics
instrumentator = create_instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)


async def background_threat_generator():
    """Generate threats periodically in the background."""
    coordinator = create_coordinator(
        use_mock=settings.should_use_mock(),
        intel_cache=intel_cache
    )

    while True:
        try:
            await asyncio.sleep(settings.threat_generation_interval)

            # Generate and analyze threat
            signal = threat_generator.generate_random_threat()
            analysis = await coordinator.analyze_threat(signal)

            # Store threat (this also publishes to Redis Pub/Sub if using RedisStore)
            await threat_store.save_threat(analysis)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Background generator error", exc_info=True, extra={"error": str(e)})
            await asyncio.sleep(5)


@app.get("/")
async def root():
    """Root endpoint - basic service info."""
    return {
        "service": "SOC Agent System",
        "version": "2.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "api": "/api/threats"
        }
    }


@app.get("/health")
async def health():
    """
    Liveness probe endpoint for Kubernetes.

    Returns 200 if the process is running. This is a fast check (<5ms)
    that doesn't verify component initialization.

    Used for: Kubernetes liveness probe
    """
    return check_liveness()


@app.get("/ready")
async def ready():
    """
    Readiness probe endpoint for Kubernetes.

    Returns 200 only when all components are initialized and ready to accept traffic.
    Checks: coordinator, all 5 agents, all 3 analyzers.

    Returns 503 during startup or if any component is not ready.

    Used for: Kubernetes readiness probe
    """
    response, status_code = check_readiness()
    if status_code != 200:
        from fastapi import Response
        return Response(
            content=json.dumps(response),
            status_code=status_code,
            media_type="application/json"
        )
    return response


@app.get("/api/threats", response_model=List[ThreatAnalysis])
async def get_threats(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get paginated list of recent threats."""
    return await threat_store.get_threats(limit=limit, offset=offset)


@app.get("/api/threats/{threat_id}", response_model=ThreatAnalysis)
async def get_threat(threat_id: str):
    """Get specific threat analysis by ID."""
    threat = await threat_store.get_threat(threat_id)
    if threat is None:
        raise HTTPException(status_code=404, detail="Threat not found")
    return threat


@app.get("/api/analytics", response_model=DashboardMetrics)
async def get_analytics():
    """Get dashboard analytics metrics."""
    # Get total count of all threats ever generated
    total_count = await threat_store.get_total_count()

    # Get stored threats for analytics (latest 100)
    threats = await threat_store.get_threats(limit=settings.max_stored_threats)

    if not threats:
        return DashboardMetrics(
            total_threats=total_count,  # Use total count, not stored count
            customers_affected=0,
            average_processing_time_ms=0,
            threats_requiring_review=0,
            threats_by_type={},
            threats_by_severity={}
        )

    # Calculate metrics from stored threats
    customers = set(t.signal.customer_name for t in threats)
    avg_time = sum(t.total_processing_time_ms for t in threats) // len(threats)
    review_count = sum(1 for t in threats if t.requires_human_review)

    # Count by type
    by_type: Dict[str, int] = {}
    for t in threats:
        type_name = t.signal.threat_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1

    # Count by severity
    by_severity: Dict[str, int] = {}
    for t in threats:
        sev = t.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return DashboardMetrics(
        total_threats=total_count,  # Total ever generated, not just stored
        customers_affected=len(customers),
        average_processing_time_ms=avg_time,
        threats_requiring_review=review_count,
        threats_by_type=by_type,
        threats_by_severity=by_severity
    )


@app.post("/api/threats/trigger", response_model=ThreatAnalysis)
async def trigger_threat(request: TriggerRequest):
    """Manually trigger a threat for demo purposes."""
    # Handle adversarial scenarios
    if request.adversarial_scenario:
        from red_team.adversarial_injector import AdversarialInjector

        injector = AdversarialInjector()

        # Determine detector state
        detector_enabled = request.adversarial_detector_enabled if request.adversarial_detector_enabled is not None else True

        # Create coordinator with detector state
        coordinator = create_coordinator(
            use_mock=settings.should_use_mock(),
            intel_cache=intel_cache,
            adversarial_detector_enabled=detector_enabled
        )

        # Generate adversarial attack based on scenario
        if request.adversarial_scenario == "note_poisoning_bypass":
            # ACT 1: Detector disabled
            attack_data = injector.inject_historical_note_poisoning_attack(
                customer_name="DEMO_NotePoisonCorp_ACT1",
                threat_type=ThreatType.ANOMALY_DETECTION
            )
            signal = attack_data["signal"]
            historical_context = attack_data["historical_context"]
            analysis = await coordinator.analyze_threat(signal, historical_context_override=historical_context)

        elif request.adversarial_scenario == "note_poisoning_catch":
            # ACT 2: Detector enabled
            attack_data = injector.inject_historical_note_poisoning_attack(
                customer_name="DEMO_NotePoisonCorp_ACT2",
                threat_type=ThreatType.ANOMALY_DETECTION
            )
            signal = attack_data["signal"]
            historical_context = attack_data["historical_context"]
            analysis = await coordinator.analyze_threat(signal, historical_context_override=historical_context)

        elif request.adversarial_scenario == "note_poisoning_baseline":
            # BASELINE: Clean signal
            attack_data = injector.inject_historical_clean_data(
                customer_name="DEMO_CleanCorp_BASELINE",
                threat_type=ThreatType.ANOMALY_DETECTION
            )
            signal = attack_data["signal"]
            # Clean data doesn't need historical context override - use normal flow
            analysis = await coordinator.analyze_threat(signal)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown adversarial scenario: {request.adversarial_scenario}")

        # Store (this also publishes to Redis Pub/Sub if using RedisStore)
        await threat_store.save_threat(analysis)

        return analysis

    # Normal threat generation (existing logic)
    coordinator = create_coordinator(
        use_mock=settings.should_use_mock(),
        intel_cache=intel_cache
    )

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

    # Store (this also publishes to Redis Pub/Sub if using RedisStore)
    await threat_store.save_threat(analysis)

    return analysis


@app.post("/api/threats/ingest/wazuh", status_code=202)
async def ingest_wazuh_alert(alert: Dict):
    """
    Ingest external Wazuh alerts for analysis.

    Wave 1: Supports rule.id=100006 (Android malicious app install).
    Wave 3: Supports Shuffle-wrapped format (extracts from all_fields).
    Returns 202 Accepted with the normalized ThreatSignal.
    """
    try:
        # Extract raw Wazuh alert from Shuffle wrapper if present
        # Shuffle wraps alerts in: {"severity": ..., "all_fields": {<raw alert>}}
        if "all_fields" in alert:
            wazuh_alert = alert["all_fields"]
        else:
            wazuh_alert = alert  # Direct format (backward compatibility)

        # Translate Wazuh alert to ThreatSignal
        signal = translate_wazuh_alert(wazuh_alert)

        # Analyze threat using coordinator
        coordinator = create_coordinator(
            use_mock=settings.should_use_mock(),
            intel_cache=intel_cache
        )
        analysis = await coordinator.analyze_threat(signal)

        # Store (this also publishes to Redis Pub/Sub if using RedisStore)
        await threat_store.save_threat(analysis)

        # Return the normalized signal (not full analysis) per Wave 1 spec
        return json.loads(signal.model_dump_json())

    except InvalidWazuhAlertError as e:
        raise HTTPException(status_code=422, detail=e.to_detail())
    except UnsupportedWazuhAlertError as e:
        raise HTTPException(status_code=422, detail=e.to_detail())
    except WazuhValidationError as e:
        raise HTTPException(status_code=422, detail=e.to_detail())
    except Exception as e:
        logger.error(f"Unexpected error ingesting Wazuh alert: {e}")
        raise HTTPException(status_code=500, detail={"message": "Internal server error processing Wazuh alert"})


@app.post("/api/egress-violations", status_code=202)
async def ingest_egress_violation(violation: EgressViolation):
    """
    Ingest egress violation events from infrastructure telemetry.

    Tier 3A: NetworkPolicy webhook integration.
    Called when K8s audit logs detect blocked egress attempts.
    Feeds into AdversarialDetector for infrastructure vs historical contradiction analysis.

    Args:
        violation: Details of the blocked egress attempt

    Returns:
        202 Accepted
    """
    record_egress_violation(violation)
    logger.info(
        f"[EGRESS_VIOLATION_INGESTED] pod={violation.source_pod} "
        f"dest={violation.attempted_destination} blocked_by={violation.blocked_by}"
    )
    return {"status": "accepted", "timestamp": violation.timestamp}


@app.get("/api/egress-violations")
async def list_egress_violations(
    since: Optional[float] = Query(None, description="Unix timestamp - only return violations after this time"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of violations to return")
):
    """
    List recent egress violations.

    Tier 3A: Used by DevOps/Infrastructure agent and AdversarialDetector.

    Args:
        since: Optional Unix timestamp (default: last hour)
        limit: Max violations to return (default: 100)

    Returns:
        List of egress violations
    """
    violations = get_recent_violations(since_timestamp=since, max_count=limit)
    return {
        "violations": violations,
        "count": len(violations),
        "timestamp": datetime.now().isoformat()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time threat streaming via Redis Pub/Sub."""
    await websocket.accept()
    websocket_clients.append(websocket)

    # Update Prometheus metric for active connections
    soc_active_websocket_connections.set(len(websocket_clients))

    try:
        # Send initial batch
        initial_threats = await threat_store.get_threats(limit=20)
        await websocket.send_json({
            "type": "initial_batch",
            "data": [json.loads(t.model_dump_json()) for t in initial_threats],
            "timestamp": datetime.utcnow().isoformat()
        })

        # Subscribe to Redis Pub/Sub for new threats
        # This works across all pods in Kubernetes
        async def send_threats():
            """Subscribe to threat events and send to WebSocket."""
            async for threat in threat_store.subscribe_threats():
                try:
                    await websocket.send_json({
                        "type": "new_threat",
                        "data": json.loads(threat.model_dump_json()),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Failed to send threat to WebSocket: {e}")
                    break

        # Start threat subscription task
        threat_task = asyncio.create_task(send_threats())

        # Keep connection alive and handle messages
        try:
            while True:
                try:
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30)

                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})

                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await websocket.send_json({"type": "ping"})

        finally:
            # Cancel threat subscription task
            threat_task.cancel()
            try:
                await threat_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)

        # Update Prometheus metric for active connections
        soc_active_websocket_connections.set(len(websocket_clients))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )

