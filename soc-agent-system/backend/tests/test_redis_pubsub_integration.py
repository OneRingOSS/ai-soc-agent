"""
Integration tests for Redis Pub/Sub cross-pod WebSocket broadcasting.

This test suite verifies the critical production behavior:
- Multiple "pods" (simulated) can share state via Redis
- WebSocket clients connected to different pods all receive the same threats
- Redis Pub/Sub correctly broadcasts across all subscribers

These tests require a running Redis instance (docker run -d -p 6379:6379 redis:7-alpine)
and are marked with @pytest.mark.integration to be run separately from unit tests.
"""
import pytest
import asyncio
import sys
sys.path.insert(0, 'src')

from store import RedisStore, create_store
from models import (
    ThreatAnalysis, ThreatSignal, ThreatType, ThreatSeverity, ThreatStatus,
    FalsePositiveScore, ResponsePlan, InvestigationTimeline,
    ResponseAction, ResponseActionType, ResponseUrgency
)
from datetime import datetime, timezone


# Skip all tests in this file if Redis is not available
pytestmark = pytest.mark.integration


def create_test_threat(threat_id: str, customer_name: str = "test-customer",
                       threat_type: ThreatType = ThreatType.BOT_TRAFFIC,
                       description: str = "Test threat") -> ThreatAnalysis:
    """Helper function to create a valid ThreatAnalysis object for testing."""
    signal = ThreatSignal(
        id=threat_id,
        threat_type=threat_type,
        customer_name=customer_name,
        timestamp=datetime.now(timezone.utc),
        metadata={"description": description}
    )

    return ThreatAnalysis(
        id=threat_id,
        signal=signal,
        status=ThreatStatus.COMPLETED,
        severity=ThreatSeverity.HIGH,
        executive_summary=f"Test threat: {description}",
        customer_narrative=f"Test narrative for {customer_name}",
        agent_analyses={},
        false_positive_score=FalsePositiveScore(
            score=0.15,
            confidence=0.85,
            indicators=[],
            recommendation="Investigate"
        ),
        response_plan=ResponsePlan(
            primary_action=ResponseAction(
                action_type=ResponseActionType.MONITOR,
                urgency=ResponseUrgency.URGENT,
                target="test-target",
                reason="Test threat monitoring",
                confidence=0.9
            )
        ),
        investigation_timeline=InvestigationTimeline(
            detection_time=datetime.now(timezone.utc),
            analysis_start_time=datetime.now(timezone.utc),
            analysis_end_time=datetime.now(timezone.utc),
            total_duration_ms=100
        ),
        total_processing_time_ms=100,
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
async def redis_store():
    """Create a Redis store for testing (requires Redis running on localhost:6379)."""
    store = await create_store("redis://localhost:6379", max_threats=100)
    
    # Verify it's actually a RedisStore (not fallback InMemoryStore)
    assert isinstance(store, RedisStore), "Redis must be running for integration tests"
    
    # Clean up any existing test data
    await store.redis.flushdb()
    
    yield store
    
    # Cleanup
    await store.close()


@pytest.fixture
def sample_threat():
    """Create a sample threat for testing."""
    return create_test_threat(
        threat_id="test-threat-123",
        customer_name="test-customer",
        threat_type=ThreatType.BOT_TRAFFIC,
        description="Test bot traffic from suspicious IP"
    )


@pytest.mark.asyncio
async def test_redis_store_save_and_retrieve(redis_store, sample_threat):
    """Test basic Redis store save and retrieve operations."""
    # Save threat
    await redis_store.save_threat(sample_threat)
    
    # Retrieve by ID
    retrieved = await redis_store.get_threat(sample_threat.id)
    
    assert retrieved is not None
    assert retrieved.id == sample_threat.id
    assert retrieved.signal.customer_name == sample_threat.signal.customer_name
    assert retrieved.signal.threat_type == sample_threat.signal.threat_type


@pytest.mark.asyncio
async def test_redis_pubsub_single_subscriber(redis_store, sample_threat):
    """Test that Redis Pub/Sub delivers threats to a single subscriber."""
    received_threats = []
    
    async def subscriber():
        """Subscribe and collect threats."""
        async for threat in redis_store.subscribe_threats():
            received_threats.append(threat)
            if len(received_threats) >= 1:
                break
    
    # Start subscriber task
    subscriber_task = asyncio.create_task(subscriber())
    
    # Wait a bit for subscription to be ready
    await asyncio.sleep(0.1)
    
    # Publish a threat
    await redis_store.save_threat(sample_threat)
    
    # Wait for subscriber to receive it
    await asyncio.wait_for(subscriber_task, timeout=2.0)
    
    # Verify
    assert len(received_threats) == 1
    assert received_threats[0].id == sample_threat.id


@pytest.mark.asyncio
async def test_redis_pubsub_multiple_subscribers_same_pod(redis_store, sample_threat):
    """
    Test that multiple WebSocket clients on the SAME pod receive the threat.
    
    This simulates multiple users connected to the same backend pod.
    """
    received_by_client1 = []
    received_by_client2 = []
    received_by_client3 = []
    
    async def client_subscriber(client_list):
        """Simulate a WebSocket client subscribing to threats."""
        async for threat in redis_store.subscribe_threats():
            client_list.append(threat)
            if len(client_list) >= 1:
                break
    
    # Start 3 WebSocket client subscribers (simulating 3 users on same pod)
    task1 = asyncio.create_task(client_subscriber(received_by_client1))
    task2 = asyncio.create_task(client_subscriber(received_by_client2))
    task3 = asyncio.create_task(client_subscriber(received_by_client3))
    
    # Wait for subscriptions to be ready
    await asyncio.sleep(0.2)
    
    # Trigger a threat (simulating POST /api/threats/trigger)
    await redis_store.save_threat(sample_threat)
    
    # Wait for all clients to receive it
    await asyncio.wait_for(asyncio.gather(task1, task2, task3), timeout=3.0)
    
    # ✅ ALL 3 clients should receive the threat!
    assert len(received_by_client1) == 1
    assert len(received_by_client2) == 1
    assert len(received_by_client3) == 1
    
    assert received_by_client1[0].id == sample_threat.id
    assert received_by_client2[0].id == sample_threat.id
    assert received_by_client3[0].id == sample_threat.id


@pytest.mark.asyncio
async def test_redis_pubsub_cross_pod_broadcasting():
    """
    **CRITICAL INTEGRATION TEST**: Multi-pod WebSocket broadcasting via Redis Pub/Sub.

    This test simulates the exact Kubernetes scenario:
    - 3 backend pods (A, B, C) each with their own Redis connection
    - 3 WebSocket clients connected to different pods:
      * Client 1 → Pod A
      * Client 2 → Pod B
      * Client 3 → Pod C
    - Threat triggered on Pod A
    - ALL 3 clients receive the threat (via Redis Pub/Sub)

    This is the core architectural feature that enables horizontal scaling!

    Equivalent to:
        kubectl scale deployment soc-backend --replicas=3
        # Connect 3 WebSocket clients to different pods
        curl -X POST http://pod-a:8000/api/threats/trigger
        # ALL 3 WebSocket clients receive the threat! ✅
    """
    # Create 3 separate Redis stores (simulating 3 different pods)
    pod_a_store = await create_store("redis://localhost:6379", max_threats=100)
    pod_b_store = await create_store("redis://localhost:6379", max_threats=100)
    pod_c_store = await create_store("redis://localhost:6379", max_threats=100)

    # Verify all are RedisStore instances
    assert isinstance(pod_a_store, RedisStore), "Pod A must use RedisStore"
    assert isinstance(pod_b_store, RedisStore), "Pod B must use RedisStore"
    assert isinstance(pod_c_store, RedisStore), "Pod C must use RedisStore"

    # Clean up any existing data
    await pod_a_store.redis.flushdb()

    # Storage for received threats
    pod_a_client_threats = []
    pod_b_client_threats = []
    pod_c_client_threats = []

    async def websocket_client_on_pod_a():
        """Simulate WebSocket client connected to Pod A."""
        async for threat in pod_a_store.subscribe_threats():
            pod_a_client_threats.append(threat)
            if len(pod_a_client_threats) >= 1:
                break

    async def websocket_client_on_pod_b():
        """Simulate WebSocket client connected to Pod B."""
        async for threat in pod_b_store.subscribe_threats():
            pod_b_client_threats.append(threat)
            if len(pod_b_client_threats) >= 1:
                break

    async def websocket_client_on_pod_c():
        """Simulate WebSocket client connected to Pod C."""
        async for threat in pod_c_store.subscribe_threats():
            pod_c_client_threats.append(threat)
            if len(pod_c_client_threats) >= 1:
                break

    # Start WebSocket clients on all 3 pods
    client_a_task = asyncio.create_task(websocket_client_on_pod_a())
    client_b_task = asyncio.create_task(websocket_client_on_pod_b())
    client_c_task = asyncio.create_task(websocket_client_on_pod_c())

    # Wait for all subscriptions to be ready
    await asyncio.sleep(0.3)

    # Create a threat using helper
    threat = create_test_threat(
        threat_id="cross-pod-test-threat",
        customer_name="test-customer",
        threat_type=ThreatType.RATE_LIMIT_BREACH,
        description="Cross-pod broadcast test threat"
    )

    # 🚨 Trigger threat on Pod A (simulating: curl -X POST http://pod-a:8000/api/threats/trigger)
    print("\n🚨 Triggering threat on Pod A...")
    await pod_a_store.save_threat(threat)

    # Wait for all clients to receive the threat
    print("⏳ Waiting for all WebSocket clients to receive the threat...")
    await asyncio.wait_for(
        asyncio.gather(client_a_task, client_b_task, client_c_task),
        timeout=5.0
    )

    # ✅ VERIFY: ALL 3 clients received the threat!
    print("\n✅ Verifying cross-pod broadcasting...")

    assert len(pod_a_client_threats) == 1, "Client on Pod A should receive the threat"
    assert len(pod_b_client_threats) == 1, "Client on Pod B should receive the threat (via Redis Pub/Sub)"
    assert len(pod_c_client_threats) == 1, "Client on Pod C should receive the threat (via Redis Pub/Sub)"

    # Verify all received the same threat
    assert pod_a_client_threats[0].id == threat.id
    assert pod_b_client_threats[0].id == threat.id
    assert pod_c_client_threats[0].id == threat.id

    # Verify threat details match
    assert pod_a_client_threats[0].signal.customer_name == "test-customer"
    assert pod_b_client_threats[0].signal.customer_name == "test-customer"
    assert pod_c_client_threats[0].signal.customer_name == "test-customer"

    assert pod_a_client_threats[0].signal.threat_type == ThreatType.RATE_LIMIT_BREACH
    assert pod_b_client_threats[0].signal.threat_type == ThreatType.RATE_LIMIT_BREACH
    assert pod_c_client_threats[0].signal.threat_type == ThreatType.RATE_LIMIT_BREACH

    print("✅ SUCCESS: All 3 WebSocket clients (on different pods) received the threat!")
    print(f"   - Client on Pod A: {pod_a_client_threats[0].id}")
    print(f"   - Client on Pod B: {pod_b_client_threats[0].id}")
    print(f"   - Client on Pod C: {pod_c_client_threats[0].id}")

    # Cleanup
    await pod_a_store.close()
    await pod_b_store.close()
    await pod_c_store.close()


@pytest.mark.asyncio
async def test_redis_pubsub_multiple_threats_ordering(redis_store):
    """Test that multiple threats are received in order via Pub/Sub."""
    received_threats = []

    async def subscriber():
        """Subscribe and collect threats."""
        async for threat in redis_store.subscribe_threats():
            received_threats.append(threat)
            if len(received_threats) >= 3:
                break

    # Start subscriber
    subscriber_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)

    # Publish 3 threats
    for i in range(3):
        threat = create_test_threat(
            threat_id=f"threat-{i}",
            customer_name="test-customer",
            threat_type=ThreatType.BOT_TRAFFIC,
            description=f"Test threat {i}"
        )
        await redis_store.save_threat(threat)
        await asyncio.sleep(0.05)  # Small delay between threats

    # Wait for all threats to be received
    await asyncio.wait_for(subscriber_task, timeout=3.0)

    # Verify all 3 received
    assert len(received_threats) == 3
    assert received_threats[0].id == "threat-0"
    assert received_threats[1].id == "threat-1"
    assert received_threats[2].id == "threat-2"

