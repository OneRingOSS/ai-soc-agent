# SOC Agent System - Sequence Flow Diagrams

This document breaks down the complete threat analysis workflow into multiple easy-to-understand sequence diagrams.

---

## Table of Contents

1. [Overview](#overview)
2. [Flow 1: Threat Detection & Ingestion](#flow-1-threat-detection--ingestion)
3. [Flow 2: Parallel Agent Execution](#flow-2-parallel-agent-execution)
4. [Flow 3: Enhanced Analysis (FP, Response, Timeline)](#flow-3-enhanced-analysis-fp-response-timeline)
5. [Flow 4: Result Synthesis & Delivery](#flow-4-result-synthesis--delivery)
6. [Flow 5: WebSocket Real-time Updates](#flow-5-websocket-real-time-updates)

---

## Overview

The complete threat analysis workflow consists of 5 major phases:

1. **Detection & Ingestion** - Threat signal received and validated
2. **Parallel Agent Execution** - 5 specialized agents analyze concurrently
3. **Enhanced Analysis** - FP scoring, response planning, timeline building
4. **Result Synthesis** - Aggregation and final analysis generation
5. **Delivery** - Storage and real-time broadcast to dashboard

**Total Duration**: ~500-1000ms (mock mode) or ~10s (live OpenAI mode)

---

## Flow 1: Threat Detection & Ingestion

This flow shows how threats enter the system and get validated.

```mermaid
sequenceDiagram
    autonumber
    participant User as SOC Analyst
    participant Dashboard as React Dashboard
    participant TG as Threat Generator
    participant API as FastAPI
    participant Validator as Pydantic Validator
    participant Coordinator as Coordinator Agent

    Note over TG: Background task runs every 30s
    TG->>TG: Generate random threat scenario
    TG->>API: POST /api/threats/trigger
    
    alt Manual Trigger
        User->>Dashboard: Click "Trigger Critical Threat"
        Dashboard->>API: POST /api/threats/trigger
    end
    
    API->>Validator: Validate ThreatSignal
    
    alt Validation Success
        Validator-->>API: Valid ThreatSignal
        API->>Coordinator: analyze_threat(signal)
        Note over Coordinator: Proceed to Phase 2
    else Validation Failure
        Validator-->>API: ValidationError
        API-->>Dashboard: 422 Unprocessable Entity
        Dashboard-->>User: Show error message
    end
```

**Key Points:**
- Threats can be auto-generated (every 30s) or manually triggered
- All inputs are validated using Pydantic models
- Invalid threats are rejected before analysis begins

---

## Flow 2: Parallel Agent Execution

This flow shows how 5 specialized agents analyze the threat concurrently.

```mermaid
sequenceDiagram
    autonumber
    participant Coordinator as Coordinator Agent
    participant HA as Historical Agent
    participant CA as Config Agent
    participant DA as DevOps Agent
    participant CTA as Context Agent
    participant PA as Priority Agent
    participant Store as Mock Data Store
    participant OpenAI as OpenAI API

    Coordinator->>Coordinator: Build agent contexts
    
    Note over Coordinator,PA: All agents execute in parallel via asyncio.gather()
    
    par Historical Analysis
        Coordinator->>HA: analyze(signal, context)
        HA->>Store: get_similar_incidents()
        Store-->>HA: Past incidents (30 days)
        HA->>OpenAI: LLM analysis (or mock)
        OpenAI-->>HA: Analysis response
        HA-->>Coordinator: AgentAnalysis (confidence, findings)
    and Config Analysis
        Coordinator->>CA: analyze(signal, context)
        CA->>Store: get_customer_config()
        Store-->>CA: Rate limits, policies
        CA->>OpenAI: LLM analysis (or mock)
        OpenAI-->>CA: Analysis response
        CA-->>Coordinator: AgentAnalysis
    and DevOps Analysis
        Coordinator->>DA: analyze(signal, context)
        DA->>Store: get_recent_infra_events()
        Store-->>DA: Deployments, changes
        DA->>OpenAI: LLM analysis (or mock)
        OpenAI-->>DA: Analysis response
        DA-->>Coordinator: AgentAnalysis
    and Context Analysis
        Coordinator->>CTA: analyze(signal, context)
        CTA->>Store: get_relevant_news()
        Store-->>CTA: News, threat intel
        CTA->>OpenAI: LLM analysis (or mock)
        OpenAI-->>CTA: Analysis response
        CTA-->>Coordinator: AgentAnalysis
    and Priority Analysis
        Coordinator->>PA: analyze(signal, context)
        PA->>OpenAI: LLM analysis (or mock)
        OpenAI-->>PA: Analysis response
        PA-->>Coordinator: AgentAnalysis (severity, MITRE)
    end
    
    Note over Coordinator: All 5 agent results collected
    Note over Coordinator: Duration: ~200-500ms (mock) or ~8-10s (live)
```

**Key Points:**
- All 5 agents run in parallel using `asyncio.gather()`
- Each agent has access to specialized data sources
- Mock mode bypasses OpenAI API for fast testing
- Each agent returns structured `AgentAnalysis` with confidence scores

---

## Flow 3: Enhanced Analysis (FP, Response, Timeline)

This flow shows the new production-grade analyzers that run after agent execution.

```mermaid
sequenceDiagram
    autonumber
    participant Coordinator as Coordinator Agent
    participant FP as False Positive Analyzer
    participant RE as Response Engine
    participant TB as Timeline Builder
    participant Store as Mock Data Store

    Note over Coordinator: Phase 2 complete - all agent results ready
    
    rect rgb(200, 220, 255)
        Note over Coordinator,FP: Step 1: False Positive Analysis
        Coordinator->>FP: analyze(signal, agent_analyses, historical)
        FP->>FP: Analyze user agent patterns
        FP->>FP: Check IP reputation
        FP->>FP: Analyze request volume
        FP->>Store: Get historical FP rate
        Store-->>FP: Similar incidents resolution
        FP->>FP: Calculate FP score (0-1)
        FP-->>Coordinator: FalsePositiveScore
        Note over FP: Score: 0.0-1.0<br/>Confidence: 0.0-1.0<br/>Recommendation: likely_fp | needs_review | likely_real
    end
    
    rect rgb(200, 255, 220)
        Note over Coordinator,RE: Step 2: Response Planning
        Coordinator->>Coordinator: Extract severity from agents
        Coordinator->>RE: generate_response_plan(signal, severity, fp_score)
        RE->>RE: Select response template
        
        alt High FP Score (>0.7)
            RE->>RE: Downgrade to MONITOR action
        else Low FP Score (<0.3)
            RE->>RE: Escalate response urgency
        end
        
        RE->>RE: Build primary action
        RE->>RE: Build secondary actions
        RE->>RE: Calculate SLA times
        RE->>RE: Generate escalation path
        RE-->>Coordinator: ResponsePlan
        Note over RE: Primary action<br/>Secondary actions<br/>SLA: 15-240 min<br/>Escalation path
    end
    
    rect rgb(255, 220, 200)
        Note over Coordinator,TB: Step 3: Timeline Construction
        Coordinator->>TB: build_timeline(signal, agents, fp_score, response)
        TB->>TB: Add DETECTION event
        TB->>TB: Add ENRICHMENT events (4)
        TB->>TB: Add ANALYSIS events (6)
        TB->>TB: Add CORRELATION events
        TB->>TB: Add DECISION event
        TB->>TB: Add ACTION events
        TB->>TB: Calculate phase breakdown
        TB-->>Coordinator: InvestigationTimeline
        Note over TB: 15-20 chronological events<br/>Phase durations<br/>Audit trail
    end
    
    Note over Coordinator: All enhanced analyses complete
    Note over Coordinator: Duration: ~80-180ms total
```

**Key Points:**
- These analyzers run **sequentially** after parallel agent execution
- **FP Analyzer**: Reduces false positives using pattern matching and historical data
- **Response Engine**: Maps threat+severity to actionable remediation steps
- **Timeline Builder**: Creates forensic audit trail for compliance
- Total overhead: <200ms for all three analyzers

---

## Flow 4: Result Synthesis & Delivery

This flow shows how all analysis results are aggregated and delivered.

```mermaid
sequenceDiagram
    autonumber
    participant Coordinator as Coordinator Agent
    participant API as FastAPI
    participant Store as Threat Store
    participant WS as WebSocket Manager

    Note over Coordinator: All analyses complete:<br/>• 5 agent analyses<br/>• FP score<br/>• Response plan<br/>• Timeline

    Coordinator->>Coordinator: _synthesize_analysis()

    rect rgb(240, 240, 255)
        Note over Coordinator: Synthesis Steps
        Coordinator->>Coordinator: Extract severity from Priority Agent
        Coordinator->>Coordinator: Collect all key findings
        Coordinator->>Coordinator: Generate executive summary
        Coordinator->>Coordinator: Generate customer narrative
        Coordinator->>Coordinator: Determine review requirement

        alt High Severity OR High FP Score OR Low Confidence
            Coordinator->>Coordinator: Set requires_human_review = true
            Coordinator->>Coordinator: Set review_reason
        end

        Coordinator->>Coordinator: Calculate total processing time
        Coordinator->>Coordinator: Build EnhancedThreatAnalysis
    end

    Coordinator-->>API: Return EnhancedThreatAnalysis

    API->>Store: Store threat (in-memory)
    Store-->>API: Stored successfully

    API->>WS: broadcast_threat(analysis)
    Note over WS: Send to all connected clients

    API-->>API: Return HTTP 200 OK

    Note over Coordinator,WS: Complete analysis available:<br/>• Threat signal<br/>• 5 agent analyses<br/>• FP score + indicators<br/>• Response plan + actions<br/>• Investigation timeline<br/>• MITRE mapping<br/>• Review status
```

**Key Points:**
- Coordinator synthesizes all results into a single `EnhancedThreatAnalysis` object
- Executive summary and customer narrative are generated
- Review requirement is determined based on severity, FP score, and confidence
- Results are stored and broadcast in real-time
- Total processing time is tracked for performance monitoring

---

## Flow 5: WebSocket Real-time Updates

This flow shows how the dashboard receives real-time threat updates.

```mermaid
sequenceDiagram
    autonumber
    participant User as SOC Analyst
    participant Dashboard as React Dashboard
    participant WS_Client as WebSocket Client
    participant WS_Server as WebSocket Server
    participant Store as Threat Store

    User->>Dashboard: Open dashboard
    Dashboard->>WS_Client: Initialize WebSocket
    WS_Client->>WS_Server: Connect to ws://localhost:8000/ws

    WS_Server-->>WS_Client: Connection accepted

    rect rgb(220, 255, 220)
        Note over WS_Server,WS_Client: Initial Data Load
        WS_Server->>Store: Get recent threats (last 50)
        Store-->>WS_Server: List of threats
        WS_Server->>WS_Client: Send "initial_batch" message
        WS_Client->>Dashboard: Update state with threats
        Dashboard-->>User: Display threat list
    end

    loop Every 25 seconds
        WS_Client->>WS_Server: Send "ping"
        WS_Server-->>WS_Client: Send "pong"
        Note over WS_Client,WS_Server: Keepalive heartbeat
    end

    rect rgb(255, 220, 220)
        Note over WS_Server: New threat analyzed
        WS_Server->>WS_Server: broadcast_threat() called
        WS_Server->>WS_Client: Send "new_threat" message
        WS_Client->>Dashboard: Add threat to state
        Dashboard->>Dashboard: Update metric cards
        Dashboard->>Dashboard: Add to threat list (top)
        Dashboard-->>User: Show new threat with animation

        alt Threat requires human review
            Dashboard->>Dashboard: Increment "Requires Review" count
            Dashboard-->>User: Highlight in UI
        end
    end

    alt Connection Lost
        WS_Client->>WS_Client: Detect disconnection
        Note over WS_Client: Wait 3 seconds
        WS_Client->>WS_Server: Attempt reconnect
        WS_Server-->>WS_Client: Reconnected
        WS_Server->>WS_Client: Send "initial_batch" (resync)
    end

    User->>Dashboard: Close browser tab
    Dashboard->>WS_Client: Cleanup
    WS_Client->>WS_Server: Disconnect
    WS_Server->>WS_Server: Remove client from connections
```

**Key Points:**
- WebSocket connection established on dashboard load
- Initial batch of recent threats sent immediately
- Heartbeat ping/pong every 25 seconds to keep connection alive
- New threats broadcast to all connected clients in real-time
- Automatic reconnection with 3-second delay on connection loss
- Dashboard updates UI reactively without page refresh

---

## Complete End-to-End Flow Summary

Here's how all 5 flows connect together:

```mermaid
flowchart TB
    Start([Threat Detected]) --> Flow1[Flow 1: Detection & Ingestion<br/>~10ms]
    Flow1 --> Flow2[Flow 2: Parallel Agent Execution<br/>~200-500ms mock / ~8-10s live]
    Flow2 --> Flow3[Flow 3: Enhanced Analysis<br/>~80-180ms]
    Flow3 --> Flow4[Flow 4: Result Synthesis<br/>~20-50ms]
    Flow4 --> Flow5[Flow 5: WebSocket Delivery<br/>~5-10ms]
    Flow5 --> End([Dashboard Updated])

    style Flow1 fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style Flow2 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style Flow3 fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
    style Flow4 fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Flow5 fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    style Start fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    style End fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
```

### Performance Breakdown

| Flow | Phase | Mock Mode | Live Mode |
|------|-------|-----------|-----------|
| **Flow 1** | Detection & Ingestion | ~10ms | ~10ms |
| **Flow 2** | Parallel Agent Execution | ~200-500ms | ~8-10s |
| **Flow 3** | Enhanced Analysis | ~80-180ms | ~80-180ms |
| **Flow 4** | Result Synthesis | ~20-50ms | ~20-50ms |
| **Flow 5** | WebSocket Delivery | ~5-10ms | ~5-10ms |
| **TOTAL** | **End-to-End** | **~500-1000ms** | **~10-12s** |

### Key Differences: Mock vs Live Mode

**Mock Mode** (No OpenAI API):
- ✅ Fast testing (~500ms per threat)
- ✅ No API costs
- ✅ Deterministic responses
- ❌ Simulated AI analysis

**Live Mode** (With OpenAI API):
- ✅ Real AI-powered analysis
- ✅ Context-aware insights
- ✅ Production-quality results
- ❌ Slower (~10s per threat)
- ❌ API costs (~$0.01 per threat)

---

## Agent Execution Details

### Data Flow Through Agents

```mermaid
flowchart LR
    Signal[ThreatSignal] --> Context{Build Contexts}

    Context --> |Historical Context| HA[Historical Agent]
    Context --> |Config Context| CA[Config Agent]
    Context --> |DevOps Context| DA[DevOps Agent]
    Context --> |External Context| CTA[Context Agent]
    Context --> |Signal Only| PA[Priority Agent]

    HA --> |AgentAnalysis| Agg[Aggregator]
    CA --> |AgentAnalysis| Agg
    DA --> |AgentAnalysis| Agg
    CTA --> |AgentAnalysis| Agg
    PA --> |AgentAnalysis| Agg

    Agg --> FP[FP Analyzer]
    FP --> RE[Response Engine]
    RE --> TB[Timeline Builder]
    TB --> Final[EnhancedThreatAnalysis]

    style Signal fill:#e3f2fd,stroke:#1976d2
    style Context fill:#fff3e0,stroke:#f57c00
    style HA fill:#f3e5f5,stroke:#7b1fa2
    style CA fill:#f3e5f5,stroke:#7b1fa2
    style DA fill:#f3e5f5,stroke:#7b1fa2
    style CTA fill:#f3e5f5,stroke:#7b1fa2
    style PA fill:#f3e5f5,stroke:#7b1fa2
    style Agg fill:#e8f5e9,stroke:#388e3c
    style FP fill:#fce4ec,stroke:#c2185b
    style RE fill:#fce4ec,stroke:#c2185b
    style TB fill:#fce4ec,stroke:#c2185b
    style Final fill:#c8e6c9,stroke:#2e7d32
```

---

## Error Handling Flows

### Validation Error Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Validator

    Client->>API: POST /api/threats/trigger (invalid data)
    API->>Validator: Validate ThreatSignal
    Validator-->>API: ValidationError
    API-->>Client: 422 Unprocessable Entity
    Note over Client: Display error:<br/>"Invalid threat signal"
```

### OpenAI API Error Flow

```mermaid
sequenceDiagram
    participant Agent
    participant OpenAI

    Agent->>OpenAI: Request analysis
    OpenAI-->>Agent: API Error (rate limit, timeout, etc.)
    Agent->>Agent: Catch exception
    Agent->>Agent: Fall back to mock analysis
    Agent-->>Coordinator: AgentAnalysis (with lower confidence)
    Note over Agent: System continues gracefully
```

### WebSocket Reconnection Flow

```mermaid
sequenceDiagram
    participant Dashboard
    participant WS_Client
    participant WS_Server

    Note over WS_Client,WS_Server: Connection active
    WS_Server-->>WS_Client: Connection lost
    WS_Client->>WS_Client: Detect disconnection
    WS_Client->>WS_Client: Wait 3 seconds
    WS_Client->>WS_Server: Reconnect attempt

    alt Reconnection Success
        WS_Server-->>WS_Client: Connected
        WS_Server->>WS_Client: Send initial_batch (resync)
        WS_Client->>Dashboard: Update state
    else Reconnection Failed
        WS_Client->>WS_Client: Wait 3 seconds
        WS_Client->>WS_Server: Retry reconnect
    end
```

---

## Conclusion

These sequence flows demonstrate:

1. **Modular Architecture** - Each phase is independent and testable
2. **Parallel Processing** - Agents run concurrently for speed
3. **Real-time Updates** - WebSocket ensures instant dashboard updates
4. **Error Resilience** - Graceful fallbacks at every layer
5. **Production-Ready** - Comprehensive analysis with FP detection, response planning, and audit trails

For more details, see:
- [Complete Architecture Documentation](./SOC_System_Architecture.md)
- [Architecture Diagrams](./soc-architecture.md)
- [Enhancement Guide](./SOC_Enhancement_Guide.md)

---

*Last Updated: 2026-02-05*

