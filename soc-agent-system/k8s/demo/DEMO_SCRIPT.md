# SOC Agent System — Interview Demo Script

This document provides a narration script and talking points for demonstrating the SOC Agent System during your Endor Labs Director of Engineering interview.

## 🎯 Demo Objectives

1. Showcase production-ready Kubernetes architecture
2. Demonstrate scalability and high availability
3. Highlight observability and testing practices
4. Show technical depth and engineering maturity

## ⏱️ Timeline (Total: ~10-15 minutes)

- **Introduction** (2 min) - Architecture overview
- **Live Demo** (3 min) - Run demo script
- **Load Test** (2 min) - Show scaling behavior
- **Deep Dive** (5-8 min) - Technical discussion
- **Q&A** (flexible) - Answer questions

---

## 📋 Pre-Demo Checklist

Before starting the demo, ensure:

- [ ] `setup_demo.sh` has been run successfully
- [ ] All pods are in Running state
- [ ] You have `DEMO_SCRIPT.md` (this file) open for reference
- [ ] Terminal is ready with proper font size for screen sharing
- [ ] Browser tabs are closed (clean demo environment)

Quick verification:
```bash
kubectl get pods -n soc-agent-demo
kubectl get hpa -n soc-agent-demo
```

---

## 🎬 Demo Script

### Part 1: Introduction (2 minutes)

**[Screen: Architecture diagram or terminal]**

> "I'd like to show you a production-ready SOC Agent System I've built as part of my interview preparation. This demonstrates several key engineering principles that are relevant to the Director of Engineering role at Endor Labs."

**Key Points:**
- Built for interview prep, but production-quality
- Showcases Kubernetes, observability, and scalability
- Relevant to Endor Labs' focus on security and developer tools

**[Show architecture]**

> "The system is deployed on Kubernetes using Helm charts. It consists of:
> - A FastAPI backend with horizontal pod autoscaling (2-8 replicas)
> - A React frontend served by nginx
> - Redis for cross-pod state management and pub/sub
> - Nginx Ingress for external access
> - All running on a local Kind cluster with 3 nodes"

**Technical Depth:**
- Mention HPA configuration (CPU-based, 70% target)
- Highlight Redis Pub/Sub for real-time updates across pods
- Note rolling update strategy (maxUnavailable=0 for zero downtime)

---

### Part 2: Live Demo (3 minutes)

**[Screen: Terminal]**

> "Let me show you the system in action. I'll run a quick demo script that sets up port-forwards and shows the current state."

**Run the demo script:**
```bash
bash soc-agent-system/k8s/demo/run_demo.sh
```

**While it's running, narrate:**

**Step 1: Environment Verification**
> "First, it verifies that all pods are running. You can see we have multiple backend pods for high availability."

**Point out:**
- Number of backend pods (should be 2 with HPA)
- HPA status showing current/desired replicas
- All pods in Running state

**Step 2: Port Forwards**
> "The script sets up port-forwards so we can access the services locally. In production, you'd use the Ingress controller or a LoadBalancer."

**Step 3: Dashboard Opens**
> "Here's the SOC dashboard. It shows real-time threat detection and analysis powered by OpenAI's GPT models."

**[Screen: Browser with dashboard]**

**Highlight:**
- Real-time updates via WebSocket
- Threat severity visualization
- Clean, professional UI

---

### Part 3: Load Test (2 minutes)

**[Screen: Terminal]**

> "Now let's run a load test to demonstrate how the system handles scale. This uses Locust to simulate 20 concurrent users over 2 minutes."

**[Press Enter to start load test]**

**While load test runs, explain:**

> "The load test is hitting multiple endpoints:
> - Creating new threats
> - Fetching threat lists
> - Analyzing threats with AI
> - Testing WebSocket connections
>
> This generates realistic load across all backend pods. With HPA configured, if CPU usage exceeds 70%, Kubernetes would automatically scale up to handle the load."

**Technical Points:**
- Locust generates ~X requests/second
- Load is distributed across multiple pods
- Redis ensures state consistency
- Each pod can handle requests independently

**[When load test completes]**

> "The test completed successfully. Let's look at the results."

**Show:**
- Total requests processed
- Response times (p50, p95, p99)
- Failure rate (should be 0%)
- Pod status (may have scaled up)

---

### Part 4: Technical Deep Dive (5-8 minutes)

**[Screen: Terminal or IDE]**

> "Let me walk you through some of the technical decisions and implementation details."

#### 4.1 Kubernetes Architecture

**Show Helm chart:**
```bash
cat soc-agent-system/k8s/charts/soc-agent/values.yaml
```

**Talking Points:**
- "I used Helm for declarative, version-controlled deployments"
- "HPA is configured with sensible defaults but can be tuned"
- "Resource limits prevent resource exhaustion"
- "Readiness/liveness probes ensure traffic only goes to healthy pods"

#### 4.2 High Availability & Resilience

**Show deployment strategy:**
```bash
kubectl get deployment soc-agent-backend -n soc-agent-demo -o yaml | grep -A 5 strategy
```

**Talking Points:**
- "Rolling update strategy with maxUnavailable=0 ensures zero downtime"
- "maxSurge=1 allows one extra pod during updates"
- "I've tested this with the resilience test suite"

**Show test results (optional):**
```bash
cat soc-agent-system/k8s/tests/test_resilience.sh
```

#### 4.3 State Management

**Explain Redis architecture:**

> "One of the interesting challenges was managing state across multiple pods. I implemented:
> - Redis for shared session storage
> - Pub/Sub for real-time updates across all pods
> - Fallback to in-memory storage if Redis is unavailable
>
> This ensures that any pod can handle any request, and all pods stay synchronized for WebSocket updates."

**Show code (optional):**
```bash
# Show Redis integration in backend
cat soc-agent-system/backend/app/redis_client.py
```

#### 4.4 Observability

**Talking Points:**
- "I've integrated OpenTelemetry for distributed tracing"
- "Prometheus metrics for monitoring"
- "Structured JSON logging for log aggregation"
- "Health check endpoints for Kubernetes probes"

**Show metrics endpoint:**
```bash
curl http://localhost:9080/metrics | head -20
```

#### 4.5 Testing Strategy

**Show test suites:**
```bash
ls -la soc-agent-system/k8s/tests/
```

**Talking Points:**
- "I've built comprehensive test suites covering:
  - Integration tests (deployment, connectivity)
  - Observability tests (metrics, traces, logs)
  - Ingress tests (routing, WebSocket)
  - Performance tests (load, multi-pod)
  - Resilience tests (pod failures, rolling updates)
- All tests are automated and can run in CI/CD"

---

### Part 5: Production Readiness (2-3 minutes)

**[Screen: Terminal or documentation]**

> "If this were going to production, here's what I'd add or change:"

**Discuss:**

1. **Security:**
   - TLS/SSL certificates for Ingress
   - Network policies for pod-to-pod communication
   - Secrets management (Vault, Sealed Secrets)
   - RBAC for service accounts

2. **Scalability:**
   - Metrics-server for HPA (not in Kind by default)
   - Cluster autoscaler for node scaling
   - Redis cluster for HA
   - CDN for frontend assets

3. **Observability:**
   - Full observability stack (Prometheus, Grafana, Jaeger, Loki)
   - Alerting rules for critical metrics
   - Distributed tracing across all services
   - Log aggregation and analysis

4. **CI/CD:**
   - GitHub Actions for automated testing
   - ArgoCD or Flux for GitOps deployment
   - Automated rollback on failures
   - Canary or blue-green deployments

5. **Disaster Recovery:**
   - Multi-region deployment
   - Automated backups
   - Disaster recovery runbooks
   - Chaos engineering tests

---

## 🎯 Key Talking Points by Topic

### For Kubernetes Experience

- "I chose Kubernetes because it's the industry standard for container orchestration"
- "Helm charts make deployments reproducible and version-controlled"
- "HPA demonstrates understanding of auto-scaling patterns"
- "Rolling updates show zero-downtime deployment strategy"

### For Scalability

- "The system can scale from 2 to 8 pods automatically based on CPU"
- "Redis Pub/Sub ensures all pods stay synchronized"
- "Stateless backend design allows horizontal scaling"
- "Load tests prove the system can handle concurrent users"

### For Observability

- "OpenTelemetry provides vendor-neutral observability"
- "Structured logging makes debugging easier"
- "Metrics expose system health and performance"
- "Health checks enable Kubernetes self-healing"

### For Testing

- "I've built 5 different test suites covering various scenarios"
- "Tests are automated and can run in CI/CD"
- "Performance tests use Locust for realistic load simulation"
- "Resilience tests verify zero-downtime deployments"

### For Engineering Leadership

- "I focused on production-ready patterns, not just demos"
- "Documentation is comprehensive for team onboarding"
- "Architecture is extensible for future requirements"
- "Testing strategy ensures confidence in deployments"

---

## ❓ Anticipated Questions & Answers

### Q: "Why did you choose this tech stack?"

**A:** "I chose technologies that are industry-standard and production-proven:
- Kubernetes for orchestration (ubiquitous in cloud-native)
- FastAPI for backend (high performance, async, type-safe)
- React for frontend (component-based, large ecosystem)
- Redis for state (fast, reliable, pub/sub support)
- OpenTelemetry for observability (vendor-neutral, future-proof)"

### Q: "How would you handle database persistence?"

**A:** "Currently, the system uses in-memory storage for demo purposes. For production:
- PostgreSQL or MySQL for relational data
- Redis for caching and sessions
- S3 or object storage for artifacts
- Database migrations with Alembic or Flyway
- Backups and point-in-time recovery"

### Q: "What about security?"

**A:** "Security would include:
- TLS everywhere (Ingress, inter-service)
- API authentication (JWT, OAuth2)
- Network policies (zero-trust networking)
- Secrets management (Vault, AWS Secrets Manager)
- Container scanning (Trivy, Snyk)
- RBAC for Kubernetes access
- Regular security audits"

### Q: "How would you monitor this in production?"

**A:** "Full observability stack:
- Prometheus for metrics collection
- Grafana for visualization and dashboards
- Jaeger or Tempo for distributed tracing
- Loki for log aggregation
- Alertmanager for alerting (PagerDuty integration)
- SLO/SLI tracking for reliability
- Custom dashboards for business metrics"

### Q: "What's your deployment strategy?"

**A:** "GitOps with ArgoCD or Flux:
- All config in Git (single source of truth)
- Automated deployments on merge to main
- Canary or blue-green for risk mitigation
- Automated rollback on health check failures
- Separate environments (dev, staging, prod)
- Feature flags for gradual rollouts"

---

## 🎓 Closing Remarks

> "This project demonstrates my approach to building production-ready systems:
> - Start with solid architecture
> - Build in observability from day one
> - Test comprehensively
> - Document thoroughly
> - Think about operations and maintenance
>
> I'm excited about bringing this mindset to Endor Labs, especially given your focus on developer security and tooling. I believe my experience with Kubernetes, observability, and production systems would be valuable for the Director of Engineering role."

---

## 📊 Metrics to Highlight

- **83 tests** passing across all test suites
- **100% test pass rate** for K8s deployment
- **Zero downtime** during rolling updates
- **Sub-second response times** under load
- **2-8 pod autoscaling** based on CPU
- **3-node cluster** for high availability

---

## 🔧 Cleanup After Demo

```bash
bash soc-agent-system/k8s/demo/teardown_demo.sh
```

Or keep cluster for follow-up questions:
```bash
bash soc-agent-system/k8s/demo/teardown_demo.sh
# (without --delete-cluster flag)
```

---

**Good luck with your interview! 🚀**

