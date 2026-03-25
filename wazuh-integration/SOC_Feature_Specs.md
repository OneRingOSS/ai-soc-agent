# SOC Agent System — Feature Implementation Specs
## MITRE ATT&CK Tactic Tagging & Live Threat Intelligence Feed
### For Augment Code

**Version:** 1.0
**Date:** March 22, 2026
**Status:** Ready for Implementation
**Existing Stack:** Python/FastAPI, 5 specialized agents (Historical, Config, DevOps, Context, Priority), CoordinatorAgent, async parallel execution, Redis pub/sub, React/Vite frontend, OpenTelemetry observability

---

## Table of Contents

1. [Overview and Integration Map](#1-overview-and-integration-map)
2. [Feature 1: MITRE ATT&CK Tactic Tagging](#2-feature-1-mitre-attck-tactic-tagging)
   - 2.1 [Spec and Objectives](#21-spec-and-objectives)
   - 2.2 [Architecture](#22-architecture)
   - 2.3 [Data Models](#23-data-models)
   - 2.4 [Agent Changes — ContextAgent / PriorityAgent](#24-agent-changes--contextagent--priorityagent)
   - 2.5 [Wazuh Pass-Through](#25-wazuh-pass-through)
   - 2.6 [API Changes](#26-api-changes)
   - 2.7 [Frontend Changes](#27-frontend-changes)
   - 2.8 [Implementation Steps](#28-implementation-steps)
3. [Feature 2: Live Threat Intelligence Feed](#3-feature-2-live-threat-intelligence-feed)
   - 3.1 [Spec and Objectives](#31-spec-and-objectives)
   - 3.2 [Architecture](#32-architecture)
   - 3.3 [Data Sources](#33-data-sources)
   - 3.4 [Intel Cache Layer](#34-intel-cache-layer)
   - 3.5 [HistoricalAgent Integration](#35-historicalagent-integration)
   - 3.6 [Data Models](#36-data-models)
   - 3.7 [API Changes](#37-api-changes)
   - 3.8 [Frontend Changes](#38-frontend-changes)
   - 3.9 [Implementation Steps](#39-implementation-steps)
4. [End-to-End Demo Flow](#4-end-to-end-demo-flow)
   - 4.1 [Full Pipeline Narrative](#41-full-pipeline-narrative)
   - 4.2 [Demo Script for Michael Spisak](#42-demo-script-for-michael-spisak)
5. [File Change Map](#5-file-change-map)
6. [Testing Checklist](#6-testing-checklist)
7. [Environment Variables](#7-environment-variables)

---

## 1. Overview and Integration Map

These two features extend the existing SOC Agent System without modifying core coordinator logic or breaking existing functionality. Both are **additive** — they enrich the `ThreatAnalysis` output and surface new data in the dashboard.

### Where Each Feature Plugs In

```text
EXISTING PIPELINE
─────────────────────────────────────────────────────────────────────────
Wazuh Alert / Synthetic Signal
        │
        ▼
POST /api/threats/trigger
        │
        ▼
CoordinatorAgent.analyze_threat(signal)
        │
        ├── HistoricalAgent    ◄── [Feature 2] Intel enrichment injected here
        ├── ConfigAgent
        ├── DevOpsAgent
        ├── ContextAgent       ◄── [Feature 1] ATT&CK tagging added here
        └── PriorityAgent      ◄── [Feature 1] ATT&CK tagging reinforced here
                │
                ▼
        FP Analyzer + Response Engine + Timeline Builder
                │
                ▼
        ThreatAnalysis (synthesized)
                │
                ├── [Feature 1] mitre_tags: List[MitreTag]  ← new field
                └── [Feature 2] intel_matches: List[IntelMatch] ← new field
                │
                ▼
        Redis pub/sub → WebSocket → React Dashboard
        (both new fields surface in UI)
─────────────────────────────────────────────────────────────────────────
```

### Key Design Principles for Augment Code

1. **Never block the coordinator.** Both features use `asyncio.gather` with `return_exceptions=True` — if the intel feed or ATT&CK lookup fails, the main analysis proceeds unaffected.
2. **Additive fields only.** `ThreatAnalysis` Pydantic model gets two new optional fields. No existing fields are modified.
3. **Wazuh pass-through first.** When a Wazuh alert arrives via the connector (already built), any ATT&CK technique IDs already present in the Wazuh rule metadata should be passed through directly — no LLM call needed for those.
4. **Intel cache.** Both CISA KEV and OTX feeds are cached in Redis with TTL (CISA: 4 hours, OTX: 1 hour). The `HistoricalAgent` reads from cache; a background task refreshes it.

---

## 2. Feature 1: MITRE ATT&CK Tactic Tagging

### 2.1 Spec and Objectives

**Goal:** Every `ThreatAnalysis` output includes one or more MITRE ATT&CK Technique IDs (e.g., `T1566.001`, `T1059.003`) and their human-readable tactic names, automatically derived from the threat signal and agent analysis.

**Sources of ATT&CK tags (in priority order):**
1. **Wazuh pass-through** — Wazuh rules already map to ATT&CK. Extract from incoming alert if present.
2. **ContextAgent LLM** — Updated system prompt instructs the agent to output structured ATT&CK tags.
3. **PriorityAgent LLM** — Reinforces and validates the tags from ContextAgent, adds any missed techniques.
4. **Keyword fallback** — Simple deterministic lookup table mapping threat types to likely ATT&CK techniques (no LLM needed, always succeeds).

**Output format in ThreatAnalysis:**
```json
"mitre_tags": [
  {
    "technique_id": "T1566.001",
    "technique_name": "Spearphishing Attachment",
    "tactic": "Initial Access",
    "tactic_id": "TA0001",
    "confidence": 0.87,
    "source": "context_agent"
  },
  {
    "technique_id": "T1059.003",
    "technique_name": "Windows Command Shell",
    "tactic": "Execution",
    "tactic_id": "TA0002",
    "confidence": 0.72,
    "source": "priority_agent"
  }
]
```

### 2.2 Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                  MITRE ATT&CK TAGGING FLOW                       │
│                                                                   │
│  1. Wazuh alert arrives with rule.mitre.technique[] array        │
│     → WazuhConnector extracts → passes as signal.mitre_hints     │
│                                                                   │
│  2. CoordinatorAgent._build_agent_contexts() adds mitre_hints    │
│     to ContextAgent and PriorityAgent context dicts              │
│                                                                   │
│  3. ContextAgent (updated system prompt):                         │
│     → Analyzes threat signal                                      │
│     → Outputs structured JSON block with ATT&CK techniques        │
│     → Returns MitreTag list in AgentAnalysis.metadata['mitre']   │
│                                                                   │
│  4. PriorityAgent (updated system prompt):                        │
│     → Reviews ContextAgent's tags                                 │
│     → Validates / adds missing techniques                         │
│     → Returns final MitreTag list                                 │
│                                                                   │
│  5. CoordinatorAgent._synthesize_analysis():                      │
│     → Merges tags from both agents (dedup by technique_id)        │
│     → Applies keyword_fallback() if list is empty                 │
│     → Sets ThreatAnalysis.mitre_tags                              │
│                                                                   │
│  6. Frontend MitreTagBadge component renders tags                 │
│     → Color-coded by tactic (red=Initial Access, orange=Exec...) │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Models

**New Pydantic model** — add to `backend/src/models.py`:

```python
class MitreTag(BaseModel):
    technique_id: str           # e.g. "T1566.001"
    technique_name: str         # e.g. "Spearphishing Attachment"
    tactic: str                 # e.g. "Initial Access"
    tactic_id: str              # e.g. "TA0001"
    confidence: float = 1.0     # 0.0–1.0
    source: str = "context_agent"  # "wazuh" | "context_agent" | "priority_agent" | "fallback"
```

**Update ThreatAnalysis** — add optional field:

```python
class ThreatAnalysis(BaseModel):
    # ... all existing fields unchanged ...
    mitre_tags: List[MitreTag] = []          # NEW — default empty list
    intel_matches: List["IntelMatch"] = []   # NEW — defined in Feature 2
```

**Update ThreatSignal** — add optional hint field from Wazuh:

```python
class ThreatSignal(BaseModel):
    # ... all existing fields unchanged ...
    mitre_hints: List[str] = []   # NEW — pre-populated by Wazuh connector if available
```

**Keyword fallback lookup table** — new file `backend/src/mitre_fallback.py`:

```python
# Maps threat_type → list of ATT&CK technique dicts (deterministic, no LLM)
THREAT_TYPE_TO_MITRE: dict[str, list[dict]] = {
    "bot_traffic": [
        {"technique_id": "T1071.001", "technique_name": "Web Protocols",
         "tactic": "Command and Control", "tactic_id": "TA0011"},
        {"technique_id": "T1583.005", "technique_name": "Botnet",
         "tactic": "Resource Development", "tactic_id": "TA0042"},
    ],
    "credential_stuffing": [
        {"technique_id": "T1110.004", "technique_name": "Credential Stuffing",
         "tactic": "Credential Access", "tactic_id": "TA0006"},
        {"technique_id": "T1078", "technique_name": "Valid Accounts",
         "tactic": "Defense Evasion", "tactic_id": "TA0005"},
    ],
    "account_takeover": [
        {"technique_id": "T1078", "technique_name": "Valid Accounts",
         "tactic": "Persistence", "tactic_id": "TA0003"},
        {"technique_id": "T1110", "technique_name": "Brute Force",
         "tactic": "Credential Access", "tactic_id": "TA0006"},
    ],
    "data_scraping": [
        {"technique_id": "T1119", "technique_name": "Automated Collection",
         "tactic": "Collection", "tactic_id": "TA0009"},
        {"technique_id": "T1213", "technique_name": "Data from Information Repositories",
         "tactic": "Collection", "tactic_id": "TA0009"},
    ],
    "geo_anomaly": [
        {"technique_id": "T1078", "technique_name": "Valid Accounts",
         "tactic": "Defense Evasion", "tactic_id": "TA0005"},
        {"technique_id": "T1133", "technique_name": "External Remote Services",
         "tactic": "Persistence", "tactic_id": "TA0003"},
    ],
    "rate_limit_breach": [
        {"technique_id": "T1499", "technique_name": "Endpoint Denial of Service",
         "tactic": "Impact", "tactic_id": "TA0040"},
        {"technique_id": "T1498", "technique_name": "Network Denial of Service",
         "tactic": "Impact", "tactic_id": "TA0040"},
    ],
    "brute_force": [
        {"technique_id": "T1110.001", "technique_name": "Password Guessing",
         "tactic": "Credential Access", "tactic_id": "TA0006"},
    ],
    "device_compromise": [
        {"technique_id": "T1059", "technique_name": "Command and Scripting Interpreter",
         "tactic": "Execution", "tactic_id": "TA0002"},
        {"technique_id": "T1543", "technique_name": "Create or Modify System Process",
         "tactic": "Persistence", "tactic_id": "TA0003"},
    ],
    "anomaly_detection": [
        {"technique_id": "T1036", "technique_name": "Masquerading",
         "tactic": "Defense Evasion", "tactic_id": "TA0005"},
    ],
    # Wazuh-originated: generic network attack
    "network_attack": [
        {"technique_id": "T1046", "technique_name": "Network Service Discovery",
         "tactic": "Discovery", "tactic_id": "TA0007"},
    ],
    "port_scan": [
        {"technique_id": "T1046", "technique_name": "Network Service Discovery",
         "tactic": "Discovery", "tactic_id": "TA0007"},
        {"technique_id": "T1595.001", "technique_name": "Scanning IP Blocks",
         "tactic": "Reconnaissance", "tactic_id": "TA0043"},
    ],
    "web_attack": [
        {"technique_id": "T1190", "technique_name": "Exploit Public-Facing Application",
         "tactic": "Initial Access", "tactic_id": "TA0001"},
    ],
    "malware": [
        {"technique_id": "T1204", "technique_name": "User Execution",
         "tactic": "Execution", "tactic_id": "TA0002"},
        {"technique_id": "T1027", "technique_name": "Obfuscated Files or Information",
         "tactic": "Defense Evasion", "tactic_id": "TA0005"},
    ],
}

def get_fallback_tags(threat_type: str) -> list[dict]:
    """Return deterministic ATT&CK tags for a given threat type. Never fails."""
    return THREAT_TYPE_TO_MITRE.get(
        threat_type.lower(),
        [{"technique_id": "T1499", "technique_name": "Endpoint Denial of Service",
          "tactic": "Impact", "tactic_id": "TA0040"}]  # safe default
    )
```

### 2.4 Agent Changes — ContextAgent / PriorityAgent

**ContextAgent** — update `get_system_prompt()` to append ATT&CK tagging instructions:

```python
def get_system_prompt(self) -> str:
    return """You are a cybersecurity context analysis specialist with deep expertise 
in MITRE ATT&CK framework.

Your role is to analyze security threats and provide:
1. Business context and risk assessment
2. Relevant news and threat intelligence context
3. MITRE ATT&CK technique mapping

CRITICAL: You MUST output a structured ATT&CK section in your response using this
exact JSON block format:

<MITRE_TAGS>
[
  {
    "technique_id": "T1566.001",
    "technique_name": "Spearphishing Attachment",
    "tactic": "Initial Access",
    "tactic_id": "TA0001",
    "confidence": 0.85
  }
]
</MITRE_TAGS>

Rules for ATT&CK tagging:
- Include 1–4 techniques maximum
- Only include techniques with confidence >= 0.60
- Use exact MITRE ATT&CK technique IDs from the official framework
- If mitre_hints are provided in the context, include those techniques first
- Map to the MOST SPECIFIC sub-technique when possible (e.g., T1566.001 not T1566)
"""
```

**PriorityAgent** — update `get_system_prompt()` to validate and extend ATT&CK tags:

```python
def get_system_prompt(self) -> str:
    return """You are a MITRE ATT&CK expert and threat prioritization specialist.

Your role is to:
1. Prioritize the security threat (CRITICAL/HIGH/MEDIUM/LOW)
2. Validate and extend the MITRE ATT&CK technique mapping from the Context Agent
3. Add any missed techniques not identified by the Context Agent

Review the context_agent_mitre_tags in your input context.
Output a validated/extended tag list using this exact format:

<MITRE_TAGS>
[
  {
    "technique_id": "T1059.003",
    "technique_name": "Windows Command Shell",
    "tactic": "Execution",
    "tactic_id": "TA0002",
    "confidence": 0.78
  }
]
</MITRE_TAGS>

Only include techniques NOT already in context_agent_mitre_tags (avoid duplicates).
Maximum 2 additional techniques. If context_agent_mitre_tags already has good coverage, 
output an empty array [].
"""
```

**Agent parser utility** — new file `backend/src/mitre_parser.py`:

```python
import re
import json
from typing import List
from models import MitreTag

def extract_mitre_tags(agent_output: str, source: str = "context_agent") -> List[MitreTag]:
    """
    Parse <MITRE_TAGS>...</MITRE_TAGS> block from LLM agent output.
    Returns empty list if block not found or JSON is malformed.
    Never raises exceptions.
    """
    try:
        match = re.search(r'<MITRE_TAGS>\s*(.*?)\s*</MITRE_TAGS>', agent_output, re.DOTALL)
        if not match:
            return []
        
        raw_json = match.group(1).strip()
        tags_data = json.loads(raw_json)
        
        if not isinstance(tags_data, list):
            return []
        
        tags = []
        for item in tags_data:
            if not isinstance(item, dict):
                continue
            if not item.get("technique_id") or not item.get("tactic"):
                continue
            tags.append(MitreTag(
                technique_id=item.get("technique_id", ""),
                technique_name=item.get("technique_name", "Unknown"),
                tactic=item.get("tactic", "Unknown"),
                tactic_id=item.get("tactic_id", ""),
                confidence=float(item.get("confidence", 0.8)),
                source=source
            ))
        
        return tags
    
    except Exception:
        return []  # Never block analysis for tagging failures


def merge_mitre_tags(context_tags: List[MitreTag], priority_tags: List[MitreTag]) -> List[MitreTag]:
    """
    Merge tags from ContextAgent and PriorityAgent.
    Deduplicates by technique_id. Context agent tags take precedence.
    """
    seen_ids = {tag.technique_id for tag in context_tags}
    merged = list(context_tags)
    
    for tag in priority_tags:
        if tag.technique_id not in seen_ids:
            merged.append(tag)
            seen_ids.add(tag.technique_id)
    
    return merged[:6]  # Cap at 6 techniques max
```

### 2.5 Wazuh Pass-Through

In the existing Wazuh connector (`backend/src/wazuh_connector.py` or similar), extract ATT&CK hints from the Wazuh alert before building the `ThreatSignal`:

```python
def extract_mitre_hints_from_wazuh(wazuh_alert: dict) -> list[str]:
    """
    Extract MITRE ATT&CK technique IDs from Wazuh alert rule metadata.
    Wazuh format: alert.rule.mitre.technique = ["T1566", "T1059"]
    Returns list of technique IDs or empty list.
    """
    try:
        rule = wazuh_alert.get("rule", {})
        mitre = rule.get("mitre", {})
        techniques = mitre.get("technique", [])
        
        if isinstance(techniques, list):
            return [t for t in techniques if isinstance(t, str) and t.startswith("T")]
        elif isinstance(techniques, str):
            return [techniques] if techniques.startswith("T") else []
        return []
    except Exception:
        return []


# In your Wazuh alert → ThreatSignal conversion function:
def wazuh_alert_to_threat_signal(alert: dict) -> ThreatSignal:
    # ... existing mapping code ...
    signal = ThreatSignal(
        # ... existing fields ...
        mitre_hints=extract_mitre_hints_from_wazuh(alert)  # ADD THIS
    )
    return signal
```

**In CoordinatorAgent._build_agent_contexts()**, pass the hints to ContextAgent and PriorityAgent:

```python
def _build_agent_contexts(self, signal: ThreatSignal) -> dict:
    # ... existing context building ...
    
    # Add mitre_hints to context for ContextAgent and PriorityAgent
    context["context"]["mitre_hints"] = signal.mitre_hints
    context["priority"]["mitre_hints"] = signal.mitre_hints
    
    return context
```

**In CoordinatorAgent._synthesize_analysis()**, collect and merge ATT&CK tags:

```python
from mitre_parser import extract_mitre_tags, merge_mitre_tags
from mitre_fallback import get_fallback_tags

def _synthesize_analysis(self, signal, analyses, elapsed_time) -> ThreatAnalysis:
    # ... existing synthesis code ...
    
    # Extract MITRE tags from ContextAgent and PriorityAgent outputs
    context_raw = analyses.get("context", {}).get("raw_output", "")
    priority_raw = analyses.get("priority", {}).get("raw_output", "")
    
    context_tags = extract_mitre_tags(context_raw, source="context_agent")
    priority_tags = extract_mitre_tags(priority_raw, source="priority_agent")
    
    # Add Wazuh pass-through tags
    wazuh_tags = [
        MitreTag(
            technique_id=tid,
            technique_name=f"Technique {tid}",  # Will be resolved by lookup if desired
            tactic="Unknown",
            tactic_id="",
            confidence=1.0,
            source="wazuh"
        )
        for tid in signal.mitre_hints
    ]
    
    mitre_tags = merge_mitre_tags(wazuh_tags + context_tags, priority_tags)
    
    # Fallback: if still empty, use deterministic table
    if not mitre_tags:
        fallback = get_fallback_tags(signal.threat_type)
        mitre_tags = [
            MitreTag(source="fallback", confidence=0.6, **tag)
            for tag in fallback
        ]
    
    # ... rest of existing synthesis ...
    
    return ThreatAnalysis(
        # ... all existing fields ...
        mitre_tags=mitre_tags
    )
```

> **Note for Augment Code:** The `raw_output` field may not exist yet in `AgentAnalysis`. If agents currently return only structured fields (confidence, findings, etc.), add a `raw_output: str = ""` field to `AgentAnalysis` and populate it with the full LLM response before parsing. This enables the regex extraction without modifying existing parsed fields.

### 2.6 API Changes

No new endpoints required. The existing `GET /api/threats/{id}` and `GET /api/threats` responses will automatically include `mitre_tags` once the `ThreatAnalysis` model is updated (Pydantic serializes new fields automatically).

Optionally add a convenience endpoint for the demo:

```python
@app.get("/api/mitre/techniques")
async def list_mitre_techniques():
    """Return the fallback ATT&CK lookup table — useful for demo UI."""
    from mitre_fallback import THREAT_TYPE_TO_MITRE
    return {"techniques": THREAT_TYPE_TO_MITRE}
```

### 2.7 Frontend Changes

**New component:** `frontend/src/components/MitreTagBadge.jsx`

```jsx
// Color mapping by tactic
const TACTIC_COLORS = {
  "Initial Access": "bg-red-600",
  "Execution": "bg-orange-600",
  "Persistence": "bg-yellow-600",
  "Privilege Escalation": "bg-amber-600",
  "Defense Evasion": "bg-green-700",
  "Credential Access": "bg-teal-600",
  "Discovery": "bg-blue-600",
  "Lateral Movement": "bg-indigo-600",
  "Collection": "bg-violet-600",
  "Command and Control": "bg-purple-700",
  "Exfiltration": "bg-pink-700",
  "Impact": "bg-rose-700",
  "Reconnaissance": "bg-slate-600",
  "Resource Development": "bg-zinc-600",
};

const SOURCE_ICONS = {
  wazuh: "🔒",
  context_agent: "🤖",
  priority_agent: "⚡",
  fallback: "📋",
};

export function MitreTagBadge({ tag }) {
  const colorClass = TACTIC_COLORS[tag.tactic] || "bg-gray-600";
  const icon = SOURCE_ICONS[tag.source] || "🏷";

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-white text-xs font-mono ${colorClass}`}
         title={`${tag.technique_name} | ${tag.tactic} | Confidence: ${(tag.confidence * 100).toFixed(0)}% | Source: ${tag.source}`}>
      <span>{icon}</span>
      <span className="font-bold">{tag.technique_id}</span>
      <span className="opacity-80 hidden sm:inline">· {tag.tactic}</span>
    </div>
  );
}

export function MitreTagList({ tags }) {
  if (!tags || tags.length === 0) return null;

  return (
    <div className="mt-3">
      <div className="text-xs text-gray-400 uppercase tracking-wider mb-1 font-semibold">
        MITRE ATT&CK
      </div>
      <div className="flex flex-wrap gap-1">
        {tags.map((tag, i) => (
          <MitreTagBadge key={`${tag.technique_id}-${i}`} tag={tag} />
        ))}
      </div>
    </div>
  );
}
```

**Update ThreatDetails component** to include `<MitreTagList tags={threat.mitre_tags} />` in the threat detail view.

**Update ThreatFeed card** to show a compact inline badge list:

```jsx
// In ThreatCard component, after severity badge:
{threat.mitre_tags?.length > 0 && (
  <div className="flex flex-wrap gap-1 mt-1">
    {threat.mitre_tags.slice(0, 2).map((tag, i) => (
      <span key={i} className="text-xs font-mono bg-gray-700 text-gray-300 px-1 rounded">
        {tag.technique_id}
      </span>
    ))}
    {threat.mitre_tags.length > 2 && (
      <span className="text-xs text-gray-500">+{threat.mitre_tags.length - 2} more</span>
    )}
  </div>
)}
```

### 2.8 Implementation Steps

```
Step 1: Backend models (30 min)
  □ Add MitreTag to models.py
  □ Add mitre_tags: List[MitreTag] = [] to ThreatAnalysis
  □ Add mitre_hints: List[str] = [] to ThreatSignal

Step 2: Fallback table (20 min)
  □ Create backend/src/mitre_fallback.py with THREAT_TYPE_TO_MITRE dict

Step 3: Parser utility (20 min)
  □ Create backend/src/mitre_parser.py with extract_mitre_tags() and merge_mitre_tags()

Step 4: Update agent prompts (45 min)
  □ Update ContextAgent.get_system_prompt() to include <MITRE_TAGS> output instruction
  □ Update PriorityAgent.get_system_prompt() to validate and extend tags
  □ Ensure AgentAnalysis has raw_output: str = "" field
  □ Store full LLM response in raw_output before parsing

Step 5: Wazuh connector (20 min)
  □ Add extract_mitre_hints_from_wazuh() to wazuh connector
  □ Populate signal.mitre_hints in wazuh_alert_to_threat_signal()

Step 6: CoordinatorAgent synthesis (30 min)
  □ Pass mitre_hints to ContextAgent and PriorityAgent contexts
  □ Extract and merge tags in _synthesize_analysis()
  □ Apply fallback if empty

Step 7: Frontend (45 min)
  □ Create MitreTagBadge.jsx and MitreTagList.jsx
  □ Update ThreatDetails to include MitreTagList
  □ Update ThreatCard to show compact badge preview

Step 8: Test (20 min)
  □ Trigger a bot_traffic threat, verify mitre_tags in API response
  □ Trigger a Wazuh alert with known ATT&CK mapping, verify pass-through
  □ Verify fallback fires when LLM output has no <MITRE_TAGS> block
```

---

## 3. Feature 2: Live Threat Intelligence Feed

### 3.1 Spec and Objectives

**Goal:** The `HistoricalAgent` enriches every threat analysis with live IOC (Indicator of Compromise) cross-references from two free public feeds:

1. **CISA KEV (Known Exploited Vulnerabilities Catalog)** — CVE IDs of vulnerabilities being actively exploited in the wild. JSON feed updated daily. No API key required.
2. **AlienVault OTX (Open Threat Exchange)** — IP addresses, domains, file hashes, and CVEs associated with known threat actors and malware campaigns. Free API with key.

**Enrichment output in ThreatAnalysis:**
```json
"intel_matches": [
  {
    "ioc_type": "cve",
    "ioc_value": "CVE-2024-21413",
    "source": "cisa_kev",
    "description": "Microsoft Outlook Remote Code Execution",
    "date_added": "2024-02-13",
    "confidence": 0.95,
    "threat_actor": null
  },
  {
    "ioc_type": "ip",
    "ioc_value": "185.220.101.45",
    "source": "otx",
    "description": "Tor exit node associated with credential stuffing campaigns",
    "date_added": "2024-11-02",
    "confidence": 0.78,
    "threat_actor": "Anonymous"
  }
]
```

**If no matches found:** `intel_matches` is an empty list. This is normal and expected for many threat signals.

### 3.2 Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                 LIVE INTEL FEED ARCHITECTURE                          │
│                                                                        │
│  BACKGROUND REFRESH (startup + periodic)                               │
│  ┌────────────────────┐    ┌──────────────────────────────────────┐   │
│  │ IntelFeedRefresher │───▶│ Redis Cache                          │   │
│  │ (runs on startup + │    │                                      │   │
│  │  every 4h / 1h)    │    │ Key: intel:cisa_kev (TTL: 4h)       │   │
│  │                    │    │ Value: List[CisaKevEntry] (JSON)     │   │
│  │ Fetches:           │    │                                      │   │
│  │ • CISA KEV JSON    │    │ Key: intel:otx_pulses (TTL: 1h)     │   │
│  │ • OTX latest 100  │    │ Value: List[OtxPulse] (JSON)         │   │
│  │   pulses          │    └──────────────────────────────────────┘   │
│  └────────────────────┘                                               │
│                                      │                                │
│  ANALYSIS PIPELINE                   │                                │
│  HistoricalAgent.analyze()           │                                │
│       │                              │                                │
│       ▼                              ▼                                │
│  IntelEnricher.match(signal) ← reads from Redis cache                 │
│       │                                                               │
│       ├── match_cisa_kev(signal)                                      │
│       │   → Checks signal source_ip, CVEs, software versions         │
│       │     against CISA KEV catalog                                  │
│       │                                                               │
│       └── match_otx(signal)                                           │
│           → Checks signal source_ip, domain, file_hash               │
│             against OTX pulse IOCs                                    │
│                                                                        │
│  Results → HistoricalAgent.metadata['intel_matches']                  │
│  → CoordinatorAgent._synthesize_analysis() picks up                   │
│  → ThreatAnalysis.intel_matches populated                             │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Sources

#### CISA KEV Feed

- **URL:** `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
- **Auth:** None required
- **Update frequency:** Daily (CISA updates the catalog as new exploited CVEs are confirmed)
- **Format:** JSON array of `{cveID, vendorProject, product, vulnerabilityName, dateAdded, shortDescription, requiredAction, dueDate}`
- **Cache TTL:** 4 hours
- **Size:** ~1,200 entries as of 2026, ~200KB uncompressed

**Matching logic:** Cross-reference against:
- CVE IDs mentioned in Wazuh rule descriptions (e.g., `rule.description` contains "CVE-2024-")
- Software names extracted from signal metadata (e.g., `vendorProject` or `product` appearing in threat description)

#### AlienVault OTX Feed

- **Base URL:** `https://otx.alienvault.com/api/v1/`
- **Auth:** Free API key (sign up at otx.alienvault.com)
- **Endpoint used:** `GET /pulses/subscribed?limit=100&modified_since={timestamp}`
- **Also used:** `GET /indicators/IPv4/{ip}/general` for direct IP lookup
- **Cache TTL:** 1 hour for pulse list; 15 minutes for individual IP lookups
- **Config:** Requires `OTX_API_KEY` environment variable

**Matching logic:**
- Direct IP match: `source_ip` from signal against IOC lists in OTX pulses
- Domain match: any domain extracted from signal
- Hash match: any file hash (SHA256/MD5) in signal metadata

### 3.4 Intel Cache Layer

**New file:** `backend/src/intel_cache.py`

```python
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
OTX_BASE_URL = "https://otx.alienvault.com/api/v1"
CISA_CACHE_KEY = "intel:cisa_kev"
OTX_PULSES_CACHE_KEY = "intel:otx_pulses"
CISA_TTL_SECONDS = 4 * 3600      # 4 hours
OTX_TTL_SECONDS = 1 * 3600       # 1 hour
OTX_IP_TTL_SECONDS = 15 * 60     # 15 minutes


class IntelFeedCache:
    def __init__(self, redis_client: aioredis.Redis, otx_api_key: Optional[str] = None):
        self.redis = redis_client
        self.otx_api_key = otx_api_key
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    # ─── CISA KEV ────────────────────────────────────────────────────────────

    async def refresh_cisa_kev(self) -> bool:
        """Fetch CISA KEV and store in Redis. Returns True on success."""
        try:
            logger.info("Refreshing CISA KEV feed...")
            response = await self.http.get(CISA_KEV_URL)
            response.raise_for_status()
            data = response.json()
            
            vulnerabilities = data.get("vulnerabilities", [])
            # Build indexed dict for fast CVE ID lookup
            indexed = {v["cveID"]: v for v in vulnerabilities}
            
            await self.redis.set(
                CISA_CACHE_KEY,
                json.dumps(indexed),
                ex=CISA_TTL_SECONDS
            )
            logger.info(f"CISA KEV cache refreshed: {len(indexed)} entries")
            return True
        
        except Exception as e:
            logger.warning(f"CISA KEV refresh failed: {e}")
            return False

    async def get_cisa_kev(self) -> dict:
        """Get CISA KEV dict from cache. Returns empty dict if unavailable."""
        try:
            raw = await self.redis.get(CISA_CACHE_KEY)
            if raw:
                return json.loads(raw)
            # Cache miss — attempt refresh
            await self.refresh_cisa_kev()
            raw = await self.redis.get(CISA_CACHE_KEY)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    async def lookup_cve(self, cve_id: str) -> Optional[dict]:
        """Look up a specific CVE in CISA KEV. Returns entry or None."""
        kev = await self.get_cisa_kev()
        return kev.get(cve_id.upper())

    # ─── OTX ─────────────────────────────────────────────────────────────────

    async def refresh_otx_pulses(self) -> bool:
        """Fetch recent OTX pulses and store in Redis. Returns True on success."""
        if not self.otx_api_key:
            logger.debug("OTX_API_KEY not configured, skipping OTX refresh")
            return False
        
        try:
            logger.info("Refreshing OTX pulses...")
            since = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
            
            headers = {"X-OTX-API-KEY": self.otx_api_key}
            response = await self.http.get(
                f"{OTX_BASE_URL}/pulses/subscribed",
                params={"limit": 100, "modified_since": since},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            pulses = data.get("results", [])
            
            # Build IP/domain/hash → pulse mapping for fast lookup
            ip_index: dict[str, list] = {}
            domain_index: dict[str, list] = {}
            hash_index: dict[str, list] = {}
            
            for pulse in pulses:
                pulse_summary = {
                    "name": pulse.get("name", ""),
                    "description": pulse.get("description", ""),
                    "author_name": pulse.get("author_name", ""),
                    "created": pulse.get("created", ""),
                    "tags": pulse.get("tags", []),
                    "malware_families": pulse.get("malware_families", []),
                    "adversary": pulse.get("adversary", ""),
                }
                for indicator in pulse.get("indicators", []):
                    ioc_type = indicator.get("type", "")
                    ioc_value = indicator.get("indicator", "")
                    if ioc_type == "IPv4":
                        ip_index.setdefault(ioc_value, []).append(pulse_summary)
                    elif ioc_type in ("domain", "hostname"):
                        domain_index.setdefault(ioc_value.lower(), []).append(pulse_summary)
                    elif ioc_type in ("FileHash-SHA256", "FileHash-MD5"):
                        hash_index.setdefault(ioc_value.lower(), []).append(pulse_summary)
            
            payload = {
                "ip_index": ip_index,
                "domain_index": domain_index,
                "hash_index": hash_index,
                "refreshed_at": datetime.utcnow().isoformat()
            }
            await self.redis.set(OTX_PULSES_CACHE_KEY, json.dumps(payload), ex=OTX_TTL_SECONDS)
            logger.info(f"OTX cache refreshed: {len(ip_index)} IPs, {len(domain_index)} domains")
            return True
        
        except Exception as e:
            logger.warning(f"OTX pulse refresh failed: {e}")
            return False

    async def get_otx_index(self) -> dict:
        """Get OTX index from cache. Returns empty dict if unavailable."""
        try:
            raw = await self.redis.get(OTX_PULSES_CACHE_KEY)
            if raw:
                return json.loads(raw)
            await self.refresh_otx_pulses()
            raw = await self.redis.get(OTX_PULSES_CACHE_KEY)
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    async def lookup_ip(self, ip: str) -> list[dict]:
        """Look up an IP in the OTX pulse index. Returns matching pulses."""
        index = await self.get_otx_index()
        return index.get("ip_index", {}).get(ip, [])

    async def lookup_domain(self, domain: str) -> list[dict]:
        """Look up a domain in the OTX pulse index. Returns matching pulses."""
        index = await self.get_otx_index()
        return index.get("domain_index", {}).get(domain.lower(), [])

    # ─── Background Refresh ──────────────────────────────────────────────────

    async def start_background_refresh(self):
        """Start background task to refresh caches periodically."""
        # Initial refresh on startup
        await asyncio.gather(
            self.refresh_cisa_kev(),
            self.refresh_otx_pulses(),
            return_exceptions=True
        )
        
        # Schedule periodic refresh
        asyncio.create_task(self._periodic_refresh())

    async def _periodic_refresh(self):
        """Refresh caches every hour for OTX and every 4 hours for CISA."""
        otx_interval = 3600       # 1 hour
        cisa_interval = 4 * 3600  # 4 hours
        
        otx_countdown = otx_interval
        cisa_countdown = cisa_interval
        
        while True:
            await asyncio.sleep(300)  # Check every 5 minutes
            otx_countdown -= 300
            cisa_countdown -= 300
            
            if otx_countdown <= 0:
                await self.refresh_otx_pulses()
                otx_countdown = otx_interval
            
            if cisa_countdown <= 0:
                await self.refresh_cisa_kev()
                cisa_countdown = cisa_interval
```

### 3.5 HistoricalAgent Integration

**New file:** `backend/src/intel_enricher.py`

```python
import re
from typing import List, Optional
from models import IntelMatch
from intel_cache import IntelFeedCache


class IntelEnricher:
    def __init__(self, cache: IntelFeedCache):
        self.cache = cache

    async def enrich(self, signal_data: dict) -> List[IntelMatch]:
        """
        Run all intel enrichment checks in parallel.
        Returns list of IntelMatch objects. Never raises exceptions.
        """
        try:
            import asyncio
            cisa_matches, otx_matches = await asyncio.gather(
                self._check_cisa_kev(signal_data),
                self._check_otx(signal_data),
                return_exceptions=True
            )
            
            results = []
            if isinstance(cisa_matches, list):
                results.extend(cisa_matches)
            if isinstance(otx_matches, list):
                results.extend(otx_matches)
            
            return results[:10]  # Cap at 10 matches max
        
        except Exception:
            return []  # Never block analysis pipeline

    async def _check_cisa_kev(self, signal_data: dict) -> List["IntelMatch"]:
        """Check if signal relates to a known exploited CVE."""
        matches = []
        
        # Extract CVE IDs from signal description, rule info, or metadata
        text_to_search = " ".join([
            signal_data.get("description", ""),
            signal_data.get("rule_description", ""),
            str(signal_data.get("metadata", {})),
        ])
        
        cve_ids = re.findall(r'CVE-\d{4}-\d+', text_to_search, re.IGNORECASE)
        cve_ids = list(set(cve_ids))  # Deduplicate
        
        for cve_id in cve_ids[:5]:  # Max 5 CVE lookups
            entry = await self.cache.lookup_cve(cve_id.upper())
            if entry:
                matches.append(IntelMatch(
                    ioc_type="cve",
                    ioc_value=cve_id.upper(),
                    source="cisa_kev",
                    description=f"{entry.get('vulnerabilityName', '')} — {entry.get('vendorProject', '')} {entry.get('product', '')}",
                    date_added=entry.get("dateAdded", ""),
                    confidence=0.95,
                    threat_actor=None
                ))
        
        return matches

    async def _check_otx(self, signal_data: dict) -> List["IntelMatch"]:
        """Check signal IOCs against OTX threat intel."""
        matches = []
        
        # Check source IP
        source_ip = signal_data.get("source_ip", "")
        if source_ip and source_ip not in ("0.0.0.0", "127.0.0.1"):
            pulses = await self.cache.lookup_ip(source_ip)
            for pulse in pulses[:2]:  # Max 2 matches per IP
                matches.append(IntelMatch(
                    ioc_type="ip",
                    ioc_value=source_ip,
                    source="otx",
                    description=pulse.get("name", "Unknown campaign"),
                    date_added=pulse.get("created", "")[:10] if pulse.get("created") else "",
                    confidence=0.80,
                    threat_actor=pulse.get("adversary") or (
                        pulse["malware_families"][0] if pulse.get("malware_families") else None
                    )
                ))
        
        # Check domain if present
        domain = signal_data.get("domain", "")
        if domain:
            pulses = await self.cache.lookup_domain(domain)
            for pulse in pulses[:2]:
                matches.append(IntelMatch(
                    ioc_type="domain",
                    ioc_value=domain,
                    source="otx",
                    description=pulse.get("name", "Unknown campaign"),
                    date_added=pulse.get("created", "")[:10] if pulse.get("created") else "",
                    confidence=0.82,
                    threat_actor=pulse.get("adversary") or None
                ))
        
        return matches
```

**Update HistoricalAgent** to call the enricher:

```python
class HistoricalAgent(BaseAgent):
    
    def __init__(self, client, intel_enricher: Optional[IntelEnricher] = None):
        super().__init__(client)
        self.intel_enricher = intel_enricher  # Injected by Coordinator

    async def analyze(self, signal: ThreatSignal, context: dict) -> AgentAnalysis:
        # ... existing analysis logic ...
        result = await super().analyze(signal, context)
        
        # Run intel enrichment in parallel with no blocking
        intel_matches = []
        if self.intel_enricher:
            signal_dict = signal.dict() if hasattr(signal, 'dict') else vars(signal)
            intel_matches = await self.intel_enricher.enrich(signal_dict)
        
        # Store in metadata for coordinator to pick up
        if result.metadata is None:
            result.metadata = {}
        result.metadata["intel_matches"] = [m.dict() for m in intel_matches]
        
        return result
```

**Update CoordinatorAgent** to initialize enricher and pass to HistoricalAgent, then collect intel_matches in synthesis:

```python
class CoordinatorAgent:
    def __init__(self, ..., intel_cache: Optional[IntelFeedCache] = None):
        # ... existing init ...
        enricher = IntelEnricher(intel_cache) if intel_cache else None
        self.historical_agent = HistoricalAgent(client=self.client, intel_enricher=enricher)
    
    def _synthesize_analysis(self, signal, analyses, elapsed_time) -> ThreatAnalysis:
        # ... existing synthesis ...
        
        # Collect intel matches from HistoricalAgent
        historical_metadata = analyses.get("historical", {}).get("metadata", {})
        raw_intel = historical_metadata.get("intel_matches", [])
        intel_matches = [IntelMatch(**m) for m in raw_intel if isinstance(m, dict)]
        
        return ThreatAnalysis(
            # ... all existing fields ...
            intel_matches=intel_matches,
        )
```

**In main.py**, initialize the cache and pass to coordinator on startup:

```python
from intel_cache import IntelFeedCache
import os

@app.on_event("startup")
async def startup_event():
    # ... existing startup code ...
    
    # Initialize intel cache
    redis_client = app.state.redis  # Use existing Redis client
    otx_api_key = os.getenv("OTX_API_KEY")
    
    intel_cache = IntelFeedCache(redis_client=redis_client, otx_api_key=otx_api_key)
    app.state.intel_cache = intel_cache
    
    # Start background refresh (non-blocking)
    asyncio.create_task(intel_cache.start_background_refresh())
    
    # Pass to coordinator
    app.state.coordinator = CoordinatorAgent(..., intel_cache=intel_cache)
```

### 3.6 Data Models

**New Pydantic model** — add to `backend/src/models.py`:

```python
class IntelMatch(BaseModel):
    ioc_type: str           # "ip" | "domain" | "cve" | "hash"
    ioc_value: str          # The actual IOC value
    source: str             # "cisa_kev" | "otx"
    description: str        # Human-readable description
    date_added: str = ""    # ISO date string when IOC was added to feed
    confidence: float = 0.8 # 0.0–1.0
    threat_actor: Optional[str] = None  # Threat actor name if known
```

### 3.7 API Changes

Add a cache status endpoint useful for the demo:

```python
@app.get("/api/intel/status")
async def intel_status():
    """Return intel feed cache status — useful for demo."""
    cache: IntelFeedCache = app.state.intel_cache
    
    cisa_raw = await cache.redis.get("intel:cisa_kev")
    otx_raw = await cache.redis.get("intel:otx_pulses")
    
    cisa_data = json.loads(cisa_raw) if cisa_raw else {}
    otx_data = json.loads(otx_raw) if otx_raw else {}
    
    return {
        "cisa_kev": {
            "loaded": bool(cisa_data),
            "entry_count": len(cisa_data),
            "ttl_seconds": await cache.redis.ttl("intel:cisa_kev")
        },
        "otx": {
            "loaded": bool(otx_data),
            "ip_count": len(otx_data.get("ip_index", {})),
            "domain_count": len(otx_data.get("domain_index", {})),
            "refreshed_at": otx_data.get("refreshed_at"),
            "ttl_seconds": await cache.redis.ttl("intel:otx_pulses")
        }
    }
```

### 3.8 Frontend Changes

**New component:** `frontend/src/components/IntelMatchCard.jsx`

```jsx
const SOURCE_LABELS = {
  cisa_kev: { label: "CISA KEV", color: "border-red-500 bg-red-950 text-red-200" },
  otx: { label: "OTX Intel", color: "border-orange-500 bg-orange-950 text-orange-200" },
};

const IOC_TYPE_ICONS = {
  ip: "🌐",
  domain: "🔗",
  cve: "⚠️",
  hash: "#️⃣",
};

export function IntelMatchCard({ match }) {
  const sourceStyle = SOURCE_LABELS[match.source] || {
    label: match.source, color: "border-gray-500 bg-gray-900 text-gray-300"
  };
  const icon = IOC_TYPE_ICONS[match.ioc_type] || "🏷";

  return (
    <div className={`rounded border p-3 text-sm ${sourceStyle.color}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold font-mono">{icon} {match.ioc_value}</span>
        <span className="text-xs px-1.5 py-0.5 rounded bg-black bg-opacity-30 font-semibold">
          {sourceStyle.label}
        </span>
      </div>
      <div className="text-xs opacity-80">{match.description}</div>
      {match.threat_actor && (
        <div className="text-xs mt-1 opacity-60">Actor: {match.threat_actor}</div>
      )}
      <div className="flex justify-between items-center mt-1">
        <span className="text-xs opacity-50">{match.date_added}</span>
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
        <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
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

**Update ThreatDetails** to include `<IntelMatchSection matches={threat.intel_matches} />`.

**Add intel status indicator** to dashboard header (small green/red dot showing whether feeds are live):

```jsx
// In Dashboard header
function IntelFeedStatus() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetch("/api/intel/status")
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  if (!status) return null;

  const isLive = status.cisa_kev.loaded;
  return (
    <span className="flex items-center gap-1 text-xs text-gray-400"
          title={`CISA KEV: ${status.cisa_kev.entry_count} entries | OTX: ${status.otx.ip_count} IPs`}>
      <span className={`w-2 h-2 rounded-full ${isLive ? "bg-green-400" : "bg-gray-600"}`}></span>
      Intel
    </span>
  );
}
```

### 3.9 Implementation Steps

```
Step 1: Data models (15 min)
  □ Add IntelMatch to models.py
  □ Add intel_matches: List[IntelMatch] = [] to ThreatAnalysis

Step 2: Intel cache layer (60 min)
  □ Create backend/src/intel_cache.py (full IntelFeedCache class)
  □ Verify CISA KEV URL is accessible and JSON parses correctly
  □ Test OTX API key auth if available

Step 3: Intel enricher (30 min)
  □ Create backend/src/intel_enricher.py
  □ Implement _check_cisa_kev() with CVE regex extraction
  □ Implement _check_otx() with IP and domain matching

Step 4: HistoricalAgent update (20 min)
  □ Add intel_enricher parameter to __init__()
  □ Call enricher in analyze() and store results in metadata

Step 5: CoordinatorAgent update (20 min)
  □ Accept intel_cache parameter in __init__()
  □ Initialize IntelEnricher and inject into HistoricalAgent
  □ Collect intel_matches in _synthesize_analysis()

Step 6: Main.py startup (20 min)
  □ Initialize IntelFeedCache on startup
  □ Start background refresh task
  □ Pass cache to coordinator
  □ Add /api/intel/status endpoint

Step 7: Environment variable (5 min)
  □ Add OTX_API_KEY to .env.example with comment
  □ Document that system works without OTX key (CISA only)

Step 8: Frontend (45 min)
  □ Create IntelMatchCard.jsx and IntelMatchSection.jsx
  □ Update ThreatDetails to show IntelMatchSection
  □ Add IntelFeedStatus indicator to dashboard header

Step 9: Test (20 min)
  □ GET /api/intel/status — verify CISA KEV loads on startup
  □ Trigger threat with a CVE ID in description — verify intel_matches
  □ If OTX key configured, verify IP lookup works
  □ Verify empty intel_matches doesn't break anything
```

---

## 4. End-to-End Demo Flow

### 4.1 Full Pipeline Narrative

Once both features are complete, the full pipeline from pentest to ATT&CK-tagged, intel-enriched analysis:

```
1. Metasploit scan runs against test target
         │
         ▼
2. Wazuh fires alert with rule ATT&CK mapping
   {rule.id: "100007", rule.description: "Port scan detected",
    rule.mitre.technique: ["T1046"], rule.level: 10}
         │
         ▼
3. Wazuh connector normalizes to ThreatSignal
   {threat_type: "port_scan", source_ip: "192.168.1.42",
    mitre_hints: ["T1046"]}
         │
         ▼
4. CoordinatorAgent fans out 5 agents in parallel
   - HistoricalAgent: runs intel enrichment on source_ip
   - ContextAgent: generates ATT&CK tags with <MITRE_TAGS> block
   - PriorityAgent: validates and extends ATT&CK tags
   - ConfigAgent, DevOpsAgent: existing analysis unchanged
         │
         ▼
5. Synthesis produces ThreatAnalysis with:
   mitre_tags: [
     {technique_id: "T1046", tactic: "Discovery", source: "wazuh"},
     {technique_id: "T1595.001", tactic: "Reconnaissance", source: "context_agent"},
   ]
   intel_matches: [
     {ioc_type: "ip", ioc_value: "192.168.1.42", source: "otx",
      description: "Tor exit node", threat_actor: "Unknown"}
   ]
         │
         ▼
6. React dashboard shows:
   - MITRE ATT&CK badges: 🔵 T1046 · Discovery  🔵 T1595.001 · Reconnaissance
   - Intel panel: 🌐 192.168.1.42 | OTX Intel | Tor exit node
   - Forensic timeline with full agent trace
```

### 4.2 Demo Script for Michael Spisak

**[0:00 — 0:20] Set the scene:**
> "I ran a Metasploit port scan against a test device. Wazuh fired an alert. Let me show you what the AI SOC system does with it."

**[0:20 — 0:60] Show the threat in the dashboard:**
> "Here's the alert coming in. You can see five agents ran in parallel — Historical, Config, DevOps, Context, Priority. Total processing time: under 10 seconds."

**[0:60 — 1:30] Point to MITRE ATT&CK tags:**
> "The Context Agent auto-tagged MITRE ATT&CK techniques — T1046 Network Service Discovery was passed through directly from the Wazuh rule, T1595 was added by the LLM based on the attack pattern. These are color-coded by tactic. Every analyst on your team speaks this language."

**[1:30 — 2:00] Point to intel enrichment:**
> "The Historical Agent cross-referenced the source IP against live feeds — CISA's Known Exploited Vulnerabilities catalog and OTX pulse data. That green dot up top means the feeds are live, refreshed an hour ago."

**[2:00 — 2:30] Switch to red-team mode:**
> "Now here's the part that maps to your agentic attack framework research — I added a red-team mode. Watch what happens when I inject a crafted signal designed to manipulate the coordinator's synthesis step..."

**[2:30 — 3:00] Show adversarial injection:**
> "The FP Analyzer flagged the contradiction between agents — Priority Agent and Historical Agent disagree on severity in a statistically improbable way. That's your detection signal for adversarial agent manipulation. The challenge is building a system that's defensively robust to the same multi-agent attack patterns your team published."

---

## 5. File Change Map

| File | Change Type | Description |
|---|---|---|
| `backend/src/models.py` | Modify | Add `MitreTag`, `IntelMatch`; update `ThreatAnalysis`, `ThreatSignal` |
| `backend/src/mitre_fallback.py` | Create | Deterministic threat_type → ATT&CK lookup table |
| `backend/src/mitre_parser.py` | Create | `extract_mitre_tags()`, `merge_mitre_tags()` utilities |
| `backend/src/intel_cache.py` | Create | `IntelFeedCache` class with CISA KEV + OTX fetch/cache |
| `backend/src/intel_enricher.py` | Create | `IntelEnricher` class, `enrich()`, `_check_cisa_kev()`, `_check_otx()` |
| `backend/src/agents/context_agent.py` | Modify | Updated system prompt with `<MITRE_TAGS>` output block |
| `backend/src/agents/priority_agent.py` | Modify | Updated system prompt to validate/extend ATT&CK tags |
| `backend/src/agents/historical_agent.py` | Modify | Inject `IntelEnricher`, call in `analyze()`, store in metadata |
| `backend/src/agents/base_agent.py` | Modify | Add `raw_output: str = ""` to `AgentAnalysis` if not present |
| `backend/src/coordinator.py` | Modify | Accept `intel_cache`, init enricher, collect mitre_tags + intel_matches in synthesis |
| `backend/src/wazuh_connector.py` | Modify | Add `extract_mitre_hints_from_wazuh()`, populate `mitre_hints` |
| `backend/src/main.py` | Modify | Initialize `IntelFeedCache` on startup, add `/api/intel/status` |
| `backend/.env.example` | Modify | Add `OTX_API_KEY=` with comment |
| `backend/requirements.txt` | Modify | Add `httpx>=0.27.0` if not present |
| `frontend/src/components/MitreTagBadge.jsx` | Create | Badge component with tactic color coding |
| `frontend/src/components/IntelMatchCard.jsx` | Create | Intel match card component |
| `frontend/src/components/ThreatDetails.jsx` | Modify | Add `MitreTagList` and `IntelMatchSection` |
| `frontend/src/components/ThreatCard.jsx` | Modify | Add compact ATT&CK badge preview |
| `frontend/src/components/Dashboard.jsx` | Modify | Add `IntelFeedStatus` indicator to header |

---

## 6. Testing Checklist

### Feature 1: MITRE ATT&CK Tagging

```
□ Trigger bot_traffic → ThreatAnalysis.mitre_tags contains ≥1 tag
□ Trigger Wazuh alert with rule.mitre.technique = ["T1046"] → mitre_tags includes T1046 with source="wazuh"
□ Simulate ContextAgent returning no <MITRE_TAGS> block → fallback fires, still returns tags
□ Simulate both agents returning empty → fallback fires
□ Verify MitreTagBadge renders correctly for each tactic color
□ Verify existing tests still pass (ATT&CK fields are additive only)
```

### Feature 2: Live Intel Feed

```
□ GET /api/intel/status on startup → cisa_kev.loaded = true
□ Verify CISA KEV has >1000 entries after load
□ Trigger threat with "CVE-2024-21413" in description → intel_matches contains CISA KEV entry
□ If OTX key present: trigger threat with known-bad IP in source_ip → intel_matches contains OTX entry
□ Trigger threat with clean IP → intel_matches is empty list (not error)
□ Stop Redis, trigger threat → analysis completes (no crash), intel_matches is []
□ Verify IntelFeedStatus dot is green when cache is loaded
□ Verify IntelMatchSection renders correctly, does not render when intel_matches is []
```

### End-to-End

```
□ Full Wazuh → AI SOC pipeline: verify both mitre_tags and intel_matches populated
□ Red-team mode demo: adversarial injection still works after new features
□ Performance: total analysis time still <15s with both features enabled
```

---

## 7. Environment Variables

Add to `backend/.env.example`:

```env
# ─── Threat Intelligence Feeds ─────────────────────────────────────────────

# AlienVault OTX API Key (optional — system works without it, CISA KEV still loads)
# Sign up free at: https://otx.alienvault.com
# Without this key: only CISA KEV enrichment is active
OTX_API_KEY=

# CISA KEV feed URL (default is fine, override only if using a mirror)
# CISA_KEV_URL=https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json

# Intel cache TTLs (seconds) — defaults shown
# CISA_CACHE_TTL=14400     # 4 hours
# OTX_CACHE_TTL=3600       # 1 hour
# OTX_IP_CACHE_TTL=900     # 15 minutes
```
