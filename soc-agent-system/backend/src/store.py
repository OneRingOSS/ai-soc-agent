"""Threat storage abstraction with Redis and in-memory implementations."""
import json
import asyncio
import logging
from typing import Optional, List, AsyncGenerator
from abc import ABC, abstractmethod

from models import ThreatAnalysis

logger = logging.getLogger(__name__)


class ThreatStore(ABC):
    """Abstract base class for threat storage."""

    @abstractmethod
    async def save_threat(self, threat: ThreatAnalysis) -> None:
        """Save a threat analysis."""
        pass

    @abstractmethod
    async def get_threat(self, threat_id: str) -> Optional[ThreatAnalysis]:
        """Get a specific threat by ID."""
        pass

    @abstractmethod
    async def get_threats(self, limit: int = 100, offset: int = 0) -> List[ThreatAnalysis]:
        """Get paginated list of threats."""
        pass

    @abstractmethod
    async def get_total_count(self) -> int:
        """Get total count of all threats ever generated (not just stored)."""
        pass

    @abstractmethod
    async def subscribe_threats(self) -> AsyncGenerator[ThreatAnalysis, None]:
        """Subscribe to new threat events (for WebSocket broadcasting)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connections and cleanup."""
        pass


class InMemoryStore(ThreatStore):
    """In-memory threat storage (fallback when Redis unavailable)."""

    def __init__(self, max_threats: int = 100):
        """Initialize in-memory store."""
        self.threats: List[ThreatAnalysis] = []
        self.max_threats = max_threats
        self.total_count = 0  # Track total threats ever generated
        self.subscribers: List[asyncio.Queue] = []
        logger.warning("⚠️  Using in-memory store. Multi-replica consistency will NOT be guaranteed.")

    async def save_threat(self, threat: ThreatAnalysis) -> None:
        """Save threat to memory and notify subscribers."""
        self.total_count += 1  # Increment total count
        self.threats.insert(0, threat)
        if len(self.threats) > self.max_threats:
            self.threats.pop()

        # Notify all subscribers
        for queue in self.subscribers:
            try:
                await queue.put(threat)
            except Exception as e:
                logger.error(f"Failed to notify subscriber: {e}")

    async def get_threat(self, threat_id: str) -> Optional[ThreatAnalysis]:
        """Get threat by ID."""
        for threat in self.threats:
            if threat.id == threat_id:
                return threat
        return None

    async def get_threats(self, limit: int = 100, offset: int = 0) -> List[ThreatAnalysis]:
        """Get paginated threats."""
        return self.threats[offset:offset + limit]

    async def get_total_count(self) -> int:
        """Get total count of all threats ever generated."""
        return self.total_count

    async def subscribe_threats(self) -> AsyncGenerator[ThreatAnalysis, None]:
        """Subscribe to new threats."""
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(queue)

        try:
            while True:
                threat = await queue.get()
                yield threat
        finally:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

    async def close(self) -> None:
        """Cleanup (no-op for in-memory)."""
        pass


class RedisStore(ThreatStore):
    """Redis-backed threat storage for multi-replica Kubernetes deployments."""
    
    def __init__(self, redis_url: str, max_threats: int = 100):
        """Initialize Redis store."""
        self.redis_url = redis_url
        self.max_threats = max_threats
        self.redis = None
        self.pubsub = None
        logger.info(f"✅ Redis store initialized: {redis_url}")
    
    async def _ensure_connected(self):
        """Ensure Redis connection is established."""
        if self.redis is None:
            import redis.asyncio as aioredis
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def save_threat(self, threat: ThreatAnalysis) -> None:
        """Save threat to Redis and publish to Pub/Sub channel."""
        await self._ensure_connected()

        # Increment total count (persisted in Redis)
        await self.redis.incr("threats:total_count")

        # Serialize threat to JSON
        threat_json = threat.model_dump_json()
        threat_id = threat.id
        created_timestamp = threat.created_at.timestamp()

        # Store in Redis hash
        await self.redis.set(f"threat:{threat_id}", threat_json)

        # Add to sorted set (scored by timestamp for ordering)
        await self.redis.zadd("threats:by_created", {threat_id: created_timestamp})

        # Trim sorted set to max_threats (only keep latest 100 for display/storage)
        total = await self.redis.zcard("threats:by_created")
        if total > self.max_threats:
            # Remove oldest threats from storage
            await self.redis.zremrangebyrank("threats:by_created", 0, total - self.max_threats - 1)

        # Publish to Pub/Sub channel for WebSocket broadcasting
        await self.redis.publish("threats:events", threat_json)

    async def get_threat(self, threat_id: str) -> Optional[ThreatAnalysis]:
        """Get threat by ID from Redis."""
        await self._ensure_connected()

        threat_json = await self.redis.get(f"threat:{threat_id}")
        if threat_json is None:
            return None

        return ThreatAnalysis.model_validate_json(threat_json)

    async def get_threats(self, limit: int = 100, offset: int = 0) -> List[ThreatAnalysis]:
        """Get paginated threats from Redis sorted set."""
        await self._ensure_connected()

        # Get threat IDs from sorted set (newest first)
        threat_ids = await self.redis.zrevrange("threats:by_created", offset, offset + limit - 1)

        if not threat_ids:
            return []

        # Fetch all threats in parallel
        pipeline = self.redis.pipeline()
        for threat_id in threat_ids:
            pipeline.get(f"threat:{threat_id}")

        threat_jsons = await pipeline.execute()

        # Parse threats
        threats = []
        for threat_json in threat_jsons:
            if threat_json:
                try:
                    threats.append(ThreatAnalysis.model_validate_json(threat_json))
                except Exception as e:
                    logger.error(f"Failed to parse threat from Redis: {e}")

        return threats

    async def get_total_count(self) -> int:
        """Get total count of all threats ever generated."""
        await self._ensure_connected()

        count = await self.redis.get("threats:total_count")
        return int(count) if count else 0

    async def subscribe_threats(self) -> AsyncGenerator[ThreatAnalysis, None]:
        """Subscribe to Redis Pub/Sub channel for new threats."""
        await self._ensure_connected()

        # Create a new Redis connection for Pub/Sub
        import redis.asyncio as aioredis
        pubsub_redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

        pubsub = pubsub_redis.pubsub()
        await pubsub.subscribe("threats:events")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        threat_json = message["data"]
                        threat = ThreatAnalysis.model_validate_json(threat_json)
                        yield threat
                    except Exception as e:
                        logger.error(f"Failed to parse threat from Pub/Sub: {e}")
        finally:
            await pubsub.unsubscribe("threats:events")
            await pubsub.close()
            await pubsub_redis.close()

    async def close(self) -> None:
        """Close Redis connections."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")


async def create_store(redis_url: str, max_threats: int = 100) -> ThreatStore:
    """
    Create a threat store instance.

    Attempts to connect to Redis. If Redis is unavailable, falls back to in-memory store.

    Args:
        redis_url: Redis connection URL
        max_threats: Maximum number of threats to store

    Returns:
        ThreatStore instance (Redis or in-memory)
    """
    try:
        # Try to create Redis store and test connection
        store = RedisStore(redis_url, max_threats)
        await store._ensure_connected()

        # Test connection with ping
        await store.redis.ping()

        logger.info("✅ Redis connection successful - using RedisStore")
        return store

    except Exception as e:
        logger.warning(f"⚠️  Redis unavailable ({e}), falling back to in-memory store")
        logger.warning("   Multi-replica consistency will NOT be guaranteed")
        return InMemoryStore(max_threats)

