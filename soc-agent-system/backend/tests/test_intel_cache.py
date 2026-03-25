"""
Unit tests for IntelFeedCache.

Stage 2 Gate: These tests must pass before proceeding to Stage 3.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.intel_cache import IntelFeedCache, DEMO_INTEL_RESULTS


class TestIntelFeedCache:
    """Test IntelFeedCache initialization and configuration."""

    def test_init_with_provided_redis_client(self):
        """Test initialization with provided Redis client."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        
        cache = IntelFeedCache(redis_client=mock_redis)
        
        assert cache.redis == mock_redis
        assert mock_redis.ping.called

    def test_init_demo_mode_true(self, monkeypatch):
        """Test initialization in DEMO_MODE=true."""
        monkeypatch.setenv("DEMO_MODE", "true")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        
        cache = IntelFeedCache(redis_client=mock_redis)
        
        assert cache.demo_mode is True
        assert cache.cache_ttl == 86400  # 24 hours

    def test_init_demo_mode_false(self, monkeypatch):
        """Test initialization in DEMO_MODE=false (live mode)."""
        monkeypatch.setenv("DEMO_MODE", "false")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        
        cache = IntelFeedCache(redis_client=mock_redis)
        
        assert cache.demo_mode is False
        assert cache.cache_ttl == 3600  # 1 hour


class TestSeedDemoCache:
    """Test demo cache seeding functionality."""

    @pytest.mark.asyncio
    async def test_seed_demo_cache_in_demo_mode(self, monkeypatch):
        """Test seeding demo cache with pre-configured results."""
        monkeypatch.setenv("DEMO_MODE", "true")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.setex = Mock()
        
        # Mock DEMO_INTEL_RESULTS with configured hashes
        test_results = {
            "com.test.app1": {
                "ioc_type": "hash",
                "ioc_value": "abc123def456",  # Configured hash
                "source": "virustotal",
                "description": "Test malware",
                "confidence": 0.9
            },
            "com.test.app2": {
                "ioc_type": "hash",
                "ioc_value": "FILL_IN_SHA256_HASH",  # Not configured
                "source": "virustotal",
                "description": "Test malware 2",
                "confidence": 0.8
            }
        }
        
        with patch("src.intel_cache.DEMO_INTEL_RESULTS", test_results):
            cache = IntelFeedCache(redis_client=mock_redis)
            await cache.seed_demo_cache()
        
        # Should only seed app1 (app2 has FILL_IN placeholder)
        assert mock_redis.setex.call_count == 1
        
        # Verify the call
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "vt:pkg:com.test.app1"
        assert call_args[1] == 86400  # TTL
        
        # Verify JSON data
        stored_data = json.loads(call_args[2])
        assert stored_data["ioc_value"] == "abc123def456"

    @pytest.mark.asyncio
    async def test_seed_demo_cache_skips_in_live_mode(self, monkeypatch):
        """Test demo cache seeding is skipped in live mode."""
        monkeypatch.setenv("DEMO_MODE", "false")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.setex = Mock()
        
        cache = IntelFeedCache(redis_client=mock_redis)
        await cache.seed_demo_cache()
        
        # Should not seed anything in live mode
        assert mock_redis.setex.call_count == 0


class TestBackgroundTasks:
    """Test background task initialization."""

    @pytest.mark.asyncio
    async def test_start_background_tasks_demo_mode(self, monkeypatch):
        """Test background tasks start in DEMO_MODE."""
        monkeypatch.setenv("DEMO_MODE", "true")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.setex = Mock()
        
        # Mock with one configured package
        test_results = {
            "com.test.app": {
                "ioc_type": "hash",
                "ioc_value": "configured_hash",
                "source": "virustotal",
                "description": "Test",
                "confidence": 0.9
            }
        }
        
        with patch("src.intel_cache.DEMO_INTEL_RESULTS", test_results):
            cache = IntelFeedCache(redis_client=mock_redis)
            await cache.start_background_tasks()
        
        # Verify seed was called
        assert mock_redis.setex.call_count == 1

    @pytest.mark.asyncio
    async def test_start_background_tasks_live_mode(self, monkeypatch):
        """Test background tasks skip seeding in live mode."""
        monkeypatch.setenv("DEMO_MODE", "false")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.setex = Mock()
        
        cache = IntelFeedCache(redis_client=mock_redis)
        await cache.start_background_tasks()
        
        # Verify seed was NOT called
        assert mock_redis.setex.call_count == 0


class TestCacheOperations:
    """Test cache get/set operations."""

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Test getting cached value (cache hit)."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        
        test_data = {
            "ioc_type": "hash",
            "ioc_value": "test_hash",
            "source": "virustotal",
            "description": "Cached result",
            "confidence": 0.85
        }
        mock_redis.get.return_value = json.dumps(test_data)
        
        cache = IntelFeedCache(redis_client=mock_redis)
        result = await cache.get("vt:pkg:com.test.app")
        
        assert result is not None
        assert result["ioc_value"] == "test_hash"
        assert result["confidence"] == 0.85
        mock_redis.get.assert_called_once_with("vt:pkg:com.test.app")

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Test getting non-existent value (cache miss)."""
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        
        cache = IntelFeedCache(redis_client=mock_redis)
        result = await cache.get("vt:pkg:com.unknown.app")
        
        assert result is None
        mock_redis.get.assert_called_once_with("vt:pkg:com.unknown.app")

    @pytest.mark.asyncio
    async def test_set_cache(self, monkeypatch):
        """Test setting cache value."""
        monkeypatch.setenv("DEMO_MODE", "false")
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.setex = Mock()
        
        cache = IntelFeedCache(redis_client=mock_redis)
        
        test_data = {
            "ioc_type": "hash",
            "ioc_value": "new_hash",
            "source": "virustotal",
            "description": "New result",
            "confidence": 0.9
        }
        
        await cache.set("vt:pkg:com.new.app", test_data)
        
        # Verify setex was called with correct parameters
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "vt:pkg:com.new.app"
        assert call_args[1] == 3600  # Live mode TTL
        
        stored_data = json.loads(call_args[2])
        assert stored_data["ioc_value"] == "new_hash"

