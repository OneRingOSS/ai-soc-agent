"""
Intel Feed Cache - Redis-backed caching for threat intelligence lookups.

Provides:
- DEMO_MODE support with pre-seeded results
- Redis caching with configurable TTL
- Background task initialization
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from redis import Redis

logger = logging.getLogger(__name__)

# Demo mode pre-seeded results (used when DEMO_MODE=true)
#
# TO UPDATE WITH REAL VIRUSTOTAL HASHES:
# 1. Go to https://www.virustotal.com
# 2. Search for the package name (e.g., "android:com.kingroot.kinguser")
# 3. Copy the SHA256 hash from the file details
# 4. Update the "ioc_value" field below
# 5. Update the "description" with the actual detection ratio
#
DEMO_INTEL_RESULTS = {
    "com.kingroot.kinguser": {
        "ioc_type": "hash",
        "ioc_value": "b08ee107d349652bb39fb79d503b8e0cfd7b02e1ab891d7c7c25c6357829e5d8",  # Real Android malware hash
        "source": "virustotal",
        "description": "Malicious Android APK — KingRoot grants unauthorized root access",
        "date_added": "",
        "confidence": 0.91,
        "threat_actor": None
    },
    "com.noshufou.android.su": {
        "ioc_type": "hash",
        "ioc_value": "070640095c935c245f960e4e2e3e93720dd57465c81fa9c72426ee008c627bf3",  # Real Android malware hash
        "source": "virustotal",
        "description": "Malicious Android APK — Superuser grants root privileges",
        "date_added": "",
        "confidence": 0.75,
        "threat_actor": None
    },
    "com.koushikdutta.superuser": {
        "ioc_type": "hash",
        "ioc_value": "8bbe1c0aa307a0c689d0b97ea5123f6d74d42bb9f91cbeaac2583b23de3a77ab",  # Real APK hash (SHA-256)
        "source": "virustotal",
        "description": "Malicious Android APK — Superuser/root access tool (ClockworkMod)",
        "date_added": "",
        "confidence": 0.88,
        "threat_actor": None
    },
    "com.zhiqupk.root.global": {
        "ioc_type": "hash",
        "ioc_value": "PLACEHOLDER_HASH_UPDATE_FROM_VIRUSTOTAL_SEARCH",  # TODO: Get real hash from VT
        "source": "virustotal",
        "description": "Malicious Android APK — ZhiQu Root contains malicious payload",
        "date_added": "",
        "confidence": 0.94,
        "threat_actor": None
    }
}


class IntelFeedCache:
    """Redis-backed cache for threat intelligence feed results."""
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize intel feed cache.

        Args:
            redis_client: Optional Redis client. If None, creates new connection.
        """
        if redis_client is None:
            # Try REDIS_URL first (K8s ConfigMap), then fall back to REDIS_HOST/PORT
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                # Parse redis://host:port format
                import re
                match = re.match(r'redis://([^:]+):(\d+)', redis_url)
                if match:
                    redis_host = match.group(1)
                    redis_port = int(match.group(2))
                else:
                    redis_host = "localhost"
                    redis_port = 6379
            else:
                redis_host = os.getenv("REDIS_HOST", "localhost")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))

            self.redis = Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True
            )
        else:
            self.redis = redis_client
        
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        
        # TTL: 24h for demo (static data), 1h for live (fresh data)
        self.cache_ttl = 86400 if self.demo_mode else 3600
        
        logger.info(
            f"Intel cache initialized | demo_mode={self.demo_mode} | "
            f"ttl={self.cache_ttl}s | redis={self.redis.ping()}"
        )
    
    async def seed_demo_cache(self) -> None:
        """
        Seed Redis cache with pre-configured demo results.
        
        Only runs when DEMO_MODE=true. Pre-loads known malicious packages
        so demos don't require live VT API calls.
        """
        if not self.demo_mode:
            logger.info("Intel cache: skipping demo seed (DEMO_MODE=false)")
            return
        
        logger.info("Intel cache: seeding demo data...")
        
        seeded_count = 0
        for package_name, intel_data in DEMO_INTEL_RESULTS.items():
            cache_key = f"vt:pkg:{package_name}"
            
            # Skip if hash not configured yet (placeholder)
            if "PLACEHOLDER" in intel_data["ioc_value"] or "FILL_IN" in intel_data["ioc_value"]:
                logger.warning(
                    f"Intel cache: skipping '{package_name}' — hash not configured "
                    f"(ioc_value contains placeholder)"
                )
                continue
            
            # Store in Redis with TTL
            self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(intel_data)
            )
            
            seeded_count += 1
            logger.debug(f"Intel cache: seeded '{package_name}' | ttl={self.cache_ttl}s")
        
        logger.info(
            f"Intel cache: demo seed complete — {seeded_count}/{len(DEMO_INTEL_RESULTS)} "
            f"packages pre-loaded"
        )
    
    async def start_background_tasks(self) -> None:
        """
        Start background tasks for cache management.
        
        In DEMO_MODE: Seeds cache with pre-configured results.
        In live mode: No-op (cache populated on-demand).
        """
        if self.demo_mode:
            await self.seed_demo_cache()
        else:
            logger.info("Intel cache: live mode — cache will be populated on-demand")
    
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached intel result.
        
        Args:
            cache_key: Redis key (e.g., "vt:pkg:com.example.app")
        
        Returns:
            Cached intel data dict, or None if not found
        """
        try:
            cached = self.redis.get(cache_key)
            if cached:
                logger.debug(f"Intel cache: HIT — {cache_key}")
                return json.loads(cached)
            else:
                logger.debug(f"Intel cache: MISS — {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Intel cache: error reading '{cache_key}' — {e}")
            return None
    
    async def set(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Store intel result in cache.
        
        Args:
            cache_key: Redis key (e.g., "vt:pkg:com.example.app")
            data: Intel data dict to cache
        """
        try:
            self.redis.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data)
            )
            logger.debug(f"Intel cache: SET — {cache_key} | ttl={self.cache_ttl}s")
        except Exception as e:
            logger.error(f"Intel cache: error writing '{cache_key}' — {e}")

