# Feature Spec: Live Threat Intelligence — VirusTotal Package Lookup
### AI SOC Agent System — For Augment Code

**Version:** 1.1
**Date:** March 23, 2026
**Status:** Ready for Implementation
**Depends on:** Wazuh connector (already built)

---

## Table of Contents

1. [Objectives and Design Decisions](#1-objectives-and-design-decisions)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Models](#3-data-models)
4. [Known Package Hash Table](#4-known-package-hash-table)
5. [Pre-Seeded Demo Cache](#5-pre-seeded-demo-cache)
6. [VirusTotal Lookup — IntelEnricher](#6-virustotal-lookup--intelenricher)
7. [Intel Cache Layer](#7-intel-cache-layer)
8. [HistoricalAgent Integration](#8-historicalagent-integration)
9. [CoordinatorAgent Changes](#9-coordinatoragent-changes)
10. [API Changes](#10-api-changes)
11. [Frontend Changes](#11-frontend-changes)
12. [Environment Variables](#12-environment-variables)
13. [File Change Map](#13-file-change-map)
14. [Implementation Steps](#14-implementation-steps)
15. [Testing Checklist](#15-testing-checklist)

---

## 1. Objectives and Design Decisions

**Goal:** When a Wazuh alert contains a known Android package name, the `HistoricalAgent` automatically queries VirusTotal for real AV engine detections and surfaces them as `intel_matches` in `ThreatAnalysis`.

**Key design decisions:**

- **No changes to Wazuh** — package name is already present in `alert.data.package_name`. The connector extracts it into `signal.metadata["package_name"]`.
- **VirusTotal is the sole intel source** — no other external feeds are used.
- **Package → Hash table** — a static `KNOWN_PACKAGE_HASHES` dict inside `intel_enricher.py` maps package names to SHA256 hashes. Pre-seeded with known malicious packages before demo.
- **Timeout-safe with pre-seeded cache** — VirusTotal API calls have a 5-second timeout. If the call times out or fails, a pre-seeded Redis cache is checked first. If cache also misses, returns empty list gracefully. Pipeline never blocks.
- **Demo mode flag** — `DEMO_MODE=true` skips live VT API calls entirely and returns pre-seeded cache data instantly. Eliminates all network risk during live demo.
- **Rich debug logging** — every step of the package → hash → VT → IntelMatch flow has structured `logger.debug()` statements so the full flow is visible in console during demo.
- **Additive only** — `intel_matches` is a new optional field on `ThreatAnalysis` with `= []` default. No existing fields are modified. No existing tests break.

---

## 2. Architecture Overview

```text
WAZUH ALERT ARRIVES
  {
    "rule": {"id": "100006", "description": "Malicious Android app installed: com.kingroot.kinguser"},
    "data": {"package_name": "com.kingroot.kinguser"}
  }
         │
         ▼
WazuhConnector.wazuh_alert_to_threat_signal()
  → extracts alert.data.package_name
  → sets signal.metadata["package_name"] = "com.kingroot.kinguser"
  [DEBUG] "Extracted package_name from Wazuh alert: com.kingroot.kinguser"
         │
         ▼
CoordinatorAgent fans out agents (existing flow, unchanged)
  HistoricalAgent.analyze() ← intel enrichment injected here
         │
         ▼
IntelEnricher.enrich(signal_data)
  → calls _check_virustotal(signal_data)
  → return_exceptions=True — never blocks pipeline
         │
         ▼
_check_virustotal(signal_data)

  Step 1: Extract package_name from signal_data["metadata"]
  [DEBUG] "VT enrichment: checking package_name=com.kingroot.kinguser"

  Step 2: Lookup SHA256 in KNOWN_PACKAGE_HASHES table
  [DEBUG] "VT enrichment: hash lookup result — found=True, hash=a1b2c3...{truncated}"
        │
        If not found:
        [DEBUG] "VT enrichment: package not in known hash table, skipping"
        └── return []

  Step 3: Check Redis cache first
  [DEBUG] "VT enrichment: checking Redis cache key=vt:pkg:{package_name}"
        │
        If cache HIT:
        [DEBUG] "VT enrichment: Redis cache HIT — returning cached result, skipping API call"
        └── return cached IntelMatch

  Step 4: If DEMO_MODE=true → return pre-seeded data immediately
  [DEBUG] "VT enrichment: DEMO_MODE active — returning pre-seeded result for {package_name}"
        └── return pre-seeded IntelMatch

  Step 5: Call VirusTotal API (timeout=5s)
  [DEBUG] "VT enrichment: calling VT API — hash={hash[:16]}... timeout=5s"
        │
        On timeout/error:
        [WARNING] "VT enrichment: API call failed ({error}) — returning empty"
        └── return []

  Step 6: Parse VT response
  [DEBUG] "VT enrichment: response received — malicious={n}, suspicious={m}, engines_total={t}"
  [DEBUG] "VT enrichment: threat_label={label}, tags={tags}"
        │
        If malicious_count == 0:
        [DEBUG] "VT enrichment: no detections — returning empty"
        └── return []

  Step 7: Build IntelMatch, store in Redis cache (TTL=1h)
  [DEBUG] "VT enrichment: IntelMatch created — confidence={c:.2f}, description={desc}"
  [DEBUG] "VT enrichment: result cached — key={cache_key}, TTL=3600s"
        │
        └── return [IntelMatch(...)]
         │
         ▼
HistoricalAgent stores intel_matches in metadata
CoordinatorAgent._synthesize_analysis() → ThreatAnalysis.intel_matches
Redis pub/sub → WebSocket → React Dashboard
```

---

## 3. Data Models

### 3.1 Update ThreatSignal — add metadata field if not present

```python
class ThreatSignal(BaseModel):
    # ... all existing fields unchanged ...
    metadata: dict = {}   # ADD if not present — carries package_name and other signal extras
```

### 3.2 New: IntelMatch — add to `backend/src/models.py`

```python
class IntelMatch(BaseModel):
    ioc_type: str                       # "hash" for VT package lookups
    ioc_value: str                      # Truncated hash for display (first 16 + last 8 chars)
    source: str                         # "virustotal"
    description: str                    # Human-readable detection summary
    date_added: str = ""                # ISO date string from VT first_submission_date
    confidence: float = 0.8             # 0.0–1.0, derived from malicious engine count
    threat_actor: Optional[str] = None  # None for VT lookups (not provided by VT)
```

### 3.3 Update ThreatAnalysis — add intel_matches field

```python
class ThreatAnalysis(BaseModel):
    # ... all existing fields unchanged ...
    intel_matches: List[IntelMatch] = []   # NEW — default empty list
```

---

## 4. Known Package Hash Table

**Location:** top of `backend/src/intel_enricher.py`

Pre-seeded with common malicious Android packages. SHA256 values must be filled in before demo.

> **Pre-demo prep (5 minutes):** For each package, visit `https://www.virustotal.com/gui/search/{package_name}`, go to the Files tab, copy the SHA256 of the top result, and paste it below.

```python
# Maps Android package name → SHA256 hash (pre-seeded for demo)
# To add a new package: search https://www.virustotal.com/gui/search/{package_name}
# Copy SHA256 from the Files tab of the first result
KNOWN_PACKAGE_HASHES: dict[str, str] = {
    # KingRoot — rooting app, flagged by 25+ AV engines
    "com.kingroot.kinguser": "FILL_IN_SHA256_FROM_VT",

    # SuperUser — classic Android rooting app
    "com.noshufou.android.su": "FILL_IN_SHA256_FROM_VT",

    # KingRoot variant
    "com.zhiqupk.root.global": "FILL_IN_SHA256_FROM_VT",

    # Fake battery optimizer — spyware
    "com.battery.fast.charger.free": "FILL_IN_SHA256_FROM_VT",

    # Dev/test app (add hash only if found on VT)
    "sk.madzik.android.logcatudp": "FILL_IN_SHA256_FROM_VT_IF_AVAILABLE",
}
```

---

## 5. Pre-Seeded Demo Cache

**Purpose:** If VT API times out or is unavailable during demo, this pre-seeded data is returned instantly. Also used when `DEMO_MODE=true` to skip all network calls.

**Location:** `backend/src/intel_cache.py`

```python
import logging
import os
import json

logger = logging.getLogger(__name__)

# Pre-seeded demo results — returned instantly when DEMO_MODE=true
# or as fallback when VT API is unavailable
# Update ioc_value fields with real hash prefixes after filling KNOWN_PACKAGE_HASHES
DEMO_INTEL_RESULTS: dict[str, dict] = {
    "com.kingroot.kinguser": {
        "ioc_type": "hash",
        "ioc_value": "a1b2c3d4e5f6a1b2...",   # Replace with first 16 chars of real SHA256
        "source": "virustotal",
        "description": "28/72 AV engines flagged as 'riskware.androidos_root' — KingRoot grants unauthorized root access to Android device",
        "date_added": "",
        "confidence": 0.91,
        "threat_actor": None
    },
    "com.noshufou.android.su": {
        "ioc_type": "hash",
        "ioc_value": "d4e5f6a1b2c3d4e5...",   # Replace with first 16 chars of real SHA256
        "source": "virustotal",
        "description": "31/72 AV engines flagged as 'riskware.android_superuser' — SuperUser grants persistent root shell access",
        "date_added": "",
        "confidence": 0.93,
        "threat_actor": None
    },
    "sk.madzik.android.logcatudp": {
        "ioc_type": "hash",
        "ioc_value": "demo_hash_logcat00...",
        "source": "virustotal",
        "description": "Log capture + UDP exfiltration tool — reads Android system logs and transmits over UDP to remote server",
        "date_added": "",
        "confidence": 0.78,
        "threat_actor": None
    },
}


class IntelFeedCache:
    def __init__(self, redis_client, **kwargs):
        self.redis = redis_client

    async def seed_demo_cache(self):
        """
        Pre-seed Redis with demo VT results on startup when DEMO_MODE=true.
        Stored with key: vt:pkg:{package_name}, TTL=24h for demo stability.
        """
        for package_name, result in DEMO_INTEL_RESULTS.items():
            cache_key = f"vt:pkg:{package_name}"
            await self.redis.set(
                cache_key,
                json.dumps(result),
                ex=86400  # 24 hours
            )
            logger.debug(
                f"Intel cache: seeded demo result — package={package_name} key={cache_key}"
            )
        logger.info(
            f"Intel cache: demo seed complete — {len(DEMO_INTEL_RESULTS)} packages pre-loaded"
        )

    async def start_background_tasks(self):
        """
        Called on app startup. Seeds demo cache if DEMO_MODE=true.
        No background polling needed — VT results are cached on first live lookup.
        """
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        logger.info(f"Intel cache: startup | DEMO_MODE={demo_mode}")
        if demo_mode:
            await self.seed_demo_cache()
```

---

## 6. VirusTotal Lookup — IntelEnricher

**Full file: `backend/src/intel_enricher.py`**

```python
import asyncio
import json
import logging
import os
from typing import Optional
import httpx

from models import IntelMatch
from intel_cache import IntelFeedCache

logger = logging.getLogger(__name__)

# ─── Known Package → SHA256 Hash Table ────────────────────────────────────────
KNOWN_PACKAGE_HASHES: dict[str, str] = {
    "com.kingroot.kinguser":          "FILL_IN_SHA256_FROM_VT",
    "com.noshufou.android.su":        "FILL_IN_SHA256_FROM_VT",
    "com.zhiqupk.root.global":        "FILL_IN_SHA256_FROM_VT",
    "com.battery.fast.charger.free":  "FILL_IN_SHA256_FROM_VT",
    "sk.madzik.android.logcatudp":    "FILL_IN_SHA256_FROM_VT_IF_AVAILABLE",
}

VT_API_BASE = "https://www.virustotal.com/api/v3"
VT_TIMEOUT_SECONDS = int(os.getenv("VT_TIMEOUT_SECONDS", "5"))
VT_CACHE_TTL = 3600  # 1 hour


class IntelEnricher:

    def __init__(self, cache: IntelFeedCache, vt_api_key: Optional[str] = None):
        self.cache = cache
        self.vt_api_key = vt_api_key
        self.demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=VT_TIMEOUT_SECONDS)
        return self._http_client

    # ─── Main Entry Point ─────────────────────────────────────────────────────

    async def enrich(self, signal_data: dict) -> list[IntelMatch]:
        """
        Run VirusTotal enrichment for the given signal.
        Returns list of IntelMatch. Never raises — failures return [].
        """
        logger.debug(
            f"IntelEnricher.enrich: start | "
            f"threat_type={signal_data.get('threat_type', 'unknown')} | "
            f"demo_mode={self.demo_mode}"
        )

        try:
            vt_matches = await self._check_virustotal(signal_data)
            logger.debug(
                f"IntelEnricher.enrich: complete | "
                f"vt_matches={len(vt_matches) if isinstance(vt_matches, list) else 'error'}"
            )
            return vt_matches if isinstance(vt_matches, list) else []

        except Exception as e:
            logger.error(f"IntelEnricher.enrich: unexpected error: {e}")
            return []

    # ─── VirusTotal Check ─────────────────────────────────────────────────────

    async def _check_virustotal(self, signal_data: dict) -> list[IntelMatch]:
        """
        Look up Android package name in VirusTotal via pre-seeded SHA256 hash.

        Flow:
          1. Extract package_name from signal metadata
          2. Lookup SHA256 in KNOWN_PACKAGE_HASHES table
          3. Check Redis cache for existing VT result
          4. If DEMO_MODE=true → return pre-seeded result immediately
          5. Call VT API with configured timeout
          6. Parse response, build IntelMatch, cache result
        """
        # Step 1: Extract package_name
        metadata = signal_data.get("metadata", {})
        package_name = metadata.get("package_name", "").strip()

        if not package_name:
            logger.debug("VT enrichment: no package_name in signal metadata — skipping")
            return []

        logger.debug(f"VT enrichment: checking package_name={package_name}")

        # Step 2: Hash lookup
        file_hash = KNOWN_PACKAGE_HASHES.get(package_name, "")
        if not file_hash or file_hash.startswith("FILL_IN"):
            logger.debug(
                f"VT enrichment: '{package_name}' not in known hash table "
                f"or hash not yet configured — skipping"
            )
            return []

        logger.debug(
            f"VT enrichment: hash lookup — found=True | "
            f"hash={file_hash[:16]}...{file_hash[-8:]}"
        )

        # Step 3: Check Redis cache
        cache_key = f"vt:pkg:{package_name}"
        try:
            cached_raw = await self.cache.redis.get(cache_key)
            if cached_raw:
                logger.debug(
                    f"VT enrichment: Redis cache HIT — key={cache_key} | "
                    f"skipping API call, returning cached result"
                )
                cached_data = json.loads(cached_raw)
                return [IntelMatch(**cached_data)]
        except Exception as e:
            logger.warning(f"VT enrichment: Redis cache read error: {e} — proceeding to API")

        # Step 4: DEMO_MODE — return pre-seeded data without any API call
        if self.demo_mode:
            from intel_cache import DEMO_INTEL_RESULTS
            demo_result = DEMO_INTEL_RESULTS.get(package_name)
            if demo_result:
                logger.debug(
                    f"VT enrichment: DEMO_MODE active — returning pre-seeded result | "
                    f"package={package_name} | "
                    f"description='{demo_result['description'][:70]}...'"
                )
                return [IntelMatch(**demo_result)]
            else:
                logger.debug(
                    f"VT enrichment: DEMO_MODE active but no pre-seeded entry for {package_name}"
                )
                return []

        # Step 5: Live VT API call
        if not self.vt_api_key:
            logger.warning(
                "VT enrichment: VT_API_KEY not configured — skipping live lookup"
            )
            return []

        logger.debug(
            f"VT enrichment: calling VT API | "
            f"hash={file_hash[:16]}... | timeout={VT_TIMEOUT_SECONDS}s"
        )

        try:
            headers = {"x-apikey": self.vt_api_key}
            response = await self.http.get(
                f"{VT_API_BASE}/files/{file_hash}",
                headers=headers
            )

            if response.status_code == 404:
                logger.debug(
                    f"VT enrichment: hash not found in VT database (404) | package={package_name}"
                )
                return []

            if response.status_code == 429:
                logger.warning("VT enrichment: rate limit hit (429) — skipping")
                return []

            if response.status_code != 200:
                logger.warning(
                    f"VT enrichment: unexpected HTTP {response.status_code} | package={package_name}"
                )
                return []

            # Step 6: Parse response
            vt_data = response.json().get("data", {}).get("attributes", {})
            stats = vt_data.get("last_analysis_stats", {})
            malicious_count = stats.get("malicious", 0)
            suspicious_count = stats.get("suspicious", 0)
            total_engines = sum(stats.values()) or 1
            threat_label = (
                vt_data.get("popular_threat_classification", {})
                       .get("suggested_threat_label", "unknown")
            )
            vt_tags = vt_data.get("tags", [])
            first_seen_ts = vt_data.get("first_submission_date", None)

            logger.debug(
                f"VT enrichment: API response | "
                f"malicious={malicious_count} | suspicious={suspicious_count} | "
                f"total_engines={total_engines} | threat_label='{threat_label}' | "
                f"tags={vt_tags}"
            )

            if malicious_count == 0 and suspicious_count == 0:
                logger.debug(
                    f"VT enrichment: no detections for {package_name} — "
                    f"returning empty (clean or unknown package)"
                )
                return []

            # Confidence: normalized against ~72 VT engines, capped at 0.97
            confidence = round(min(0.97, 0.5 + (malicious_count / 72)), 2)

            # Format first_seen timestamp
            first_seen_str = ""
            if first_seen_ts:
                try:
                    import datetime
                    first_seen_str = datetime.datetime.utcfromtimestamp(
                        first_seen_ts
                    ).strftime("%Y-%m-%d")
                except Exception:
                    pass

            intel_match = IntelMatch(
                ioc_type="hash",
                ioc_value=f"{file_hash[:16]}...{file_hash[-8:]}",
                source="virustotal",
                description=(
                    f"{malicious_count}/{total_engines} AV engines flagged as "
                    f"'{threat_label}' — package: {package_name}"
                ),
                date_added=first_seen_str,
                confidence=confidence,
                threat_actor=None
            )

            logger.debug(
                f"VT enrichment: IntelMatch created | "
                f"confidence={confidence} | "
                f"description='{intel_match.description[:80]}...'"
            )

            # Cache result to avoid repeat API calls for same package
            try:
                await self.cache.redis.set(
                    cache_key,
                    json.dumps(intel_match.dict()),
                    ex=VT_CACHE_TTL
                )
                logger.debug(
                    f"VT enrichment: result cached | key={cache_key} | TTL={VT_CACHE_TTL}s"
                )
            except Exception as e:
                logger.warning(f"VT enrichment: cache write failed: {e}")

            return [intel_match]

        except httpx.TimeoutException:
            logger.warning(
                f"VT enrichment: API timed out after {VT_TIMEOUT_SECONDS}s | "
                f"package={package_name} — returning empty"
            )
            return []

        except httpx.RequestError as e:
            logger.warning(
                f"VT enrichment: network error calling VT API: {e} — returning empty"
            )
            return []

        except Exception as e:
            logger.error(f"VT enrichment: unexpected error for {package_name}: {e}")
            return []
```

---

## 7. Intel Cache Layer

**Full file: `backend/src/intel_cache.py`**

Simple Redis wrapper. No background polling — VT results are cached on first live lookup and expire after 1 hour. Demo data is seeded on startup when `DEMO_MODE=true`.

```python
import asyncio
import json
import logging
import os
from typing import Optional
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

DEMO_INTEL_RESULTS: dict[str, dict] = {
    "com.kingroot.kinguser": {
        "ioc_type": "hash",
        "ioc_value": "a1b2c3d4e5f6a1b2...",
        "source": "virustotal",
        "description": "28/72 AV engines flagged as 'riskware.androidos_root' — KingRoot grants unauthorized root access to Android device",
        "date_added": "",
        "confidence": 0.91,
        "threat_actor": None
    },
    "com.noshufou.android.su": {
        "ioc_type": "hash",
        "ioc_value": "d4e5f6a1b2c3d4e5...",
        "source": "virustotal",
        "description": "31/72 AV engines flagged as 'riskware.android_superuser' — SuperUser grants persistent root shell access",
        "date_added": "",
        "confidence": 0.93,
        "threat_actor": None
    },
    "sk.madzik.android.logcatudp": {
        "ioc_type": "hash",
        "ioc_value": "demo_hash_logcat00...",
        "source": "virustotal",
        "description": "Log capture + UDP exfiltration tool — reads Android system logs and transmits over UDP to remote server",
        "date_added": "",
        "confidence": 0.78,
        "threat_actor": None
    },
}


class IntelFeedCache:

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def seed_demo_cache(self):
        """
        Pre-seed Redis with demo VT results.
        Called on startup when DEMO_MODE=true.
        TTL=24h for demo stability across restarts.
        """
        for package_name, result in DEMO_INTEL_RESULTS.items():
            cache_key = f"vt:pkg:{package_name}"
            await self.redis.set(
                cache_key,
                json.dumps(result),
                ex=86400
            )
            logger.debug(
                f"Intel cache: seeded | package={package_name} | key={cache_key}"
            )
        logger.info(
            f"Intel cache: demo seed complete — {len(DEMO_INTEL_RESULTS)} packages pre-loaded"
        )

    async def start_background_tasks(self):
        """
        Called on app startup.
        Seeds demo cache if DEMO_MODE=true.
        No background polling — VT results are request-time cached.
        """
        demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
        logger.info(f"Intel cache: startup | DEMO_MODE={demo_mode}")

        if demo_mode:
            logger.info("Intel cache: DEMO_MODE active — seeding demo packages into Redis")
            await self.seed_demo_cache()
        else:
            logger.info(
                "Intel cache: live mode — VT results will be cached on first lookup per package"
            )
```

---

## 8. HistoricalAgent Integration

**Update `backend/src/agents/historical_agent.py`:**

```python
import logging
from typing import Optional
logger = logging.getLogger(__name__)


class HistoricalAgent(BaseAgent):

    def __init__(self, client, intel_enricher=None):
        super().__init__(client)
        self.intel_enricher = intel_enricher
        logger.debug(
            f"HistoricalAgent init: intel_enricher="
            f"{'configured' if intel_enricher else 'None'}"
        )

    async def analyze(self, signal: ThreatSignal, context: dict) -> AgentAnalysis:
        logger.debug(
            f"HistoricalAgent.analyze: start | "
            f"threat_type={signal.threat_type} | "
            f"package_name={signal.metadata.get('package_name', 'none')}"
        )

        # Run existing historical analysis (unchanged)
        result = await super().analyze(signal, context)

        # Run VT enrichment — never blocks if it fails
        intel_matches = []
        if self.intel_enricher:
            signal_dict = signal.dict() if hasattr(signal, 'dict') else vars(signal)
            logger.debug("HistoricalAgent.analyze: starting VT intel enrichment")
            intel_matches = await self.intel_enricher.enrich(signal_dict)
            logger.debug(
                f"HistoricalAgent.analyze: VT enrichment complete | "
                f"matches={len(intel_matches)}"
            )
        else:
            logger.debug("HistoricalAgent.analyze: no intel_enricher configured — skipping")

        # Store results in metadata for coordinator to pick up
        if result.metadata is None:
            result.metadata = {}
        result.metadata["intel_matches"] = [m.dict() for m in intel_matches]

        logger.debug(
            f"HistoricalAgent.analyze: complete | "
            f"intel_matches_count={len(intel_matches)}"
        )
        return result
```

---

## 9. CoordinatorAgent Changes

**Two changes in `backend/src/coordinator.py`:**

### 9.1 Initialize IntelEnricher and inject into HistoricalAgent

```python
import os
import logging
from intel_cache import IntelFeedCache
from intel_enricher import IntelEnricher

class CoordinatorAgent:

    def __init__(self, ..., intel_cache: Optional[IntelFeedCache] = None):
        # ... existing init ...
        self.logger = logging.getLogger(__name__)

        vt_api_key = os.getenv("VT_API_KEY")
        enricher = IntelEnricher(intel_cache, vt_api_key=vt_api_key) if intel_cache else None
        self.historical_agent = HistoricalAgent(client=self.client, intel_enricher=enricher)

        self.logger.debug(
            f"CoordinatorAgent init | "
            f"intel_enricher={'configured' if enricher else 'None'} | "
            f"vt_api_key={'set' if vt_api_key else 'NOT SET'} | "
            f"demo_mode={os.getenv('DEMO_MODE', 'false')}"
        )
```

### 9.2 Collect intel_matches in synthesis

```python
def _synthesize_analysis(self, signal, analyses, elapsed_time) -> ThreatAnalysis:
    # ... existing synthesis code ...

    # Collect intel_matches from HistoricalAgent metadata
    historical_metadata = analyses.get("historical", {}).get("metadata", {})
    raw_intel = historical_metadata.get("intel_matches", [])
    intel_matches = []
    for item in raw_intel:
        try:
            intel_matches.append(IntelMatch(**item))
        except Exception as e:
            self.logger.warning(f"CoordinatorAgent: failed to parse IntelMatch: {e}")

    self.logger.debug(
        f"CoordinatorAgent._synthesize_analysis: intel_matches_count={len(intel_matches)}"
    )

    return ThreatAnalysis(
        # ... all existing fields unchanged ...
        intel_matches=intel_matches   # NEW FIELD
    )
```

---

## 10. API Changes

### 10.1 Initialize IntelFeedCache on startup — `backend/src/main.py`

```python
from intel_cache import IntelFeedCache
import asyncio

@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...

    redis_client = app.state.redis  # Use existing Redis client
    intel_cache = IntelFeedCache(redis_client=redis_client)
    app.state.intel_cache = intel_cache

    # Seed demo cache if DEMO_MODE=true (non-blocking)
    asyncio.create_task(intel_cache.start_background_tasks())

    # Pass cache to coordinator
    app.state.coordinator = CoordinatorAgent(..., intel_cache=intel_cache)
```

### 10.2 Status endpoint — useful for demo verification

```python
import os
from intel_enricher import KNOWN_PACKAGE_HASHES

@app.get("/api/intel/status")
async def intel_status():
    """Return VT configuration and cache status. Use to verify setup before demo."""
    vt_api_key = os.getenv("VT_API_KEY", "")
    demo_mode = os.getenv("DEMO_MODE", "false")

    hashes_configured = [
        pkg for pkg, h in KNOWN_PACKAGE_HASHES.items()
        if h and not h.startswith("FILL_IN")
    ]

    return {
        "demo_mode": demo_mode,
        "virustotal": {
            "api_key_configured": bool(vt_api_key),
            "known_packages_total": len(KNOWN_PACKAGE_HASHES),
            "hashes_configured": hashes_configured,
            "hashes_pending": [
                pkg for pkg in KNOWN_PACKAGE_HASHES
                if pkg not in hashes_configured
            ]
        }
    }
```

---

## 11. Frontend Changes

### 11.1 New file: `frontend/src/components/IntelMatchCard.jsx`

```jsx
export function IntelMatchCard({ match }) {
  return (
    <div className="rounded border border-blue-500 bg-blue-950 text-blue-200 p-3 text-sm">
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold font-mono text-xs">
          🔑 {match.ioc_value}
        </span>
        <span className="text-xs px-1.5 py-0.5 rounded bg-black bg-opacity-30 font-semibold">
          🛡 VirusTotal
        </span>
      </div>
      <div className="text-xs opacity-80 leading-relaxed">{match.description}</div>
      <div className="flex justify-between items-center mt-2">
        {match.date_added
          ? <span className="text-xs opacity-50">First seen: {match.date_added}</span>
          : <span />
        }
        <span className="text-xs opacity-60">
          {(match.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
    </div>
  );
}

export function IntelMatchSection({ matches }) {
  if (!matches || matches.length === 0) return null;

  return (
    <div className="mt-4">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 font-semibold flex items-center gap-2">
        <span>🛡 Live Threat Intelligence</span>
        <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
      </div>
      <div className="grid gap-2">
        {matches.map((match, i) => (
          <IntelMatchCard key={`${match.ioc_value}-${i}`} match={match} />
        ))}
      </div>
    </div>
  );
}
```

### 11.2 Update ThreatDetails component

```jsx
import { IntelMatchSection } from "./IntelMatchCard";

// Inside ThreatDetails render, after MITRE tags section:
<IntelMatchSection matches={threat.intel_matches} />
```

### 11.3 VT status indicator in Dashboard header

```jsx
function VTStatus() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetch("/api/intel/status")
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  if (!status) return null;

  const vtReady = status.virustotal?.hashes_configured?.length > 0;

  return (
    <div className="flex items-center gap-1.5 text-xs text-gray-400"
         title={`VT: ${status.virustotal?.hashes_configured?.length ?? 0} packages ready`}>
      <span className={`w-2 h-2 rounded-full ${vtReady ? "bg-blue-400" : "bg-gray-600"}`} />
      <span>VT Intel</span>
      {status.demo_mode === "true" && (
        <span className="px-1 rounded bg-yellow-800 text-yellow-300 font-semibold">DEMO</span>
      )}
    </div>
  );
}
```

---

## 12. Environment Variables

Add to `backend/.env.example`:

```env
# ─── VirusTotal Intel ─────────────────────────────────────────────────────────

# VirusTotal API Key (free tier: 500 req/day, 4 req/min)
# Sign up free at: https://www.virustotal.com/gui/join-us
# Without this key: VT lookups are skipped (intel_matches returns [])
VT_API_KEY=

# Demo mode: skips live VT API calls and returns pre-seeded cache data instantly
# Set true for live demos — eliminates all network latency risk
# Set false for real deployments and production testing
DEMO_MODE=false

# VirusTotal request timeout in seconds (default: 5)
# Reduce to 2 for faster fallback during demos if needed
# VT_TIMEOUT_SECONDS=5
```

---

## 13. File Change Map

| File | Change | Notes |
|---|---|---|
| `backend/src/models.py` | **Modify** | Add `IntelMatch`; add `intel_matches: List[IntelMatch] = []` to `ThreatAnalysis`; add `metadata: dict = {}` to `ThreatSignal` if missing |
| `backend/src/intel_enricher.py` | **Create** | `IntelEnricher` class, `KNOWN_PACKAGE_HASHES` table, `_check_virustotal()` with full debug logging |
| `backend/src/intel_cache.py` | **Create** | `IntelFeedCache` class, `DEMO_INTEL_RESULTS` table, `seed_demo_cache()`, `start_background_tasks()` |
| `backend/src/agents/historical_agent.py` | **Modify** | Accept `intel_enricher`; call `enrich()` in `analyze()`; store in `metadata["intel_matches"]` |
| `backend/src/coordinator.py` | **Modify** | Accept `intel_cache`; init `IntelEnricher`; inject into `HistoricalAgent`; collect `intel_matches` in synthesis |
| `backend/src/main.py` | **Modify** | Init `IntelFeedCache` on startup; start background tasks; add `/api/intel/status` |
| `backend/src/wazuh_connector.py` | **Modify** | Confirm `alert.data.package_name` → `signal.metadata["package_name"]` |
| `backend/.env.example` | **Modify** | Add `VT_API_KEY`, `DEMO_MODE`, `VT_TIMEOUT_SECONDS` |
| `backend/requirements.txt` | **Modify** | Add `httpx>=0.27.0` if not present |
| `frontend/src/components/IntelMatchCard.jsx` | **Create** | Intel match card + section components |
| `frontend/src/components/ThreatDetails.jsx` | **Modify** | Add `<IntelMatchSection>` |
| `frontend/src/components/Dashboard.jsx` | **Modify** | Add `<VTStatus>` indicator to header |

**Total: 12 files** (3 new, 9 modified)

---

## 14. Implementation Steps

```
Step 1 — Data models (15 min)
  □ Add IntelMatch to models.py
  □ Add intel_matches: List[IntelMatch] = [] to ThreatAnalysis
  □ Add metadata: dict = {} to ThreatSignal if not present
  □ Add httpx>=0.27.0 to requirements.txt if not present

Step 2 — Intel cache (20 min)
  □ Create intel_cache.py
  □ Add DEMO_INTEL_RESULTS with all 3 demo packages
  □ Implement seed_demo_cache() with per-package debug logging
  □ Implement start_background_tasks()

Step 3 — Intel enricher (45 min)
  □ Create intel_enricher.py with KNOWN_PACKAGE_HASHES table
  □ Implement enrich() wrapper
  □ Implement _check_virustotal() with all 7 steps
  □ Verify all logger.debug() and logger.warning() statements present per architecture diagram
  □ Verify every failure path returns [] without raising

Step 4 — Wazuh connector (10 min)
  □ Confirm alert.data.package_name is extracted to signal.metadata["package_name"]
  □ Add extraction line if not already present

Step 5 — HistoricalAgent (15 min)
  □ Add intel_enricher parameter to __init__()
  □ Call enrich() after existing super().analyze()
  □ Store results in result.metadata["intel_matches"]
  □ Add all debug logging statements

Step 6 — CoordinatorAgent (20 min)
  □ Accept intel_cache; init IntelEnricher with VT_API_KEY from env
  □ Inject enricher into HistoricalAgent
  □ Collect intel_matches from historical metadata in synthesis
  □ Add debug log for intel_matches count

Step 7 — Main.py startup (15 min)
  □ Initialize IntelFeedCache using existing Redis client
  □ asyncio.create_task(intel_cache.start_background_tasks())
  □ Pass cache to coordinator
  □ Add /api/intel/status endpoint

Step 8 — Environment (5 min)
  □ Add VT_API_KEY, DEMO_MODE, VT_TIMEOUT_SECONDS to .env.example
  □ Set DEMO_MODE=true in local .env for demo
  □ Add VT_API_KEY to local .env

Step 9 — Fill KNOWN_PACKAGE_HASHES (5 min — do before demo)
  □ Visit virustotal.com/gui/search/com.kingroot.kinguser → Files tab → copy SHA256
  □ Repeat for com.noshufou.android.su
  □ Repeat for sk.madzik.android.logcatudp (skip if not on VT)
  □ Update ioc_value prefixes in DEMO_INTEL_RESULTS to match real hash prefixes

Step 10 — Frontend (35 min)
  □ Create IntelMatchCard.jsx with IntelMatchCard and IntelMatchSection
  □ Update ThreatDetails.jsx to include <IntelMatchSection matches={threat.intel_matches} />
  □ Add <VTStatus /> indicator to Dashboard header

Step 11 — Verify (15 min)
  □ GET /api/intel/status — confirm packages listed, DEMO_MODE shown
  □ Set DEMO_MODE=true, trigger com.kingroot.kinguser → IntelMatch appears in dashboard
  □ Check console for full debug log chain (all 7 steps visible)
  □ Set DEMO_MODE=false + VT_API_KEY → confirm live VT response parsed
  □ Remove VT_API_KEY → confirm graceful skip, no crash
```

**Estimated total: ~3 hours** + 5 min pre-demo hash prep

---

## 15. Testing Checklist

```
□ GET /api/intel/status returns expected structure
□ DEMO_MODE=true: IntelMatch returned instantly for com.kingroot.kinguser
□ DEMO_MODE=true: console shows "DEMO_MODE active — returning pre-seeded result"
□ DEMO_MODE=false + VT_API_KEY: live VT response parsed, IntelMatch created
□ DEMO_MODE=false + no VT_API_KEY: enrichment skipped, intel_matches=[], no crash
□ Package not in KNOWN_PACKAGE_HASHES: returns [], debug log shows "not in known hash table"
□ Hash set to "FILL_IN...": treated as unconfigured, returns [], no API call
□ VT API timeout (set VT_TIMEOUT_SECONDS=1): returns [], warning logged, no crash
□ VT API 429 rate limit: returns [], warning logged, no crash
□ VT API 404: returns [], debug logged, no crash
□ Redis cache hit on second trigger of same package: no VT API call made
□ ThreatAnalysis.intel_matches=[] for alert with no package: no crash, section not rendered
□ IntelMatchCard renders blue VT styling correctly
□ IntelMatchSection animate-pulse dot visible when matches present
□ VTStatus header dot is blue when hashes configured, gray when not
□ DEMO badge visible in header when DEMO_MODE=true
□ All existing tests pass (intel_matches is additive field)
```
