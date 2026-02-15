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
from logging_config import demo_mode_minimal
from telemetry import init_telemetry, instrument_fastapi

# Configure logging for demo
demo_mode_minimal()  # Use demo_mode_detailed() for more verbose output

logger = logging.getLogger(__name__)


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
    logger.info("🚀 SOC Agent System starting up...")
    logger.info(f"   Mode: {'MOCK (no OpenAI API)' if not settings.openai_api_key else 'LIVE (OpenAI API enabled)'}")
    logger.info(f"   Host: {settings.host}:{settings.port}")
    logger.info(f"   CORS Origins: {settings.cors_origins}")

    # Initialize OpenTelemetry
    logger.info("   Initializing OpenTelemetry...")
    init_telemetry()

    # Startup: Start background threat generation
    logger.info("   Starting background threat generator...")
    task = asyncio.create_task(background_threat_generator())

    logger.info("✅ SOC Agent System ready!\n")

    yield

    # Shutdown: Cancel background task
    logger.info("🛑 SOC Agent System shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
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
        reload=settings.debug
    )

