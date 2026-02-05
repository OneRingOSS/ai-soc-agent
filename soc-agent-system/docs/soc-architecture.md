# SOC Agent System - Architecture Diagrams

A comprehensive visual documentation of the SOC Agent System architecture using Mermaid diagrams.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Request Flow Sequence](#2-request-flow-sequence)
3. [Agent System Architecture](#3-agent-system-architecture)
4. [Data Models](#4-data-models)
5. [WebSocket Communication](#5-websocket-communication)
6. [API Endpoints](#6-api-endpoints)
7. [Technology Stack](#7-technology-stack)
8. [Deployment Architecture](#8-deployment-architecture)

---

## 1. System Overview

High-level component architecture showing the main system components and their interactions.

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React + Vite)"]
        UI[Dashboard UI]
        WS_Client[WebSocket Client]
        Charts[Chart.js Visualizations]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[REST API]
        WS_Server[WebSocket Server]
        TG[Threat Generator]

        subgraph Coordinator["Coordinator Agent"]
            CA[CoordinatorAgent]
        end

        subgraph Agents["Specialized Agents (5)"]
            HA[Historical Agent]
            CFA[Config Agent]
            DA[DevOps Agent]
            CTA[Context Agent]
            PA[Priority Agent]
        end

        subgraph Analyzers["Enhanced Analyzers (3)"]
            FPA[False Positive Analyzer]
            REA[Response Engine]
            TBA[Timeline Builder]
        end

        subgraph Data["Data Layer"]
            MS[Mock Data Store]
            TS[Threat Store]
        end
    end

    subgraph External["External Services"]
        OpenAI[OpenAI API]
    end

    UI --> API
    UI --> WS_Client
    WS_Client <--> WS_Server
    Charts --> UI

    API --> CA
    TG --> CA
    CA --> HA & CFA & DA & CTA & PA

    HA & CFA & DA & CTA & PA --> OpenAI
    HA & CFA & DA & CTA --> MS

    CA --> FPA & REA & TBA
    FPA & REA & TBA --> MS

    CA --> TS
    WS_Server --> TS

    style Frontend fill:#3b82f6,color:#fff
    style Backend fill:#10b981,color:#fff
    style External fill:#f59e0b,color:#fff
    style Coordinator fill:#8b5cf6,color:#fff
    style Agents fill:#ec4899,color:#fff
    style Analyzers fill:#f59e0b,color:#fff
```

---

## 2. Request Flow Sequence

Sequence diagram showing the complete flow of a threat analysis request with enhanced analyzers.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant Dashboard as React Dashboard
    participant API as FastAPI
    participant Coordinator as Coordinator Agent
    participant Agents as Specialized Agents (5)
    participant Analyzers as Enhanced Analyzers (3)
    participant OpenAI as OpenAI API
    participant Store as Data Stores
    participant WS as WebSocket

    User->>Dashboard: Trigger Threat / Auto-generated
    Dashboard->>API: POST /api/threats/trigger
    API->>Coordinator: analyze_threat(signal)

    Note over Coordinator,Agents: Phase 1: Parallel Agent Execution
    par Parallel Agent Execution
        Coordinator->>Agents: Historical Agent
        Agents->>Store: get_similar_incidents()
        Agents->>OpenAI: LLM Analysis
        OpenAI-->>Agents: Response
    and
        Coordinator->>Agents: Config Agent
        Agents->>Store: get_customer_config()
        Agents->>OpenAI: LLM Analysis
        OpenAI-->>Agents: Response
    and
        Coordinator->>Agents: DevOps Agent
        Agents->>Store: get_recent_infra_events()
        Agents->>OpenAI: LLM Analysis
        OpenAI-->>Agents: Response
    and
        Coordinator->>Agents: Context Agent
        Agents->>Store: get_relevant_news()
        Agents->>OpenAI: LLM Analysis
        OpenAI-->>Agents: Response
    and
        Coordinator->>Agents: Priority Agent
        Agents->>OpenAI: LLM Analysis
        OpenAI-->>Agents: Response
    end

    Agents-->>Coordinator: AgentAnalysis results (5)

    Note over Coordinator,Analyzers: Phase 2: Enhanced Analysis
    Coordinator->>Analyzers: FP Analyzer
    Analyzers->>Store: Get historical FP rates
    Analyzers-->>Coordinator: FalsePositiveScore

    Coordinator->>Analyzers: Response Engine
    Analyzers-->>Coordinator: ResponsePlan

    Coordinator->>Analyzers: Timeline Builder
    Analyzers-->>Coordinator: InvestigationTimeline

    Note over Coordinator: Phase 3: Synthesis
    Coordinator->>Coordinator: synthesize_analysis()
    Coordinator-->>API: EnhancedThreatAnalysis
    API->>Store: Store threat
    API->>WS: broadcast_threat()
    WS-->>Dashboard: new_threat message
    Dashboard-->>User: Update UI with FP score, response plan, timeline
```

---

## 3. Agent System Architecture

Class diagram showing the agent inheritance, analyzers, and relationships.

```mermaid
classDiagram
    class BaseAgent {
        <<abstract>>
        +name: str
        +client: AsyncOpenAI
        +get_system_prompt()* str
        +build_user_prompt(signal, context)* str
        +analyze(signal, context) AgentAnalysis
        +analyze_mock(signal, context) AgentAnalysis
    }

    class HistoricalAgent {
        +name: "Historical Agent"
        +get_system_prompt() str
        +build_user_prompt(signal, context) str
    }

    class ConfigAgent {
        +name: "Config Agent"
        +get_system_prompt() str
        +build_user_prompt(signal, context) str
    }

    class DevOpsAgent {
        +name: "DevOps Agent"
        +get_system_prompt() str
        +build_user_prompt(signal, context) str
    }

    class ContextAgent {
        +name: "Context Agent"
        +get_system_prompt() str
        +build_user_prompt(signal, context) str
    }

    class PriorityAgent {
        +name: "Priority Agent"
        +get_system_prompt() str
        +build_user_prompt(signal, context) str
    }

    class FalsePositiveAnalyzer {
        +analyze(signal, analyses, incidents) FalsePositiveScore
        -_analyze_user_agent(signal) float
        -_analyze_ip(signal) float
        -_analyze_request_volume(signal) float
        -_analyze_historical_patterns(signal, incidents) float
        -_calculate_score(indicators) FalsePositiveScore
    }

    class ResponseActionEngine {
        +generate_response_plan(signal, severity, fp_score, config) ResponsePlan
        -_select_template(threat_type, severity) dict
        -_build_primary_action(template, signal) ResponseAction
        -_build_secondary_actions(template, signal) List
        -_calculate_sla(severity) int
        -_build_escalation_path(severity, config) List
    }

    class TimelineBuilder {
        +build_timeline(signal, analyses, fp_score, response) InvestigationTimeline
        -_add_detection_event(signal) TimelineEvent
        -_add_enrichment_events(signal) List
        -_add_agent_analysis_events(analyses) List
        -_add_fp_analysis_event(fp_score) TimelineEvent
        -_add_decision_event(severity) TimelineEvent
        -_add_response_events(response) List
    }

    class CoordinatorAgent {
        +mock_data: MockDataStore
        +client: AsyncOpenAI
        +use_mock: bool
        +historical_agent: HistoricalAgent
        +config_agent: ConfigAgent
        +devops_agent: DevOpsAgent
        +context_agent: ContextAgent
        +priority_agent: PriorityAgent
        +fp_analyzer: FalsePositiveAnalyzer
        +response_engine: ResponseActionEngine
        +timeline_builder: TimelineBuilder
        +analyze_threat(signal) EnhancedThreatAnalysis
        -_build_agent_contexts(signal) Dict
        -_synthesize_analysis(signal, analyses, time, severity, fp_score, response, timeline) EnhancedThreatAnalysis
        -_generate_executive_summary(signal, severity, findings) str
    }

    BaseAgent <|-- HistoricalAgent
    BaseAgent <|-- ConfigAgent
    BaseAgent <|-- DevOpsAgent
    BaseAgent <|-- ContextAgent
    BaseAgent <|-- PriorityAgent

    CoordinatorAgent o-- HistoricalAgent
    CoordinatorAgent o-- ConfigAgent
    CoordinatorAgent o-- DevOpsAgent
    CoordinatorAgent o-- ContextAgent
    CoordinatorAgent o-- PriorityAgent
    CoordinatorAgent o-- FalsePositiveAnalyzer
    CoordinatorAgent o-- ResponseActionEngine
    CoordinatorAgent o-- TimelineBuilder
```

---

## 4. Data Models

Entity relationship diagram showing the enhanced data model structure.

```mermaid
erDiagram
    ThreatSignal ||--o{ EnhancedThreatAnalysis : "analyzed_into"
    EnhancedThreatAnalysis ||--|{ AgentAnalysis : "contains"
    EnhancedThreatAnalysis ||--|| FalsePositiveScore : "has"
    EnhancedThreatAnalysis ||--|| ResponsePlan : "has"
    EnhancedThreatAnalysis ||--|| InvestigationTimeline : "has"
    EnhancedThreatAnalysis ||--o{ MITRETactic : "maps_to"
    EnhancedThreatAnalysis ||--o{ MITRETechnique : "maps_to"
    FalsePositiveScore ||--|{ FPIndicator : "contains"
    ResponsePlan ||--|| ResponseAction : "has_primary"
    ResponsePlan ||--o{ ResponseAction : "has_secondary"
    InvestigationTimeline ||--|{ TimelineEvent : "contains"

    ThreatSignal {
        string id PK
        ThreatType threat_type
        string customer_name
        string source_ip
        string user_agent
        int request_count
        datetime detected_at
        dict raw_data
    }

    EnhancedThreatAnalysis {
        string id PK
        ThreatSignal signal FK
        ThreatSeverity severity
        ThreatStatus status
        string executive_summary
        string customer_narrative
        bool requires_human_review
        string review_reason
        int total_processing_time_ms
        datetime created_at
    }

    AgentAnalysis {
        string agent_name
        string analysis
        float confidence
        list key_findings
        list recommendations
        int processing_time_ms
    }

    FalsePositiveScore {
        float score
        float confidence
        string recommendation
        string explanation
        float historical_fp_rate
        int similar_resolved_as_fp
        int similar_resolved_as_real
    }

    FPIndicator {
        string indicator
        float weight
        string description
        string source
    }

    ResponsePlan {
        int sla_minutes
        float overall_confidence
        list escalation_path
    }

    ResponseAction {
        ResponseActionType action_type
        ResponseUrgency urgency
        string target
        string reason
        dict parameters
        bool auto_executable
        bool requires_approval
        string estimated_impact
        float confidence
    }

    InvestigationTimeline {
        datetime start_time
        datetime end_time
        int duration_ms
        dict phase_breakdown
    }

    TimelineEvent {
        TimelineEventType event_type
        datetime timestamp
        string phase
        string title
        string description
        dict details
        ThreatSeverity severity
        string agent_name
    }

    MITRETactic {
        string id PK
        string name
        string description
    }

    MITRETechnique {
        string id PK
        string name
        string description
    }

    HistoricalIncident {
        string id PK
        string customer_name
        ThreatType threat_type
        datetime timestamp
        string resolution
        bool was_false_positive
    }

    CustomerConfig {
        string customer_name PK
        int rate_limit_per_minute
        list geo_restrictions
        string bot_detection_sensitivity
    }

    InfraEvent {
        string id PK
        string event_type
        datetime timestamp
        string description
        list affected_services
    }

    NewsItem {
        string id PK
        string title
        string summary
        datetime published_at
        string source
    }
```

---

## 5. WebSocket Communication

State diagram showing WebSocket connection lifecycle and message flow.

```mermaid
stateDiagram-v2
    [*] --> Connecting: Client initiates connection
    Connecting --> Connected: Connection accepted
    Connecting --> Disconnected: Connection failed
    
    Connected --> ReceivingInitialBatch: Send initial_batch
    ReceivingInitialBatch --> Listening: Batch received
    
    Listening --> ProcessingThreat: new_threat received
    ProcessingThreat --> Listening: Update UI
    
    Listening --> SendingPing: Ping interval (25s)
    SendingPing --> Listening: Receive pong
    
    Listening --> Disconnected: Connection lost
    Disconnected --> Reconnecting: After 3s delay
    Reconnecting --> Connecting: Attempt reconnect
    
    Connected --> [*]: Manual disconnect
```

### WebSocket Message Types

```mermaid
flowchart LR
    subgraph Server_to_Client["Server → Client"]
        initial_batch["initial_batch<br/>List of recent threats"]
        new_threat["new_threat<br/>Real-time threat data"]
        pong["pong<br/>Heartbeat response"]
        ping_s["ping<br/>Keepalive check"]
    end
    
    subgraph Client_to_Server["Client → Server"]
        ping_c["ping<br/>Heartbeat request"]
    end
    
    style Server_to_Client fill:#10b981,color:#fff
    style Client_to_Server fill:#3b82f6,color:#fff
```

---

## 6. API Endpoints

Flowchart showing all available API endpoints and their relationships.

```mermaid
flowchart TB
    subgraph REST["REST API Endpoints"]
        GET_ROOT["GET /<br/>Health Check"]
        GET_THREATS["GET /api/threats<br/>List Threats (paginated)"]
        GET_THREAT_ID["GET /api/threats/{id}<br/>Get Threat by ID"]
        GET_ANALYTICS["GET /api/analytics<br/>Dashboard Metrics"]
        POST_TRIGGER["POST /api/threats/trigger<br/>Manual Trigger"]
    end
    
    subgraph WebSocket["WebSocket Endpoint"]
        WS_ENDPOINT["WS /ws<br/>Real-time Stream"]
    end
    
    subgraph Responses["Response Models"]
        HealthResponse["HealthResponse<br/>status, timestamp, counts"]
        ThreatList["List[ThreatAnalysis]"]
        ThreatDetail["ThreatAnalysis"]
        Metrics["DashboardMetrics"]
    end
    
    GET_ROOT --> HealthResponse
    GET_THREATS --> ThreatList
    GET_THREAT_ID --> ThreatDetail
    GET_ANALYTICS --> Metrics
    POST_TRIGGER --> ThreatDetail
    
    WS_ENDPOINT -.-> |initial_batch| ThreatList
    WS_ENDPOINT -.-> |new_threat| ThreatDetail
    
    style REST fill:#3b82f6,color:#fff
    style WebSocket fill:#8b5cf6,color:#fff
    style Responses fill:#10b981,color:#fff
```

---

## 7. Technology Stack

Comprehensive view of the technology stack.

```mermaid
flowchart TB
    subgraph Frontend_Stack["Frontend Stack"]
        React["React 18"]
        Vite["Vite 5"]
        ChartJS["Chart.js 4"]
        DateFns["date-fns 3"]
    end
    
    subgraph Backend_Stack["Backend Stack"]
        FastAPI["FastAPI 0.109"]
        Uvicorn["Uvicorn"]
        Pydantic["Pydantic 2.5"]
        OpenAI_SDK["OpenAI SDK 1.10"]
    end
    
    subgraph Testing_Stack["Testing Stack"]
        Pytest["pytest"]
        Pytest_Asyncio["pytest-asyncio"]
        Vitest["Vitest"]
        RTL["React Testing Library"]
    end
    
    subgraph Infrastructure["Infrastructure"]
        Python["Python 3.11+"]
        Node["Node.js 18+"]
        WebSockets["WebSockets"]
    end
    
    subgraph External_APIs["External APIs"]
        OpenAI_API["OpenAI GPT-4 API"]
    end
    
    Frontend_Stack --> Infrastructure
    Backend_Stack --> Infrastructure
    Backend_Stack --> External_APIs
    Testing_Stack --> Frontend_Stack
    Testing_Stack --> Backend_Stack
    
    style Frontend_Stack fill:#3b82f6,color:#fff
    style Backend_Stack fill:#10b981,color:#fff
    style Testing_Stack fill:#f59e0b,color:#fff
    style Infrastructure fill:#64748b,color:#fff
    style External_APIs fill:#ec4899,color:#fff
```

---

## 8. Deployment Architecture

Production deployment architecture diagram.

```mermaid
flowchart TB
    subgraph Users["Users"]
        Browser["Web Browser"]
    end
    
    subgraph CDN["CDN / Static Hosting"]
        Static["Static Assets<br/>(React Build)"]
    end
    
    subgraph LoadBalancer["Load Balancer"]
        LB["Nginx / ALB"]
    end
    
    subgraph AppServers["Application Servers"]
        API1["FastAPI Instance 1"]
        API2["FastAPI Instance 2"]
        API3["FastAPI Instance N"]
    end
    
    subgraph SharedState["Shared State (Production)"]
        Redis["Redis<br/>(Pub/Sub + Cache)"]
        DB["PostgreSQL<br/>(Persistent Storage)"]
    end
    
    subgraph ExternalServices["External Services"]
        OpenAI["OpenAI API"]
        Monitoring["Monitoring<br/>(Prometheus/Grafana)"]
        Logging["Logging<br/>(ELK Stack)"]
    end
    
    Browser --> CDN
    Browser --> LoadBalancer
    CDN --> Static
    LoadBalancer --> API1 & API2 & API3
    API1 & API2 & API3 --> Redis
    API1 & API2 & API3 --> DB
    API1 & API2 & API3 --> OpenAI
    API1 & API2 & API3 --> Monitoring
    API1 & API2 & API3 --> Logging
    
    style Users fill:#64748b,color:#fff
    style CDN fill:#f59e0b,color:#fff
    style LoadBalancer fill:#8b5cf6,color:#fff
    style AppServers fill:#10b981,color:#fff
    style SharedState fill:#3b82f6,color:#fff
    style ExternalServices fill:#ec4899,color:#fff
```

---

## Agent & Analyzer Responsibilities Summary

### Specialized Agents (5)

| Agent | Primary Function | Data Sources | Key Outputs |
|-------|------------------|--------------|-------------|
| **Historical** | Pattern recognition | Past incidents (30 days) | Similar incidents, false positive rates |
| **Config** | Policy compliance | Customer configurations | Rate limit violations, config issues |
| **DevOps** | Infrastructure correlation | Recent infra events | Deployment correlations, platform issues |
| **Context** | Business intelligence | News, market data | External factors, legitimate surge detection |
| **Priority** | Threat classification | All agent outputs | MITRE mapping, severity, customer narrative |

### Enhanced Analyzers (3)

| Analyzer | Primary Function | Inputs | Key Outputs |
|----------|------------------|--------|-------------|
| **False Positive Analyzer** | ML-based FP detection | Signal, agent analyses, historical incidents | FP score (0-1), confidence, indicators, recommendation |
| **Response Action Engine** | Automated remediation | Signal, severity, FP score, customer config | Primary/secondary actions, SLA times, escalation path |
| **Timeline Builder** | Forensic reconstruction | Signal, agent analyses, FP score, response plan | Chronological events, phase breakdown, audit trail |

---

## Key Architecture Patterns

1. **Multi-Agent Pattern**: Specialized agents with single responsibilities
2. **Parallel Execution**: `asyncio.gather()` for concurrent agent analysis
3. **Event-Driven Updates**: WebSocket for real-time threat streaming
4. **Mock Mode**: Testing without external API dependencies
5. **Factory Pattern**: `create_coordinator()` for flexible instantiation

---

## Performance Characteristics

| Metric | Target | Implementation |
|--------|--------|----------------|
| Agent Parallelism | 5 concurrent | `asyncio.gather()` |
| Analyzer Execution | Sequential | After agent completion |
| Total Analysis Time (Mock) | ~500-1000ms | No OpenAI API calls |
| Total Analysis Time (Live) | ~10-12s | With OpenAI API |
| WebSocket Keepalive | 25 seconds | Client-side ping interval |
| Reconnect Delay | 3 seconds | Exponential backoff recommended for production |
| Max Stored Threats | 50 | Configurable via environment |
| Threat Generation | 30 seconds | Background task interval |

### Analysis Phase Breakdown

| Phase | Components | Mock Mode | Live Mode |
|-------|-----------|-----------|-----------|
| **Phase 1** | 5 Agents (parallel) | ~200-500ms | ~8-10s |
| **Phase 2** | FP Analyzer | ~50-100ms | ~50-100ms |
| **Phase 3** | Response Engine | ~20-50ms | ~20-50ms |
| **Phase 4** | Timeline Builder | ~10-30ms | ~10-30ms |
| **Phase 5** | Synthesis & Delivery | ~20-50ms | ~20-50ms |
| **TOTAL** | **End-to-End** | **~500-1000ms** | **~10-12s** |

---

*Generated for SOC Agent System v2.0.0 - Enhanced with FP Detection, Response Planning, and Timeline Reconstruction*
