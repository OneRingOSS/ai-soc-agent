"""
Intel Enricher - Enriches threat signals with live threat intelligence.

Provides:
- Package name → SHA256 hash lookup
- VirusTotal API integration (with DEMO_MODE support)
- Redis caching for API results
- Graceful degradation on failures
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from models import IntelMatch
from intel_cache import IntelFeedCache

logger = logging.getLogger(__name__)

# Known package name → SHA256 hash mapping
# Demo hashes (use actual VT hashes in production)
KNOWN_PACKAGE_HASHES = {
    "com.kingroot.kinguser": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
    "com.noshufou.android.su": "b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef1234567",
    "com.zhiqupk.root.global": "c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678",
    "com.battery.fast.charger.free": "d4e5f6789012345678901234567890abcdef1234567890abcdef123456789",
    "sk.madzik.android.logcatudp": "e5f6789012345678901234567890abcdef1234567890abcdef1234567890",
    "com.koushikdutta.superuser": "8bbe1c0aa307a0c689d0b97ea5123f6d74d42bb9f91cbeaac2583b23de3a77ab",
}


class IntelEnricher:
    """Enriches threat signals with live threat intelligence from external feeds."""
    
    def __init__(
        self,
        cache: IntelFeedCache,
        vt_api_key: Optional[str] = None,
        timeout: int = 5
    ):
        """
        Initialize intel enricher.
        
        Args:
            cache: IntelFeedCache instance for caching results
            vt_api_key: VirusTotal API key (optional, not needed in DEMO_MODE)
            timeout: HTTP timeout in seconds (default: 5)
        """
        self.cache = cache
        self.vt_api_key = vt_api_key or os.getenv("VT_API_KEY", "")
        self.timeout = timeout
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        
        logger.info(
            f"Intel enricher initialized | demo_mode={self.demo_mode} | "
            f"vt_api_key_configured={bool(self.vt_api_key)} | timeout={timeout}s"
        )
    
    async def enrich(self, signal_data: Dict[str, Any]) -> List[IntelMatch]:
        """
        Enrich threat signal with intel matches.
        
        Args:
            signal_data: ThreatSignal data dict with metadata
        
        Returns:
            List of IntelMatch objects (empty list if no matches or on error)
        """
        # Step 1: Extract package_name from metadata
        metadata = signal_data.get("metadata", {})
        package_name = metadata.get("package_name")
        
        if not package_name:
            logger.debug("VT enrichment: no package_name in metadata — skipping")
            return []
        
        logger.debug(f"VT enrichment: checking package_name={package_name}")
        
        # Step 2: Look up SHA256 hash for package
        sha256_hash = KNOWN_PACKAGE_HASHES.get(package_name)
        
        if not sha256_hash:
            logger.debug(
                f"VT enrichment: '{package_name}' not in known hash table — skipping"
            )
            return []
        
        if "FILL_IN" in sha256_hash:
            logger.warning(
                f"VT enrichment: '{package_name}' hash not configured "
                f"(contains 'FILL_IN') — skipping"
            )
            return []
        
        logger.debug(f"VT enrichment: hash lookup — found=True | hash={sha256_hash[:16]}...")
        
        # Step 3: Check Redis cache
        cache_key = f"vt:pkg:{package_name}"
        cached_result = await self.cache.get(cache_key)
        
        if cached_result:
            logger.debug("VT enrichment: Redis cache HIT — returning cached result")
            return [IntelMatch(**cached_result)]
        
        logger.debug("VT enrichment: Redis cache MISS — checking VirusTotal")
        
        # Step 4: Check VirusTotal (or return demo data)
        intel_match = await self._check_virustotal(package_name, sha256_hash)
        
        if intel_match:
            # Step 5: Cache the result
            await self.cache.set(cache_key, intel_match.model_dump())
            return [intel_match]
        
        return []
    
    async def _check_virustotal(
        self,
        package_name: str,
        sha256_hash: str
    ) -> Optional[IntelMatch]:
        """
        Check VirusTotal for hash analysis.
        
        In DEMO_MODE: Returns pre-seeded data from cache.
        In live mode: Calls VT API.
        
        Args:
            package_name: Android package name
            sha256_hash: SHA256 hash of the APK
        
        Returns:
            IntelMatch if malicious, None otherwise
        """
        # DEMO_MODE: Return pre-seeded data
        if self.demo_mode:
            logger.debug("VT enrichment: DEMO_MODE active — returning pre-seeded result")
            
            # Try to get from cache (should be pre-seeded)
            cache_key = f"vt:pkg:{package_name}"
            cached = await self.cache.get(cache_key)
            
            if cached:
                return IntelMatch(**cached)
            else:
                logger.warning(
                    f"VT enrichment: DEMO_MODE but no pre-seeded data for '{package_name}' "
                    f"— returning None"
                )
                return None
        
        # Live mode: Call VT API
        if not self.vt_api_key:
            logger.warning("VT enrichment: no VT_API_KEY configured — skipping API call")
            return None
        
        logger.debug(f"VT enrichment: calling VT API | hash={sha256_hash[:16]}...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"https://www.virustotal.com/api/v3/files/{sha256_hash}",
                    headers={"x-apikey": self.vt_api_key}
                )
            
            if response.status_code == 404:
                logger.debug("VT enrichment: hash not found in VT (404) — returning None")
                return None
            
            if response.status_code == 429:
                logger.warning("VT enrichment: rate limit exceeded (429) — returning None")
                return None
            
            if response.status_code != 200:
                logger.error(
                    f"VT enrichment: unexpected status {response.status_code} — returning None"
                )
                return None
            
            # Parse VT response
            data = response.json()
            attributes = data.get("data", {}).get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})
            
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            total = sum(stats.values())
            
            # Only return match if flagged by at least one engine
            if malicious + suspicious == 0:
                logger.debug("VT enrichment: 0 detections — returning None")
                return None
            
            # Extract threat label
            threat_label = (
                attributes.get("popular_threat_classification", {})
                .get("suggested_threat_label", "unknown")
            )
            
            # Calculate confidence based on detection ratio
            confidence = min(0.95, (malicious + suspicious * 0.5) / total)
            
            # Get first submission date
            first_seen = attributes.get("first_submission_date", 0)
            date_added = datetime.fromtimestamp(first_seen).isoformat() if first_seen else ""
            
            logger.info(
                f"VT enrichment: match found | detections={malicious}/{total} | "
                f"confidence={confidence:.2f} | label={threat_label}"
            )
            
            return IntelMatch(
                ioc_type="hash",
                ioc_value=sha256_hash,
                source="virustotal",
                description=f"{malicious}/{total} AV engines flagged as '{threat_label}'",
                date_added=date_added,
                confidence=confidence,
                threat_actor=None
            )
        
        except httpx.TimeoutException:
            logger.warning(f"VT enrichment: timeout after {self.timeout}s — returning None")
            return None
        except Exception as e:
            logger.error(f"VT enrichment: error — {e} — returning None")
            return None

