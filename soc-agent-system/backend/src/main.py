"""FastAPI application for SOC Agent System."""
import asyncio
import json
import logging
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
from logger import setup_json_logging, get_logger
from telemetry import init_telemetry, instrument_fastapi
from metrics import create_instrumentator, soc_active_websocket_connections
from health import check_liveness, check_readiness, set_coordinator, set_store
from store import create_store, ThreatStore

# Configure structured JSON logging
setup_json_logging("INFO")

logger = get_logger(__name__)


# Threat store (Redis or in-memory fallback)
threat_store: Optional[ThreatStore] = None
websocket_clients: List[WebSocket] = []


class TriggerRequest(BaseModel):
    """Request model for manual threat trigger."""
    threat_type: Optional[str] = None
    scenario: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global threat_store

    logger.info("🚀 SOC Agent System starting up...")
    use_mock = settings.should_use_mock()
    if settings.force_mock_mode.lower() in ("1", "true"):
        logger.info(f"   Mode: MOCK (forced via FORCE_MOCK_MODE)")
    else:
        logger.info(f"   Mode: {'MOCK (no OpenAI API)' if use_mock else 'LIVE (OpenAI API enabled)'}")
    logger.info(f"   Host: {settings.host}:{settings.port}")
    logger.info(f"   CORS Origins: {settings.cors_origins}")

    # Initialize OpenTelemetry
    logger.info("   Initializing OpenTelemetry...")
    init_telemetry()

    # Initialize threat store (Redis or in-memory fallback)
    logger.info(f"   Initializing threat store (Redis URL: {settings.redis_url})...")
    threat_store = await create_store(settings.redis_url, settings.max_stored_threats)
    set_store(threat_store)

    # Initialize coordinator for health checks
    logger.info("   Initializing coordinator for health checks...")
    coordinator = create_coordinator(use_mock=settings.should_use_mock())
    set_coordinator(coordinator)

    # Startup: Start background threat generation
    logger.info("   Starting background threat generator...")
    task = asyncio.create_task(background_threat_generator())

    logger.info("✅ SOC Agent System ready!\n")

    yield

    # Shutdown: Cancel background task and close store
    logger.info("🛑 SOC Agent System shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    if threat_store:
        await threat_store.close()

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
    coordinator = create_coordinator(use_mock=settings.should_use_mock())

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
    coordinator = create_coordinator(use_mock=settings.should_use_mock())

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

