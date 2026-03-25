# Feature Spec: MITRE ATT&CK Tactic Tagging
### AI SOC Agent System — For Augment Code

**Version:** 1.1 (Consolidated)
**Date:** March 22, 2026
**Status:** Ready for Implementation
**Depends on:** Wazuh connector (already built)

---

## Table of Contents

1. [Objectives](#1-objectives)
2. [Architecture Overview](#2-architecture-overview)
3. [Tagging Source Priority Chain](#3-tagging-source-priority-chain)
4. [Data Models](#4-data-models)
5. [Wazuh Pass-Through](#5-wazuh-pass-through)
6. [PriorityAgent — Updated System Prompt](#6-priorityagent--updated-system-prompt)
7. [Parser Utility](#7-parser-utility)
8. [Keyword Fallback Table](#8-keyword-fallback-table)
9. [CoordinatorAgent — Synthesis Changes](#9-coordinatoragent--synthesis-changes)
10. [API Changes](#10-api-changes)
11. [Frontend Components](#11-frontend-components)
12. [File Change Map](#12-file-change-map)
13. [Implementation Steps](#13-implementation-steps)
14. [Testing Checklist](#14-testing-checklist)

---

## 1. Objectives

Every `ThreatAnalysis` output must include one or more MITRE ATT&CK Technique IDs automatically derived from the incoming Wazuh alert and agent analysis.

**Key design decisions:**
- **Single agent** — MITRE tagging is done in **PriorityAgent only**. It already consumes ContextAgent's full output, so it has all context needed. No redundant tagging in ContextAgent.
- **No external DB, Redis store, or RAG required** — the LLM has the full MITRE ATT&CK framework (both Enterprise and Mobile matrices) in its training data. No infrastructure needed for tag lookups.
- **Deterministic fallback** — a keyword table covers the case where LLM output contains no valid tags.
- **Additive only** — `mitre_tags` is a new optional field with `= []` default. No existing fields are modified. No existing tests break.
- **Never blocks the pipeline** — all tagging logic is wrapped in `try/except` and returns gracefully on any failure.

**Output example:**
```json
"mitre_tags": [
  {
    "technique_id": "T1533",
    "technique_name": "Data from Local System",
    "tactic": "Collection",
    "tactic_id": "TA0035",
    "confidence": 0.88,
    "source": "priority_agent"
  },
  {
    "technique_id": "T1437",
    "technique_name": "Application Layer Protocol",
    "tactic": "Command and Control",
    "tactic_id": "TA0037",
    "confidence": 0.91,
    "source": "priority_agent"
  },
  {
    "technique_id": "T1046",
    "technique_name": "Network Service Discovery",
    "tactic": "Discovery",
    "tactic_id": "TA0007",
    "confidence": 1.0,
    "source": "wazuh"
  }
]
```

---

## 2. Architecture Overview

```text
INCOMING WAZUH ALERT
  {rule.mitre.technique: ["T1046"], rule.description: "Port scan detected", ...}
         │
         ▼
WazuhConnector.wazuh_alert_to_threat_signal()
  → extracts rule.mitre.technique[] → ThreatSignal.mitre_hints: ["T1046"]
         │
         ▼
CoordinatorAgent._build_agent_contexts()
  → passes mitre_hints into PriorityAgent context dict
         │
         ▼
PriorityAgent.analyze()  ← already receives full ContextAgent output as context
  → Updated system prompt instructs ATT&CK tagging
  → Outputs <MITRE_TAGS>[...json...]</MITRE_TAGS> block in its response
  → raw_output stored in AgentAnalysis.raw_output
         │
         ▼
CoordinatorAgent._synthesize_analysis()
  → mitre_parser.extract_mitre_tags(priority_raw_output, source="priority_agent")
  → Prepend Wazuh pass-through tags (source="wazuh")
  → If combined list still empty → mitre_fallback.get_fallback_tags(threat_type)
  → Set ThreatAnalysis.mitre_tags
         │
         ▼
React Dashboard
  → MitreTagBadge components, color-coded by tactic
  → Compact preview on ThreatCard (max 2 badges)
  → Full list in ThreatDetails panel
```

---

## 3. Tagging Source Priority Chain

Tags are collected from the following sources and merged in this order. The first non-empty result wins, but Wazuh pass-through tags are **always prepended** regardless.

| Priority | Source | Mechanism | Confidence |
|---|---|---|---|
| 1 | **Wazuh pass-through** | `rule.mitre.technique[]` extracted directly from alert | 1.0 (authoritative) |
| 2 | **PriorityAgent LLM** | `<MITRE_TAGS>` JSON block in agent response | 0.6–0.95 (LLM-assigned) |
| 3 | **Keyword fallback** | `mitre_fallback.py` deterministic lookup table | 0.6 (fixed) |

**Merge rules:**
- Wazuh tags are always included (source="wazuh")
- PriorityAgent tags are deduplicated against Wazuh tags by `technique_id`
- Fallback fires **only** if both Wazuh and PriorityAgent produce zero tags
- Final list capped at **6 techniques maximum**

---

## 4. Data Models

### 4.1 New: MitreTag — add to `backend/src/models.py`

```python
class MitreTag(BaseModel):
    technique_id: str            # e.g. "T1566.001"
    technique_name: str          # e.g. "Spearphishing Attachment"
    tactic: str                  # e.g. "Initial Access"
    tactic_id: str               # e.g. "TA0001"
    confidence: float = 1.0      # 0.0–1.0
    source: str = "priority_agent"  # "wazuh" | "priority_agent" | "fallback"
```

### 4.2 Update: ThreatAnalysis — add optional field

```python
class ThreatAnalysis(BaseModel):
    # ... all existing fields unchanged ...
    mitre_tags: List[MitreTag] = []   # NEW — default empty list
```

### 4.3 Update: ThreatSignal — add mitre_hints from Wazuh

```python
class ThreatSignal(BaseModel):
    # ... all existing fields unchanged ...
    mitre_hints: List[str] = []   # NEW — populated by Wazuh connector
```

### 4.4 Update: AgentAnalysis — ensure raw_output exists

```python
class AgentAnalysis(BaseModel):
    # ... all existing fields unchanged ...
    raw_output: str = ""   # ADD if not already present — stores full LLM response text
```

> **Note for Augment:** If `raw_output` already exists in `AgentAnalysis`, no change needed. The coordinator uses this field to run regex extraction on the full LLM response for the `<MITRE_TAGS>` block. If agents currently don't populate it, add a single line in `BaseAgent.analyze()` to store the raw LLM response string before parsing.

---

## 5. Wazuh Pass-Through

Wazuh rules already encode ATT&CK mappings in `alert.rule.mitre.technique`. Extract these before any LLM call — they are authoritative and require no inference.

**Add to `backend/src/wazuh_connector.py`:**

```python
def extract_mitre_hints_from_wazuh(wazuh_alert: dict) -> list[str]:
    """
    Extract MITRE ATT&CK technique IDs from Wazuh alert rule metadata.
    Wazuh format: alert.rule.mitre.technique = ["T1566", "T1059"]
    Returns list of technique IDs or empty list. Never raises.
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
```

**Update `wazuh_alert_to_threat_signal()`:**

```python
def wazuh_alert_to_threat_signal(alert: dict) -> ThreatSignal:
    # ... existing mapping code ...
    signal = ThreatSignal(
        # ... existing fields ...
        mitre_hints=extract_mitre_hints_from_wazuh(alert)   # ADD THIS LINE
    )
    return signal
```

**Real alert example** (from dev testing):
```json
{
  "rule": {
    "id": "100006",
    "level": 15,
    "description": "Malicious Android app installed: sk.madzik.android.logcatudp",
    "mitre": {
      "technique": ["T1475", "T1533"]
    }
  }
}
```
→ `mitre_hints = ["T1475", "T1533"]` extracted, passed through at `confidence=1.0`

> **Note:** Many Wazuh rules do NOT have `rule.mitre` populated — `mitre_hints` will simply be `[]` in those cases, and the LLM + fallback chain handles tagging.

---

## 6. PriorityAgent — Updated System Prompt

**Only PriorityAgent needs updating.** ContextAgent system prompt is unchanged.

PriorityAgent runs after all other agents and already receives ContextAgent's full output as part of its input context. It therefore has all the information needed to make accurate ATT&CK mappings without any external lookup.

The LLM has the full MITRE ATT&CK Enterprise and Mobile matrices in its training data. For common SOC threat types, technique ID recall is high. The system prompt addition below improves reliability for Mobile ATT&CK (Android/iOS) by explicitly reminding the model to use Mobile tactic IDs.

**Update `PriorityAgent.get_system_prompt()`:**

```python
def get_system_prompt(self) -> str:
    return """You are a senior threat analyst and MITRE ATT&CK expert specializing 
in threat prioritization.

Your responsibilities:
1. Assess threat severity: CRITICAL / HIGH / MEDIUM / LOW
2. Provide prioritization rationale based on context, history, and risk
3. Map the threat to MITRE ATT&CK techniques

## MITRE ATT&CK Tagging Instructions

You MUST include a <MITRE_TAGS> block in every response using this exact format:

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

Rules:
- Include 1–4 techniques maximum
- Only include techniques with confidence >= 0.60
- Use the most SPECIFIC sub-technique when applicable (e.g. T1566.001 not T1566)
- If mitre_hints are provided in the context, include those techniques first 
  with confidence 1.0 and source will be set to "wazuh" by the system
- For Android/iOS threats: use MITRE ATT&CK for Mobile tactic IDs
  (TA0027=Initial Access, TA0041=Execution, TA0028=Persistence, 
   TA0035=Collection, TA0037=Command and Control, TA0036=Exfiltration)
- For network/endpoint threats: use Enterprise ATT&CK tactic IDs
  (TA0001=Initial Access, TA0002=Execution, TA0003=Persistence,
   TA0005=Defense Evasion, TA0006=Credential Access, TA0007=Discovery,
   TA0009=Collection, TA0011=Command and Control, TA0040=Impact)
- Output an empty array [] only if you have absolutely no basis for mapping

## Example: Android malware alert
For an alert about "sk.madzik.android.logcatudp" installed on device:
- T1533 Data from Local System (logcat reads device logs) — Collection TA0035
- T1437 Application Layer Protocol (UDP exfil in package name) — C2 TA0037
- T1475 Deliver Malicious App (package install event) — Initial Access TA0027
"""
```

---

## 7. Parser Utility

**New file: `backend/src/mitre_parser.py`**

```python
import re
import json
from typing import List
from models import MitreTag


def extract_mitre_tags(agent_output: str, source: str = "priority_agent") -> List[MitreTag]:
    """
    Parse <MITRE_TAGS>...</MITRE_TAGS> block from LLM agent output.
    Returns empty list if block not found or JSON is malformed.
    Never raises exceptions — failure returns [] silently.
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
            technique_id = item.get("technique_id", "")
            tactic = item.get("tactic", "")
            if not technique_id or not tactic:
                continue  # Skip malformed entries
            confidence = float(item.get("confidence", 0.8))
            if confidence < 0.6:
                continue  # Skip low-confidence tags
            tags.append(MitreTag(
                technique_id=technique_id,
                technique_name=item.get("technique_name", "Unknown"),
                tactic=tactic,
                tactic_id=item.get("tactic_id", ""),
                confidence=confidence,
                source=source
            ))

        return tags

    except Exception:
        return []  # Never block analysis pipeline for tagging failures


def build_wazuh_tags(mitre_hints: List[str]) -> List[MitreTag]:
    """
    Convert raw Wazuh technique IDs (e.g. ["T1046"]) into MitreTag objects.
    Technique name and tactic are unknown at this stage — PriorityAgent may
    enrich them; the fallback table can also supplement.
    """
    return [
        MitreTag(
            technique_id=tid,
            technique_name=f"Technique {tid}",  # Placeholder; LLM output may provide name
            tactic="Unknown",
            tactic_id="",
            confidence=1.0,
            source="wazuh"
        )
        for tid in mitre_hints
        if tid.startswith("T")
    ]


def merge_mitre_tags(
    wazuh_tags: List[MitreTag],
    priority_tags: List[MitreTag]
) -> List[MitreTag]:
    """
    Merge Wazuh pass-through tags with PriorityAgent tags.
    Wazuh tags always come first. Deduplicates by technique_id.
    Caps result at 6 techniques.
    """
    seen_ids = {tag.technique_id for tag in wazuh_tags}
    merged = list(wazuh_tags)

    for tag in priority_tags:
        if tag.technique_id not in seen_ids:
            merged.append(tag)
            seen_ids.add(tag.technique_id)

    return merged[:6]
```

---

## 8. Keyword Fallback Table

**New file: `backend/src/mitre_fallback.py`**

Fires only when both Wazuh hints and PriorityAgent produce zero valid tags. Covers all common SOC threat types deterministically — no LLM, no network, never fails.

```python
# Maps threat_type (lowercase) → list of ATT&CK technique dicts
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
    ],
    "brute_force": [
        {"technique_id": "T1110.001", "technique_name": "Password Guessing",
         "tactic": "Credential Access", "tactic_id": "TA0006"},
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
    "android_malware": [
        {"technique_id": "T1475", "technique_name": "Deliver Malicious App via Authorized App Store",
         "tactic": "Initial Access", "tactic_id": "TA0027"},
        {"technique_id": "T1533", "technique_name": "Data from Local System",
         "tactic": "Collection", "tactic_id": "TA0035"},
        {"technique_id": "T1437", "technique_name": "Application Layer Protocol",
         "tactic": "Command and Control", "tactic_id": "TA0037"},
    ],
    "device_compromise": [
        {"technique_id": "T1059", "technique_name": "Command and Scripting Interpreter",
         "tactic": "Execution", "tactic_id": "TA0002"},
        {"technique_id": "T1543", "technique_name": "Create or Modify System Process",
         "tactic": "Persistence", "tactic_id": "TA0003"},
    ],
    "network_attack": [
        {"technique_id": "T1046", "technique_name": "Network Service Discovery",
         "tactic": "Discovery", "tactic_id": "TA0007"},
    ],
    "anomaly_detection": [
        {"technique_id": "T1036", "technique_name": "Masquerading",
         "tactic": "Defense Evasion", "tactic_id": "TA0005"},
    ],
}

# Safe default for unknown threat types
_DEFAULT_TAGS = [
    {"technique_id": "T1499", "technique_name": "Endpoint Denial of Service",
     "tactic": "Impact", "tactic_id": "TA0040"}
]


def get_fallback_tags(threat_type: str) -> list[dict]:
    """Return deterministic ATT&CK tags for a given threat type. Never fails."""
    return THREAT_TYPE_TO_MITRE.get(threat_type.lower().replace(" ", "_"), _DEFAULT_TAGS)
```

---

## 9. CoordinatorAgent — Synthesis Changes

**Two changes needed in `coordinator.py`:**

### 9.1 Pass mitre_hints to PriorityAgent context

In `_build_agent_contexts()`:

```python
def _build_agent_contexts(self, signal: ThreatSignal) -> dict:
    # ... existing context building ...

    # Pass Wazuh ATT&CK hints to PriorityAgent
    context["priority"]["mitre_hints"] = signal.mitre_hints
    # Include in context string so LLM sees it:
    if signal.mitre_hints:
        context["priority"]["mitre_hints_note"] = (
            f"Wazuh has already identified these ATT&CK techniques: {signal.mitre_hints}. "
            f"Include these in your <MITRE_TAGS> output with confidence 1.0."
        )

    return context
```

### 9.2 Collect and merge tags in synthesis

In `_synthesize_analysis()`:

```python
from mitre_parser import extract_mitre_tags, build_wazuh_tags, merge_mitre_tags
from mitre_fallback import get_fallback_tags

def _synthesize_analysis(self, signal, analyses, elapsed_time) -> ThreatAnalysis:
    # ... existing synthesis code ...

    # Step 1: Wazuh pass-through tags (always authoritative)
    wazuh_tags = build_wazuh_tags(signal.mitre_hints)

    # Step 2: PriorityAgent LLM tags
    priority_raw = analyses.get("priority", {}).get("raw_output", "")
    priority_tags = extract_mitre_tags(priority_raw, source="priority_agent")

    # Step 3: Merge (Wazuh first, dedup by technique_id, cap at 6)
    mitre_tags = merge_mitre_tags(wazuh_tags, priority_tags)

    # Step 4: Fallback — only if both sources produced nothing
    if not mitre_tags:
        fallback_dicts = get_fallback_tags(signal.threat_type)
        mitre_tags = [
            MitreTag(source="fallback", confidence=0.6, **tag)
            for tag in fallback_dicts
        ]

    return ThreatAnalysis(
        # ... all existing fields unchanged ...
        mitre_tags=mitre_tags   # NEW FIELD
    )
```

---

## 10. API Changes

No new endpoints required. `GET /api/threats/{id}` and `GET /api/threats` automatically include `mitre_tags` via Pydantic serialization once `ThreatAnalysis` is updated.

Optional convenience endpoint for debugging:

```python
@app.get("/api/mitre/fallback")
async def list_mitre_fallback():
    """Return the fallback ATT&CK lookup table — useful for dev/debug."""
    from mitre_fallback import THREAT_TYPE_TO_MITRE
    return {"threat_types": list(THREAT_TYPE_TO_MITRE.keys())}
```

---

## 11. Frontend Components

### 11.1 New file: `frontend/src/components/MitreTagBadge.jsx`

```jsx
const TACTIC_COLORS = {
  "Initial Access":        "bg-red-700",
  "Execution":             "bg-orange-600",
  "Persistence":           "bg-yellow-600",
  "Privilege Escalation":  "bg-amber-600",
  "Defense Evasion":       "bg-green-700",
  "Credential Access":     "bg-teal-600",
  "Discovery":             "bg-blue-600",
  "Lateral Movement":      "bg-indigo-600",
  "Collection":            "bg-violet-600",
  "Command and Control":   "bg-purple-700",
  "Exfiltration":          "bg-pink-700",
  "Impact":                "bg-rose-700",
  "Reconnaissance":        "bg-slate-600",
  "Resource Development":  "bg-zinc-600",
  "Unknown":               "bg-gray-600",
};

const SOURCE_ICONS = {
  wazuh:          "🔒",  // Wazuh pass-through (authoritative)
  priority_agent: "🤖",  // LLM-derived
  fallback:       "📋",  // Deterministic fallback
};

export function MitreTagBadge({ tag }) {
  const colorClass = TACTIC_COLORS[tag.tactic] || "bg-gray-600";
  const icon = SOURCE_ICONS[tag.source] || "🏷";
  const confidencePct = `${(tag.confidence * 100).toFixed(0)}%`;

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-white text-xs font-mono ${colorClass}`}
      title={`${tag.technique_name} | ${tag.tactic} | Confidence: ${confidencePct} | Source: ${tag.source}`}
    >
      <span>{icon}</span>
      <span className="font-bold">{tag.technique_id}</span>
      <span className="opacity-75 hidden sm:inline">· {tag.tactic}</span>
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

### 11.2 Update: ThreatDetails component

Add inside the threat detail panel:

```jsx
import { MitreTagList } from "./MitreTagBadge";

// Inside ThreatDetails render, after severity/priority section:
<MitreTagList tags={threat.mitre_tags} />
```

### 11.3 Update: ThreatCard component

Add compact preview (max 2 badges) on each card in the feed:

```jsx
{threat.mitre_tags?.length > 0 && (
  <div className="flex flex-wrap gap-1 mt-1">
    {threat.mitre_tags.slice(0, 2).map((tag, i) => (
      <span
        key={i}
        className="text-xs font-mono bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded"
      >
        {tag.technique_id}
      </span>
    ))}
    {threat.mitre_tags.length > 2 && (
      <span className="text-xs text-gray-500">
        +{threat.mitre_tags.length - 2} more
      </span>
    )}
  </div>
)}
```

---

## 12. File Change Map

| File | Change | Notes |
|---|---|---|
| `backend/src/models.py` | **Modify** | Add `MitreTag`; add `mitre_tags` to `ThreatAnalysis`; add `mitre_hints` to `ThreatSignal`; add `raw_output` to `AgentAnalysis` if missing |
| `backend/src/mitre_fallback.py` | **Create** | Deterministic threat_type → ATT&CK lookup table |
| `backend/src/mitre_parser.py` | **Create** | `extract_mitre_tags()`, `build_wazuh_tags()`, `merge_mitre_tags()` |
| `backend/src/agents/priority_agent.py` | **Modify** | Updated system prompt with `<MITRE_TAGS>` output block and Mobile ATT&CK guidance |
| `backend/src/agents/base_agent.py` | **Modify** | Ensure `raw_output` is populated with full LLM response string |
| `backend/src/wazuh_connector.py` | **Modify** | Add `extract_mitre_hints_from_wazuh()`; populate `mitre_hints` in signal |
| `backend/src/coordinator.py` | **Modify** | Pass hints to PriorityAgent context; collect + merge tags in synthesis |
| `frontend/src/components/MitreTagBadge.jsx` | **Create** | Badge + list components, tactic color-coded |
| `frontend/src/components/ThreatDetails.jsx` | **Modify** | Add `<MitreTagList>` |
| `frontend/src/components/ThreatCard.jsx` | **Modify** | Add compact ATT&CK badge preview |

**Total: 10 files** (3 new, 7 modified)

---

## 13. Implementation Steps

```
Step 1 — Data models (20 min)
  □ Add MitreTag class to models.py
  □ Add mitre_tags: List[MitreTag] = [] to ThreatAnalysis
  □ Add mitre_hints: List[str] = [] to ThreatSignal
  □ Add raw_output: str = "" to AgentAnalysis (if not present)
  □ Ensure BaseAgent.analyze() stores full LLM response in raw_output

Step 2 — Fallback table (15 min)
  □ Create backend/src/mitre_fallback.py
  □ Verify all threat_types used in your system are covered

Step 3 — Parser utility (20 min)
  □ Create backend/src/mitre_parser.py
  □ Test extract_mitre_tags() with a sample <MITRE_TAGS> block
  □ Test that malformed JSON returns [] without raising

Step 4 — Wazuh connector (15 min)
  □ Add extract_mitre_hints_from_wazuh() to wazuh_connector.py
  □ Call it in wazuh_alert_to_threat_signal() and populate signal.mitre_hints
  □ Test with the sample Android malware alert JSON above

Step 5 — PriorityAgent prompt (20 min)
  □ Update get_system_prompt() with ATT&CK tagging instructions
  □ Include Mobile ATT&CK tactic ID guidance (TA0027–TA0037)
  □ Include the Android malware example in the prompt

Step 6 — CoordinatorAgent synthesis (25 min)
  □ Pass signal.mitre_hints into PriorityAgent context dict
  □ Extract priority_tags from analyses["priority"]["raw_output"]
  □ Call build_wazuh_tags(), merge_mitre_tags(), fallback logic
  □ Assign mitre_tags in ThreatAnalysis constructor

Step 7 — Frontend (40 min)
  □ Create MitreTagBadge.jsx with TACTIC_COLORS and SOURCE_ICONS maps
  □ Update ThreatDetails.jsx to include <MitreTagList>
  □ Update ThreatCard.jsx to show compact 2-badge preview

Step 8 — Test (20 min)
  □ Trigger port_scan alert with rule.mitre.technique → verify wazuh source tags
  □ Trigger Android malware alert → verify Mobile ATT&CK tactic IDs
  □ Simulate PriorityAgent returning no <MITRE_TAGS> → verify fallback fires
  □ Verify existing tests still pass (mitre_tags is additive only)
```

**Estimated total: ~2.5 hours**

---

## 14. Testing Checklist

```
□ ThreatAnalysis JSON includes mitre_tags field (even when empty [])
□ Wazuh alert with rule.mitre.technique populated → tags appear with source="wazuh"
□ Wazuh alert without rule.mitre → mitre_hints=[], LLM tags still generated
□ Android malware alert → Mobile ATT&CK tactic IDs (TA0035, TA0037) in output
□ PriorityAgent returns <MITRE_TAGS>[] empty array → fallback table fires
□ PriorityAgent returns malformed JSON → fallback table fires, no crash
□ PriorityAgent raw_output missing entirely → fallback table fires, no crash
□ Merged list never exceeds 6 techniques
□ Tags with confidence < 0.60 are filtered out
□ MitreTagBadge renders all 14 tactic colors without error
□ ThreatCard shows max 2 badges + "+N more" overflow label
□ All existing tests pass (no regressions from additive model changes)
```
