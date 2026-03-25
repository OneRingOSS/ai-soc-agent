"""
Unit tests for IntelEnricher.

Stage 3 Gate: These tests must pass before proceeding to Stage 4.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from src.intel_enricher import IntelEnricher, KNOWN_PACKAGE_HASHES
from src.intel_cache import IntelFeedCache
from src.models import IntelMatch
import httpx


@pytest.fixture
def mock_cache():
    """Create a mock IntelFeedCache."""
    cache = Mock(spec=IntelFeedCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.demo_mode = False
    return cache


@pytest.fixture
def mock_cache_demo_mode():
    """Create a mock IntelFeedCache in demo mode."""
    cache = Mock(spec=IntelFeedCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.demo_mode = True
    return cache


class TestIntelEnricherInit:
    """Test IntelEnricher initialization."""

    def test_init_with_api_key(self, mock_cache):
        """Test initialization with VT API key."""
        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key_123")
        
        assert enricher.cache == mock_cache
        assert enricher.vt_api_key == "test_key_123"
        assert enricher.timeout == 5

    def test_init_without_api_key(self, mock_cache, monkeypatch):
        """Test initialization without VT API key."""
        monkeypatch.delenv("VT_API_KEY", raising=False)
        enricher = IntelEnricher(cache=mock_cache)
        
        assert enricher.vt_api_key == ""

    def test_init_demo_mode(self, mock_cache, monkeypatch):
        """Test initialization in DEMO_MODE."""
        monkeypatch.setenv("DEMO_MODE", "true")
        enricher = IntelEnricher(cache=mock_cache)
        
        assert enricher.demo_mode is True


class TestEnrichNoPackageName:
    """Test enrichment when no package_name in metadata."""

    @pytest.mark.asyncio
    async def test_enrich_no_metadata(self, mock_cache):
        """Test enrichment skips when no metadata."""
        enricher = IntelEnricher(cache=mock_cache)
        signal_data = {}
        
        result = await enricher.enrich(signal_data)
        
        assert result == []
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_enrich_no_package_name(self, mock_cache):
        """Test enrichment skips when no package_name in metadata."""
        enricher = IntelEnricher(cache=mock_cache)
        signal_data = {"metadata": {"other_field": "value"}}
        
        result = await enricher.enrich(signal_data)
        
        assert result == []
        mock_cache.get.assert_not_called()


class TestEnrichUnknownPackage:
    """Test enrichment with unknown package."""

    @pytest.mark.asyncio
    async def test_enrich_unknown_package(self, mock_cache):
        """Test enrichment skips unknown package."""
        enricher = IntelEnricher(cache=mock_cache)
        signal_data = {"metadata": {"package_name": "com.unknown.benign.app"}}
        
        result = await enricher.enrich(signal_data)
        
        assert result == []
        mock_cache.get.assert_not_called()


class TestEnrichUnconfiguredHash:
    """Test enrichment with unconfigured hash (FILL_IN placeholder)."""

    @pytest.mark.asyncio
    async def test_enrich_unconfigured_hash(self, mock_cache):
        """Test enrichment skips package with FILL_IN hash."""
        enricher = IntelEnricher(cache=mock_cache)
        
        # Mock KNOWN_PACKAGE_HASHES with FILL_IN placeholder
        with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "FILL_IN_SHA256_HASH"}):
            signal_data = {"metadata": {"package_name": "com.test.app"}}
            result = await enricher.enrich(signal_data)
        
        assert result == []
        mock_cache.get.assert_not_called()


class TestEnrichCacheHit:
    """Test enrichment with Redis cache hit."""

    @pytest.mark.asyncio
    async def test_enrich_cache_hit_skips_api(self, mock_cache):
        """Test Redis cache hit skips VT API call."""
        cached_data = {
            "ioc_type": "hash",
            "ioc_value": "cached_hash_123",
            "source": "virustotal",
            "description": "Cached result",
            "date_added": "",
            "confidence": 0.85,
            "threat_actor": None
        }
        mock_cache.get = AsyncMock(return_value=cached_data)
        
        enricher = IntelEnricher(cache=mock_cache)
        
        with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
            signal_data = {"metadata": {"package_name": "com.test.app"}}
            result = await enricher.enrich(signal_data)
        
        assert len(result) == 1
        assert result[0].ioc_value == "cached_hash_123"
        assert result[0].confidence == 0.85
        
        # Verify cache was checked
        mock_cache.get.assert_called_once_with("vt:pkg:com.test.app")
        
        # Verify cache was NOT set (already cached)
        mock_cache.set.assert_not_called()


class TestEnrichDemoMode:
    """Test enrichment in DEMO_MODE."""

    @pytest.mark.asyncio
    async def test_enrich_demo_mode_returns_preseeded(self, mock_cache_demo_mode, monkeypatch):
        """Test DEMO_MODE returns pre-seeded result without API call."""
        monkeypatch.setenv("DEMO_MODE", "true")
        
        # Mock pre-seeded cache data
        preseeded_data = {
            "ioc_type": "hash",
            "ioc_value": "demo_hash_abc123",
            "source": "virustotal",
            "description": "28/72 AV engines flagged",
            "date_added": "",
            "confidence": 0.91,
            "threat_actor": None
        }
        mock_cache_demo_mode.get = AsyncMock(return_value=preseeded_data)
        
        enricher = IntelEnricher(cache=mock_cache_demo_mode)
        
        with patch.dict(KNOWN_PACKAGE_HASHES, {"com.kingroot.kinguser": "configured_hash"}):
            signal_data = {"metadata": {"package_name": "com.kingroot.kinguser"}}
            result = await enricher.enrich(signal_data)
        
        assert len(result) == 1
        assert result[0].source == "virustotal"
        assert result[0].confidence == 0.91

        # Verify cache was checked (returns early on cache hit)
        assert mock_cache_demo_mode.get.call_count == 1


class TestVTAPITimeout:
    """Test VT API timeout handling."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_timeout_returns_empty(self, mock_cache, monkeypatch):
        """Test VT API timeout returns empty list gracefully."""
        monkeypatch.setenv("DEMO_MODE", "false")

        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key")

        # Mock httpx to raise timeout
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
                signal_data = {"metadata": {"package_name": "com.test.app"}}
                result = await enricher.enrich(signal_data)

        assert result == []


class TestVTAPI404:
    """Test VT API 404 (hash not found) handling."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_404_returns_empty(self, mock_cache, monkeypatch):
        """Test VT API 404 (hash not found) returns empty list."""
        monkeypatch.setenv("DEMO_MODE", "false")

        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key")

        # Mock httpx to return 404
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
                signal_data = {"metadata": {"package_name": "com.test.app"}}
                result = await enricher.enrich(signal_data)

        assert result == []


class TestVTAPI429:
    """Test VT API 429 (rate limit) handling."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_429_returns_empty(self, mock_cache, monkeypatch):
        """Test VT API 429 (rate limit) returns empty list."""
        monkeypatch.setenv("DEMO_MODE", "false")

        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key")

        # Mock httpx to return 429
        mock_response = Mock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
                signal_data = {"metadata": {"package_name": "com.test.app"}}
                result = await enricher.enrich(signal_data)

        assert result == []


class TestVTAPISuccess:
    """Test successful VT API response."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_success_creates_intel_match(self, mock_cache, monkeypatch):
        """Test successful VT API response creates IntelMatch."""
        monkeypatch.setenv("DEMO_MODE", "false")

        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key")

        # Mock VT API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 28,
                        "suspicious": 3,
                        "undetected": 41,
                        "harmless": 0
                    },
                    "popular_threat_classification": {
                        "suggested_threat_label": "riskware.androidos_root"
                    },
                    "tags": ["android", "root"],
                    "first_submission_date": 1640000000
                }
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
                signal_data = {"metadata": {"package_name": "com.test.app"}}
                result = await enricher.enrich(signal_data)

        assert len(result) == 1
        assert result[0].source == "virustotal"
        assert result[0].ioc_type == "hash"
        assert result[0].ioc_value == "abc123def456"
        assert "28/" in result[0].description
        assert "riskware.androidos_root" in result[0].description
        assert result[0].confidence > 0.3  # 28/72 = ~0.41 confidence

        # Verify result was cached
        mock_cache.set.assert_called_once()


class TestVTAPINoDetections:
    """Test VT API with zero detections."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_no_detections_returns_empty(self, mock_cache, monkeypatch):
        """Test VT API with 0 detections returns empty list."""
        monkeypatch.setenv("DEMO_MODE", "false")

        enricher = IntelEnricher(cache=mock_cache, vt_api_key="test_key")

        # Mock VT API response with 0 detections
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "attributes": {
                    "last_analysis_stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 72,
                        "harmless": 0
                    }
                }
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
                signal_data = {"metadata": {"package_name": "com.test.app"}}
                result = await enricher.enrich(signal_data)

        assert result == []

        # Verify result was NOT cached (no match)
        mock_cache.set.assert_not_called()


class TestVTAPINoAPIKey:
    """Test VT API call without API key."""

    @pytest.mark.asyncio
    async def test_enrich_vt_api_no_key_returns_empty(self, mock_cache, monkeypatch):
        """Test VT API call without API key returns empty list."""
        monkeypatch.setenv("DEMO_MODE", "false")
        monkeypatch.delenv("VT_API_KEY", raising=False)

        enricher = IntelEnricher(cache=mock_cache)  # No API key

        with patch.dict(KNOWN_PACKAGE_HASHES, {"com.test.app": "abc123def456"}):
            signal_data = {"metadata": {"package_name": "com.test.app"}}
            result = await enricher.enrich(signal_data)

        assert result == []

