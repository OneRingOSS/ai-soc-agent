# SOC Agent System – Architecture v2: Core Architecture
## Enterprise-Ready, Cloud-Agnostic Platform Design

**Version:** 2.0
**Last Updated:** February 16, 2026
**Status:** Enterprise Architecture Blueprint

---

## Table of Contents

1. [Core Architecture v2](#1-core-architecture-v2)
   - 1.1 [Logical Layering](#11-logical-layering)
   - 1.2 [Polyglot Analysis Runtime](#12-polyglot-analysis-runtime)
   - 1.3 [LLM/SLM Strategy](#13-llmslm-strategy)
2. [Enterprise-Grade Capabilities](#2-enterprise-grade-capabilities)
   - 2.1 [Identity, RBAC & Multi-tenancy](#21-identity-rbac--multi-tenancy)
   - 2.2 [Persistence, Audit & Compliance](#22-persistence-audit--compliance)
   - 2.3 [Alerts & On-Call (PagerDuty, etc.)](#23-alerts--on-call-pagerduty-etc)
3. [Cloud Deployment on AWS & GCP](#3-cloud-deployment-on-aws--gcp)
   - 3.1 [Core Platform Services](#31-core-platform-services)
   - 3.2 [Observability Stack Options](#32-observability-stack-options)
   - 3.3 [Networking, Security & Data](#33-networking-security--data)

---

## 1. Core Architecture v2

### 1.1 Logical Layering

v2 keeps the overall layering from the current architecture but makes each layer explicitly cloud- and language-agnostic.

```text
┌─────────────────────────────────────────────────────────────┐
│          ANALYST & INTEGRATION LAYER (EXTERNAL)            │
│  • React/Tailwind SOC UI (multi-tenant)                    │
│  • REST/GraphQL API for integrations (SIEM, SOAR, EDR)     │
│  • Webhooks & streaming connectors                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           API & CONTROL PLANE (Go / Python)                │
│  • Public API Gateway (FastAPI or Go HTTP/gRPC)            │
│  • AuthN/AuthZ (OIDC, RBAC, tenancy routing)               │
│  • Configuration & policy service                          │
│  • Runbook orchestration & async jobs                      │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         ORCHESTRATION & ANALYSIS FABRIC (Polyglot)         │
│  • Coordinator (Python or Go)                              │
│  • Agents (Python, with hot paths in Go/Rust)              │
│  • FP Analyzer (Python/ML)                                 │
│  • Response Engine (rules + ML/risk)                       │
│  • Timeline Builder (Python)                               │
│  • Async task queue (Redis Streams / NATS / Kafka)         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         STATE, DATA & KNOWLEDGE LAYER                       │
│  • PostgreSQL (primary store, RLS for multi-tenancy)       │
│  • Redis (caching, WebSocket fan-out, queues)              │
│  • Object storage (S3/GCS) for artifacts & raw logs        │
│  • Feature store & model registry (MLflow or vendor)       │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         PLATFORM, OBSERVABILITY & SECURITY                  │
│  • Kubernetes (EKS/GKE/AKS or self-managed)                 │
│  • Ingress / API gateway                                    │
│  • OTel + Prometheus + Loki + Tempo/Jaeger + Grafana       │
│  • SSO, RBAC, secrets, KMS, security scanners              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Polyglot Analysis Runtime

The v1 system uses Python (FastAPI + async agents) for everything. v2 introduces a polyglot pattern while preserving the existing design.

#### Runtime Split

**Python (primary):**
- Coordinator, agents, FP Analyzer, Response Engine, Timeline Builder.
- ML/analytics-heavy paths (FP scoring, anomaly detection, model inference).
- Rapid prototyping for new analyzers and agent types.

**Go:**
- High-throughput ingestion gateway (optional replacement for FastAPI at scale).
- gRPC-based coordinator if Python's concurrency model becomes a bottleneck (>500 RPS sustained).
- Long-lived worker pools for heavy I/O or CPU-bound operations (bulk log parsing, enrichment fanout).
- Health/readiness probes, metrics exporters, and other infrastructure services.

**Rust (selective):**
- Hot-path analyzers (e.g., parsing massive JSON logs, regex-heavy detection rules).
- Sandboxed execution of customer-defined rules/policies (WASM compilation target).
- Cryptographic operations (signature verification, hash computation).

#### Interaction Pattern

```text
┌──────────────────────┐     gRPC/protobuf     ┌─────────────────────┐
│  Python Coordinator  │ ◄──────────────────── │  Go Ingestion GW    │
│                      │                        │  (high-QPS entry)   │
│  Calls agents via:   │                        └─────────────────────┘
│  • Python (in-proc)  │
│  • gRPC (Go/Rust)    │     gRPC/protobuf     ┌─────────────────────┐
│                      │ ◄──────────────────── │  Rust Parser Worker │
│                      │                        │  (hot-path analysis)│
└──────────────────────┘                        └─────────────────────┘
```

- Go/Rust workers run as sidecar or standalone services behind a gRPC boundary.
- Coordinator calls workers via gRPC with strict schemas (protobuf).
- OpenTelemetry is instrumented consistently across Python/Go/Rust so the trace tree is fully connected.
- Service mesh (Istio/Linkerd) provides mTLS, retries, and circuit breaking between polyglot services.

#### Decision Rule for Language Choice

| Criteria | Python | Go | Rust |
|----------|--------|----|------|
| **When to use** | Fast iteration, ML, low–medium QPS | High-QPS endpoints, concurrency, IO-heavy | Safety-critical, latency-sensitive parsing |
| **Typical QPS** | <200 sustained | 200–10,000+ | N/A (used for hot paths, not full services) |
| **Dev velocity** | Fastest | Moderate | Slowest |
| **Memory footprint** | Highest | Low | Lowest |
| **ML ecosystem** | Best (PyTorch, scikit-learn, HF) | Limited | Very limited |
| **Concurrency model** | asyncio (cooperative) | Goroutines (preemptive) | async-std/tokio (zero-cost) |

#### Migration Path from v1 to Polyglot

This is an incremental process, not a rewrite:

1. **Phase 1 (current):** All Python. FastAPI + asyncio.gather for agents.
2. **Phase 2:** Extract ingestion gateway to Go. Python coordinator calls it via gRPC. Agents remain Python.
3. **Phase 3:** Move the highest-volume agents (e.g., Historical Agent doing DB lookups) to Go workers.
4. **Phase 4:** Add Rust parsers for specific analysis tasks (PCAP parsing, log normalization, YARA rule execution).

### 1.3 LLM/SLM Strategy

v2 treats AI models as **replaceable infrastructure** rather than hardcoded code paths.

#### Use Cases

| Use Case | Model Type | Latency Target | Frequency |
|----------|-----------|----------------|-----------|
| Per-threat executive summary generation | Local SLM (7B/8B) | <500ms | Every threat |
| FP decision explanation (analyst-facing) | Local SLM | <300ms | Every threat |
| Suggested response playbook text | Local SLM or Remote LLM | <2s | On demand |
| Batch retrospective analysis | Remote LLM (GPT-4, Claude) | <30s | Nightly/weekly |
| "What-if" simulation for runbooks | Remote LLM | <10s | On demand |
| Complex incident correlation | Remote LLM | <15s | On demand |

#### Local SLM (Small Language Model) — Primary

- Deploy a quantized 7B/8B model (e.g., Llama 3.1 8B, Mistral 7B, Phi-3) on-cluster.
- Serve via vLLM or Ollama behind a gRPC/REST interface.
- Used for latency-sensitive per-threat explanations (runs alongside analysis pipeline).
- Hardware: single GPU node (A10G on AWS, L4 on GCP) or CPU-only with quantization (GGUF/GPTQ).
- Cost: predictable, no per-token charges.

#### Remote LLM — Secondary

- Pluggable vendor adapter (OpenAI, Anthropic, Vertex AI, Azure OpenAI).
- Used for:
  - Offline batch scoring (nightly FP model evaluation).
  - Complex playbook generation requiring reasoning.
  - "What-if" simulation for runbooks.
- Circuit breaker pattern: if remote LLM is unavailable, fall back to template-based generation.

#### Architecture Pattern

```text
┌──────────────────────────────────────────────────────────────┐
│                    MODEL SERVICE (Microservice)               │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ Router      │───▶│ Local SLM   │    │ Remote LLM  │     │
│  │             │    │ (vLLM/Ollama│    │ (OpenAI/    │     │
│  │ Decides:    │    │  on-cluster)│    │  Claude/    │     │
│  │ local vs    │    └─────────────┘    │  Vertex)    │     │
│  │ remote      │───────────────────────▶└─────────────┘     │
│  │ based on:   │                                             │
│  │ • latency   │    ┌─────────────┐                          │
│  │ • complexity│───▶│ Template    │  (fallback if both       │
│  │ • cost      │    │ Engine      │   models unavailable)    │
│  └─────────────┘    └─────────────┘                          │
│                                                              │
│  Interfaces:                                                 │
│  • gRPC: GenerateSummary(threat_context) → text              │
│  • gRPC: ExplainFPDecision(fp_score, indicators) → text     │
│  • gRPC: SuggestPlaybook(threat_type, severity) → playbook  │
│                                                              │
│  Observability:                                              │
│  • OTel spans for every inference call                       │
│  • Prometheus: model_inference_duration_seconds              │
│  • Prometheus: model_token_count_total                       │
│  • Prometheus: model_fallback_total (counts fallbacks)       │
└──────────────────────────────────────────────────────────────┘
```

#### Inference Isolation

All inference runs in a **separate service** so that:
- Failures or latency spikes in LLMs never block core detection or response.
- Model upgrades are independent of application releases.
- GPU resources are isolated and autoscaled separately from CPU workloads.

#### MLOps Lifecycle

```text
┌──────────┐    ┌───────────┐    ┌──────────────┐    ┌──────────┐
│ Training │───▶│ Registry  │───▶│ Shadow Mode  │───▶│ Promote  │
│ (offline)│    │ (MLflow)  │    │ (runs beside │    │ (replace │
│          │    │           │    │  production  │    │  active   │
│          │    │           │    │  model)      │    │  model)   │
└──────────┘    └───────────┘    └──────────────┘    └──────────┘
                                        │
                                   Compare metrics:
                                   • Accuracy vs baseline
                                   • Latency vs SLA
                                   • Cost per inference
                                   Auto-rollback if worse
```

---

## 2. Enterprise-Grade Capabilities

### 2.1 Identity, RBAC & Multi-tenancy

#### Identity

- OIDC-based SSO (Okta, Azure AD, Google Workspace).
- Short-lived JWTs or opaque tokens issued by IdP, validated by API gateway.
- Service-to-service auth via mTLS and workload identity (e.g., IAM roles on AWS/GCP).
- Session management: server-side sessions backed by Redis with configurable TTL.

#### RBAC Model

| Role | View Incidents | Modify Incidents | Execute Actions | Configure Rules | Manage Users | Export Data |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| `ANALYST_T1` | ✅ | Comment only | ❌ | ❌ | ❌ | ❌ |
| `ANALYST_T2` | ✅ | ✅ | Approve & execute | View only | ❌ | ✅ |
| `SOC_MANAGER` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `CUSTOMER_ADMIN` | Own tenant | Own tenant | Own tenant | Own tenant | Own tenant | Own tenant |
| `PLATFORM_ADMIN` | ✅ (all tenants) | ✅ | ✅ | ✅ | ✅ | ✅ |
| `READONLY` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

#### Implementation

- Central **AuthZ service** exposing `check(subject, action, resource) → bool`.
- Options: Oso, Cerbos, OpenFGA, or homegrown in Go/Python.
- RBAC rules stored in Postgres `roles` / `permissions` tables, cached in Redis.
- Every API endpoint decorated with permission check middleware.

#### Multi-tenancy

- **Data isolation:** Single Postgres cluster with row-level security (RLS) per tenant.
- Every table has `tenant_id` column; RLS policies enforce `tenant_id = current_setting('app.tenant_id')`.
- API layer sets `app.tenant_id` on every DB session based on authenticated user's JWT `org_id` claim.
- **Compute isolation:** K8s namespace-per-tenant for large enterprise customers (optional).
- **Redis isolation:** Key prefix per tenant (`tenant:{id}:threats:*`).

### 2.2 Persistence, Audit & Compliance

#### PostgreSQL as Primary System of Record

v1 uses in-memory + Redis. v2 adds PostgreSQL as the durable, queryable, compliance-ready store.

**Schema overview:**

```text
┌─────────────────────────────────┐
│           PLATFORM TABLES       │
├─────────────────────────────────┤
│ tenants                         │
│ users                           │
│ roles                           │
│ permissions                     │
│ user_roles (junction)           │
│ api_keys                        │
│ sessions                        │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│        THREAT DATA TABLES       │
├─────────────────────────────────┤
│ threats (PK: id, FK: tenant_id) │
│ agent_results                   │
│ fp_scores                       │
│ response_plans                  │
│ timeline_events                 │
│ response_actions_taken          │
│ analyst_comments                │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│        CONFIGURATION TABLES     │
├─────────────────────────────────┤
│ customer_configs                │
│ detection_rules                 │
│ response_templates              │
│ notification_channels           │
│ escalation_policies             │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│        COMPLIANCE TABLES        │
├─────────────────────────────────┤
│ audit_log                       │
│ data_retention_policies         │
│ pii_registry                    │
│ deletion_requests               │
│ compliance_reports              │
└─────────────────────────────────┘
```

**All tables include:** `tenant_id`, `created_at`, `updated_at`, `created_by`.

#### Audit Log Coverage

Every security-sensitive action is logged to `audit_log`:

| Action Category | Examples | Retention |
|----------------|---------|-----------|
| Authentication | Login, logout, failed login, MFA challenge | 1 year |
| Authorization | Role change, permission grant/revoke | 1 year |
| Incident lifecycle | Create, triage, assign, resolve, suppress, reopen | 2 years |
| Configuration | Rule change, threshold change, integration change | 1 year |
| Data access | Export, bulk query, API key creation | 1 year |
| System | Deployment, config reload, model promotion | 6 months |

#### GDPR / Privacy Compliance

- **Data classification:** Every field tagged as PII, quasi-PII, or non-PII in schema metadata.
- **Right to erasure workflow:**
  1. Deletion request received via API or UI.
  2. System identifies all records with matching `subject_id`.
  3. PII columns anonymized (hashed or nulled); aggregated metrics preserved.
  4. Audit log entry: "Erasure completed for subject X at timestamp Y."
- **Data retention policies:**
  - Configurable per tenant (30 / 90 / 365 days).
  - Background job runs nightly to purge expired records.
  - Object storage lifecycle policies for raw log archives.
- **Consent tracking:** Optional module for tracking data processing consent per customer/subject.

#### Encryption & Key Management

| Layer | Mechanism | Provider |
|-------|-----------|----------|
| At rest (DB) | Transparent Data Encryption (TDE) | RDS/Cloud SQL native |
| At rest (files) | Server-side encryption | S3 SSE-KMS / GCS CMEK |
| In transit | TLS 1.3 everywhere | Load balancer + service mesh |
| Inter-service | mTLS via service mesh | Istio/Linkerd |
| Application-level | Envelope encryption for sensitive fields | AWS KMS / GCP KMS |
| Secrets | Managed secret store | AWS Secrets Manager / GCP Secret Manager |

#### Backups & Disaster Recovery

- **Database:** Point-In-Time Recovery (PITR) enabled; daily automated snapshots retained 30 days.
- **Configuration:** All rules, templates, and policies exported to object storage (S3/GCS) nightly.
- **Cross-region:** Optional read replica in secondary region for DR.
- **RTO/RPO targets:**
  - Tier 1 (Critical): RPO 1 hour, RTO 4 hours.
  - Tier 2 (Standard): RPO 24 hours, RTO 8 hours.
- **Tested restore runbook:** Quarterly DR drill documented in runbook.

### 2.3 Alerts & On-Call (PagerDuty, etc.)

#### Alert Routing Architecture

```text
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ Response Engine   │────▶│ Alert Router      │────▶│ PagerDuty        │
│ (ResponsePlan)   │     │                   │     │ Opsgenie         │
│                  │     │ Routes based on:  │     │ VictorOps        │
│ Observability    │────▶│ • severity        │     └──────────────────┘
│ (Grafana alerts) │     │ • tenant config   │
│                  │     │ • time of day     │     ┌──────────────────┐
│ System health    │────▶│ • on-call schedule│────▶│ Slack / Teams    │
│ (K8s events)     │     │                   │     │ (channel per     │
│                  │     │ Deduplication:    │     │  incident)       │
│                  │     │ • fingerprinting  │     └──────────────────┘
│                  │     │ • cooldown window │
│                  │     │ • grouping rules  │     ┌──────────────────┐
│                  │     │                   │────▶│ Email            │
│                  │     └───────────────────┘     │ (digest mode)    │
│                  │                               └──────────────────┘
└──────────────────┘
```

#### Routing Rules

| Severity | Channel | SLA | Auto-escalation |
|----------|---------|-----|-----------------|
| Critical | PagerDuty (immediate page) + Slack war room | 15 min | Escalate to SOC Manager after 10 min |
| High | PagerDuty (high urgency) + Slack notification | 30 min | Escalate after 20 min |
| Medium | Slack notification + email | 2 hours | Escalate after 1.5 hours |
| Low | Dashboard only + email digest | 24 hours | No auto-escalation |
| Info | Dashboard only | N/A | N/A |

#### Integration Pattern

- Webhook-based integration with incident management platforms.
- Events emitted: `incident.created`, `incident.acknowledged`, `incident.escalated`, `incident.resolved`, `sla.breached`.
- Bidirectional sync: when analyst acknowledges in PagerDuty, SOC dashboard updates status.

---

## 3. Cloud Deployment on AWS & GCP

v2 is **cloud-agnostic** at the architecture level. Provider-specific services are confined to the platform layer and swappable via configuration.

### 3.1 Core Platform Services

| Concern | AWS | GCP | Cloud-Agnostic Alternative | Notes |
|---------|-----|-----|---------------------------|-------|
| **Container orchestration** | EKS | GKE | Kind (local), k3s (edge) | Same Helm charts across all. |
| **Ingress / API gateway** | ALB + AWS API Gateway | Cloud Load Balancing + API Gateway | Nginx Ingress Controller | K8s-native ingress for internal; cloud gateway for public APIs. |
| **Identity** | Cognito + IAM | Cloud Identity + IAM + IAP | Keycloak (self-hosted) | Support 3rd-party IdPs (Okta, Azure AD). |
| **Database** | RDS PostgreSQL / Aurora | Cloud SQL / AlloyDB | Self-managed Postgres on K8s | Use RLS, encrypted at rest, automated backups. |
| **Cache & Pub/Sub** | ElastiCache Redis | Memorystore Redis | Self-managed Redis on K8s | Same Redis store/pub-sub design as v1. |
| **Object storage** | S3 | GCS | MinIO (self-hosted) | Raw logs, model artifacts, exports, backups. |
| **Queues / streaming** | SQS / MSK (Kafka) / Kinesis | Cloud Pub/Sub / Kafka (Confluent) | NATS / Redis Streams | For async pipelines and high-volume ingest. |
| **Secrets management** | Secrets Manager / SSM | Secret Manager | HashiCorp Vault | No secrets in ConfigMaps; references only. |
| **DNS & CDN** | Route 53 + CloudFront | Cloud DNS + Cloud CDN | Cloudflare | Static frontend assets via CDN. |
| **KMS** | AWS KMS | Cloud KMS | HashiCorp Vault Transit | Envelope encryption for sensitive fields. |
| **GPU (for SLM)** | EC2 G5 (A10G) / Inf2 | GCE L4 / TPU | On-prem GPU nodes | vLLM or Ollama serving. |

### 3.2 Observability Stack Options

#### Option A: Open Source Stack (Current v1 Approach)

Best for: cost control, data sovereignty, no vendor lock-in.

| Pillar | Tool | Deployment |
|--------|------|------------|
| **Metrics** | Prometheus + Thanos (long-term storage) | Helm chart on K8s |
| **Logs** | Loki + Promtail | Helm chart on K8s |
| **Traces** | Tempo or Jaeger | Helm chart on K8s |
| **Dashboards** | Grafana | Helm chart on K8s |
| **Instrumentation** | OpenTelemetry SDK + Collector | Sidecar or DaemonSet |
| **Alerting** | Grafana Alerting → PagerDuty/Slack | Built into Grafana |

#### Option B: Managed Commercial (Recommended for Enterprise)

Best for: reduced operational burden, advanced features (APM, RUM, synthetics).

| Vendor | Strengths | Integration Pattern |
|--------|-----------|-------------------|
| **Datadog** | Unified platform (metrics, logs, traces, APM, security). Best-in-class dashboarding. | OTel SDK in code → OTel Collector → Datadog exporter. Replace Prometheus/Loki/Jaeger entirely. |
| **Grafana Cloud** | Managed version of the open-source stack. Familiar if already using OSS. | Same OTel SDK → Grafana Agent → Grafana Cloud endpoints. |
| **New Relic** | Strong APM, good K8s integration. Generous free tier. | OTel SDK → New Relic OTLP endpoint. |
| **Honeycomb** | Best for high-cardinality trace analysis and debugging. | OTel SDK → Honeycomb OTLP endpoint. |
| **Dynatrace** | AI-powered root cause analysis. Enterprise-focused. | OneAgent on K8s nodes + OTel SDK. |

#### Option C: Cloud-Native (Tight Cloud Integration)

| Pillar | AWS | GCP |
|--------|-----|-----|
| **Metrics** | CloudWatch Metrics | Cloud Monitoring |
| **Logs** | CloudWatch Logs | Cloud Logging |
| **Traces** | X-Ray | Cloud Trace |
| **Dashboards** | CloudWatch Dashboards | Grafana on GCP (managed) |

#### Design Principle

Keep **OpenTelemetry in the application code** as the universal abstraction. The OTel Collector's exporter configuration is the only thing that changes between options A, B, and C. Application code never references a specific vendor.

```text
┌─────────────────────┐
│  Application Code   │
│  (OTel SDK)         │  ← Never changes
└──────────┬──────────┘
           │ OTLP
           ▼
┌─────────────────────┐
│  OTel Collector     │  ← Exporter config changes per environment
│                     │
│  Exporters:         │
│  ├─ prometheus      │  → Option A (OSS)
│  ├─ jaeger          │  → Option A (OSS)
│  ├─ loki            │  → Option A (OSS)
│  ├─ datadog         │  → Option B (Datadog)
│  ├─ otlphttp        │  → Option B (New Relic/Honeycomb)
│  ├─ awsxray         │  → Option C (AWS)
│  └─ googlecloud     │  → Option C (GCP)
└─────────────────────┘
```

### 3.3 Networking, Security & Data

#### Network Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                     PUBLIC INTERNET                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │   WAF / DDoS Shield   │
              │   (AWS WAF / Cloud    │
              │    Armor)             │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   CDN + TLS Term      │
              │   (CloudFront /       │
              │    Cloud CDN)         │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   API Gateway         │
              │   (rate limiting,     │
              │    auth, routing)     │
              └───────────┬───────────┘
                          │
           ┌──────────────▼──────────────┐
           │      PRIVATE VPC / VNet     │
           │                             │
           │  ┌────────────────────┐    │
           │  │ K8s Cluster (EKS/  │    │
           │  │ GKE) — private     │    │
           │  │ nodes, no public   │    │
           │  │ IPs                │    │
           │  └────────┬───────────┘    │
           │           │                 │
           │  ┌────────▼───────────┐    │
           │  │ Private DB subnet  │    │
           │  │ (RDS / Cloud SQL)  │    │
           │  │ + Redis subnet     │    │
           │  └────────────────────┘    │
           │                             │
           └─────────────────────────────┘
```

#### Security Controls

| Control | Implementation | Notes |
|---------|---------------|-------|
| **WAF** | AWS WAF / Cloud Armor | Rate limiting, geo-blocking, OWASP top-10 rules |
| **DDoS** | AWS Shield / Cloud Armor | Always-on L3/L4/L7 protection |
| **Network policies** | K8s NetworkPolicy + Calico/Cilium | Pod-to-pod microsegmentation |
| **mTLS** | Istio / Linkerd service mesh | All inter-service communication encrypted |
| **Secrets** | External Secrets Operator → AWS SM / GCP SM | Syncs cloud secrets into K8s Secrets |
| **Image signing** | Cosign + Sigstore | Verify image integrity before admission |
| **Admission control** | OPA Gatekeeper / Kyverno | Enforce policies on K8s resources |
| **Runtime security** | Falco / Datadog CWS | Detect anomalous container behavior |

---

*This document covers Sections 1–3 of the SOC Agent System Architecture v2.*
*See also:*
- *`SOC_System_Architecture_v2_Runbooks.md` — Section 4 (Runbooks)*
- *`SOC_System_Architecture_v2_Operations.md` — Sections 5–6 (CI/CD, Security Scanning)*
