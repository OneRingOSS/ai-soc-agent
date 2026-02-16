# Block 4: Kind + Helm Kubernetes Deployment — Intent Spec

## Overview

**Goal:** Create a complete Kubernetes deployment solution for the SOC Agent System using Kind (local K8s) and Helm charts. This enables cloud-agnostic deployment that works identically on Kind, GKE, EKS, or AKS.

**Tool:** Augment Intent (generates interconnected infrastructure files)

**Estimated Time:** 3 hours

**Dependencies:**
- Block 1 (Observability instrumentation) — COMPLETED ✅
- Block 2 (Docker Compose stack) — COMPLETED ✅
- Block 3 (Load Testing) — COMPLETED ✅
- Redis Integration — COMPLETED ✅
- Dockerfiles exist: `backend/Dockerfile` and `frontend/Dockerfile` ✅
- Integration tests validate multi-pod deployment — COMPLETED ✅

**Fallback Strategy:** If this block fails, Docker Compose remains the primary demo. The Helm chart can be shown as code artifacts and discussed architecturally.

---

## Intent Specification

```
SPEC: Kubernetes Deployment for SOC Agent System using Kind + Helm

GOAL: Create a production-ready Helm chart and local Kind cluster configuration that deploys 
the SOC Agent System with full observability stack. The deployment should demonstrate 
cloud-agnostic best practices: health probes, HPA, resource limits, ConfigMaps, and 
multi-environment support via values files.

EXISTING CONTEXT:
- Backend: Python FastAPI application
  - Docker image: soc-backend:latest (built from backend/Dockerfile)
  - Exposes port 8000
  - Health endpoints: GET /health (liveness), GET /ready (readiness)
  - Metrics endpoint: GET /metrics (Prometheus format)
  - API endpoints: POST /api/threats/trigger, GET /api/threats, GET /api/threats/{id}
  - WebSocket: /ws (uses Redis Pub/Sub for cross-pod broadcasting)
  - Environment variables needed:
    - REDIS_URL (REQUIRED: redis://redis:6379 - for shared state across pods)
    - OTEL_EXPORTER_OTLP_ENDPOINT (default: http://otel-collector:4317)
    - OTEL_SERVICE_NAME (default: soc-agent-system)
    - LOG_LEVEL (default: INFO)
    - OPENAI_API_KEY (optional, for real LLM calls)
  - CRITICAL: Requires Redis for multi-pod deployment
    - All pods share state via Redis (threat storage)
    - WebSocket broadcasts use Redis Pub/Sub channel "threats:events"
    - Falls back to in-memory store if Redis unavailable (single pod only)
  - Validated by integration tests: backend/tests/test_redis_pubsub_integration.py
    - Tests simulate 3 pods with cross-pod WebSocket broadcasting
    - All 5 integration tests passing

- Frontend: React + Vite application served by nginx
  - Docker image: soc-frontend:latest (built from frontend/Dockerfile)
  - Exposes port 80
  - Serves static files from /usr/share/nginx/html
  - Needs reverse proxy to backend for /api/* and /ws
  - nginx.conf included in Docker image for reverse proxy configuration

- Observability Stack (from Block 2):
  - OpenTelemetry Collector (receives traces/metrics from backend)
  - Jaeger (trace visualization)
  - Prometheus (metrics storage)
  - Loki (log aggregation)
  - Grafana (unified dashboards)

- Target Environment:
  - Local: Kind cluster (1 control-plane + 2 worker nodes)
  - Images loaded via `kind load docker-image` (no registry)
  - Production: GKE/EKS/AKS with image registry

PROJECT STRUCTURE:
soc-agent-system/
├── backend/
│   ├── src/
│   │   ├── store.py (Redis + in-memory threat storage abstraction)
│   │   └── main.py (FastAPI app with Redis integration)
│   ├── tests/
│   │   └── test_redis_pubsub_integration.py (validates multi-pod deployment)
│   └── Dockerfile (exists - multi-stage Python build)
├── frontend/
│   ├── nginx.conf (exists - reverse proxy config)
│   └── Dockerfile (exists - multi-stage Node.js + nginx build)
├── observability/
│   ├── docker-compose.yml (exists from Block 2)
│   └── configs/ (OTel, Prometheus, Grafana configs exist)
└── k8s/ (NEW — to be generated)
    ├── kind-config.yaml
    ├── deploy.sh
    ├── teardown.sh
    └── charts/
        └── soc-agent/
            ├── Chart.yaml
            ├── values.yaml
            ├── values-production.yaml
            ├── README.md
            └── templates/
                ├── _helpers.tpl
                ├── backend-deployment.yaml
                ├── backend-service.yaml
                ├── backend-hpa.yaml
                ├── backend-configmap.yaml
                ├── redis-deployment.yaml (NEW - REQUIRED)
                ├── redis-service.yaml (NEW - REQUIRED)
                ├── frontend-deployment.yaml
                ├── frontend-service.yaml
                ├── ingress.yaml
                └── NOTES.txt

FILES TO GENERATE:

1. k8s/kind-config.yaml
   Purpose: Kind cluster configuration for local development
   Requirements:
   - API version: kind.x-k8s.io/v1alpha4
   - 3 nodes: 1 control-plane, 2 workers
   - Control plane node labels: "ingress-ready=true"
   - Port mappings on control plane:
     - containerPort 80 → hostPort 8080 (HTTP ingress)
     - containerPort 443 → hostPort 8443 (HTTPS ingress)
   - Enable kubeadm patches for ingress controller

2. k8s/charts/soc-agent/Chart.yaml
   Purpose: Helm chart metadata
   Requirements:
   - apiVersion: v2
   - name: soc-agent
   - version: 1.0.0
   - appVersion: "2.0.0"
   - description: "SOC Agent System - Multi-agent threat analysis platform with observability"
   - type: application
   - keywords: [security, soc, observability, ai-agents]

3. k8s/charts/soc-agent/values.yaml
   Purpose: Default values for local/dev deployment
   Requirements:
   - redis:
     - enabled: true
     - image:
       - repository: redis
       - tag: 7-alpine
       - pullPolicy: IfNotPresent
     - service:
       - type: ClusterIP
       - port: 6379
     - persistence:
       - enabled: false  # For local Kind, use true for production
     - resources:
       - requests: {cpu: 50m, memory: 128Mi}
       - limits: {cpu: 200m, memory: 256Mi}

   - backend:
     - replicaCount: 2
     - image:
       - repository: soc-backend
       - tag: latest
       - pullPolicy: Never  # For Kind (no registry)
     - service:
       - type: ClusterIP
       - port: 8000
     - resources:
       - requests: {cpu: 100m, memory: 256Mi}
       - limits: {cpu: 500m, memory: 512Mi}
     - hpa:
       - enabled: true
       - minReplicas: 2
       - maxReplicas: 8
       - targetCPUUtilizationPercentage: 70
     - env:
       - REDIS_URL: "redis://{{ include \"soc-agent.fullname\" . }}-redis:6379"
       - OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
       - OTEL_SERVICE_NAME: "soc-agent-system"
       - LOG_LEVEL: "INFO"
     - probes:
       - liveness: {path: /health, initialDelaySeconds: 10, periodSeconds: 30}
       - readiness: {path: /ready, initialDelaySeconds: 5, periodSeconds: 10}
   
   - frontend:
     - replicaCount: 1
     - image:
       - repository: soc-frontend
       - tag: latest
       - pullPolicy: Never
     - service:
       - type: ClusterIP
       - port: 80
     - resources:
       - requests: {cpu: 50m, memory: 64Mi}
       - limits: {cpu: 200m, memory: 128Mi}
   
   - ingress:
     - enabled: true
     - className: nginx
     - annotations: {}
     - hosts:
       - host: localhost
         paths:
           - path: /
             pathType: Prefix
             backend: frontend
           - path: /api
             pathType: Prefix
             backend: backend
           - path: /ws
             pathType: Prefix
             backend: backend
     - tls: []

4. k8s/charts/soc-agent/values-production.yaml
   Purpose: Production overrides showing cloud deployment configuration
   Requirements:
   - backend:
     - replicaCount: 4
     - image:
       - pullPolicy: Always  # Pull from registry
       - repository: gcr.io/my-project/soc-backend  # Example registry
     - resources:
       - requests: {cpu: 500m, memory: 1Gi}
       - limits: {cpu: 2, memory: 2Gi}
     - hpa:
       - maxReplicas: 20
       - targetCPUUtilizationPercentage: 60
     - env:
       - LOG_LEVEL: "WARNING"

   - ingress:
     - annotations:
       - cert-manager.io/cluster-issuer: "letsencrypt-prod"
     - tls:
       - enabled: true
       - secretName: soc-agent-tls
       - hosts: [soc.example.com]

5. k8s/charts/soc-agent/templates/_helpers.tpl
   Purpose: Reusable template helpers for consistent naming and labeling
   Requirements:
   - Define template: soc-agent.name (chart name)
   - Define template: soc-agent.fullname (release name + chart name)
   - Define template: soc-agent.chart (chart name + version)
   - Define template: soc-agent.labels (standard Helm labels)
   - Define template: soc-agent.selectorLabels (pod selector labels)
   - Define template: soc-agent.serviceAccountName (if needed)

6. k8s/charts/soc-agent/templates/backend-deployment.yaml
   Purpose: Backend FastAPI deployment
   Requirements:
   - apiVersion: apps/v1, kind: Deployment
   - metadata.name: {{ include "soc-agent.fullname" . }}-backend
   - metadata.labels: {{ include "soc-agent.labels" . }}
   - spec.replicas: {{ .Values.backend.replicaCount }}
   - spec.selector.matchLabels: app=soc-backend, release={{ .Release.Name }}
   - Pod template:
     - labels: app=soc-backend, release={{ .Release.Name }}
     - containers:
       - name: backend
       - image: {{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag }}
       - imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
       - ports: containerPort 8000
       - envFrom: configMapRef (backend-config)
       - resources: {{ .Values.backend.resources }}
       - livenessProbe:
         - httpGet: {path: /health, port: 8000}
         - initialDelaySeconds: {{ .Values.backend.probes.liveness.initialDelaySeconds }}
         - periodSeconds: {{ .Values.backend.probes.liveness.periodSeconds }}
       - readinessProbe:
         - httpGet: {path: /ready, port: 8000}
         - initialDelaySeconds: {{ .Values.backend.probes.readiness.initialDelaySeconds }}
         - periodSeconds: {{ .Values.backend.probes.readiness.periodSeconds }}
     - affinity:
       - podAntiAffinity (preferredDuringSchedulingIgnoredDuringExecution)
       - Prefer spreading pods across different nodes

7. k8s/charts/soc-agent/templates/backend-service.yaml
   Purpose: Backend ClusterIP service
   Requirements:
   - apiVersion: v1, kind: Service
   - metadata.name: {{ include "soc-agent.fullname" . }}-backend
   - spec.type: {{ .Values.backend.service.type }}
   - spec.ports: port 8000, targetPort 8000, protocol TCP, name http
   - spec.selector: app=soc-backend, release={{ .Release.Name }}

8. k8s/charts/soc-agent/templates/backend-hpa.yaml
   Purpose: HorizontalPodAutoscaler for backend
   Requirements:
   - Conditional: {{- if .Values.backend.hpa.enabled }}
   - apiVersion: autoscaling/v2, kind: HorizontalPodAutoscaler
   - metadata.name: {{ include "soc-agent.fullname" . }}-backend
   - spec.scaleTargetRef: Deployment/backend
   - spec.minReplicas: {{ .Values.backend.hpa.minReplicas }}
   - spec.maxReplicas: {{ .Values.backend.hpa.maxReplicas }}
   - spec.metrics:
     - type: Resource
     - resource.name: cpu
     - resource.target.type: Utilization
     - resource.target.averageUtilization: {{ .Values.backend.hpa.targetCPUUtilizationPercentage }}

9. k8s/charts/soc-agent/templates/backend-configmap.yaml
   Purpose: Environment variables for backend
   Requirements:
   - apiVersion: v1, kind: ConfigMap
   - metadata.name: {{ include "soc-agent.fullname" . }}-backend-config
   - data: all key-value pairs from .Values.backend.env

10. k8s/charts/soc-agent/templates/redis-deployment.yaml
    Purpose: Redis deployment for shared state across backend pods
    Requirements:
    - Conditional: {{- if .Values.redis.enabled }}
    - apiVersion: apps/v1, kind: Deployment
    - metadata.name: {{ include "soc-agent.fullname" . }}-redis
    - spec.replicas: 1  # Single Redis instance for local dev
    - spec.selector.matchLabels: app=redis, release={{ .Release.Name }}
    - Pod template:
      - containers:
        - name: redis
        - image: {{ .Values.redis.image.repository }}:{{ .Values.redis.image.tag }}
        - imagePullPolicy: {{ .Values.redis.image.pullPolicy }}
        - ports: containerPort 6379
        - resources: {{ .Values.redis.resources }}
        - livenessProbe: exec {command: ["redis-cli", "ping"]}
        - readinessProbe: exec {command: ["redis-cli", "ping"]}
    - CRITICAL: Backend pods depend on this for cross-pod WebSocket broadcasting

11. k8s/charts/soc-agent/templates/redis-service.yaml
    Purpose: Redis ClusterIP service
    Requirements:
    - Conditional: {{- if .Values.redis.enabled }}
    - apiVersion: v1, kind: Service
    - metadata.name: {{ include "soc-agent.fullname" . }}-redis
    - spec.type: {{ .Values.redis.service.type }}
    - spec.ports: port 6379, targetPort 6379, protocol TCP, name redis
    - spec.selector: app=redis, release={{ .Release.Name }}
    - CRITICAL: Backend REDIS_URL must reference this service name

12. k8s/charts/soc-agent/templates/frontend-deployment.yaml
    Purpose: Frontend nginx deployment
    Requirements:
    - apiVersion: apps/v1, kind: Deployment
    - metadata.name: {{ include "soc-agent.fullname" . }}-frontend
    - spec.replicas: {{ .Values.frontend.replicaCount }}
    - spec.selector.matchLabels: app=soc-frontend, release={{ .Release.Name }}
    - Pod template:
      - containers:
        - name: frontend
        - image: {{ .Values.frontend.image.repository }}:{{ .Values.frontend.image.tag }}
        - imagePullPolicy: {{ .Values.frontend.image.pullPolicy }}
        - ports: containerPort 80
        - resources: {{ .Values.frontend.resources }}
        - livenessProbe: httpGet {path: /, port: 80}

13. k8s/charts/soc-agent/templates/frontend-service.yaml
    Purpose: Frontend ClusterIP service
    Requirements:
    - apiVersion: v1, kind: Service
    - metadata.name: {{ include "soc-agent.fullname" . }}-frontend
    - spec.type: ClusterIP
    - spec.ports: port 80, targetPort 80, protocol TCP, name http
    - spec.selector: app=soc-frontend, release={{ .Release.Name }}

14. k8s/charts/soc-agent/templates/ingress.yaml
    Purpose: Nginx ingress for routing external traffic
    Requirements:
    - Conditional: {{- if .Values.ingress.enabled }}
    - apiVersion: networking.k8s.io/v1, kind: Ingress
    - metadata.name: {{ include "soc-agent.fullname" . }}
    - metadata.annotations: {{ .Values.ingress.annotations }}
    - spec.ingressClassName: {{ .Values.ingress.className }}
    - spec.rules:
      - host: {{ .Values.ingress.hosts[0].host }}
      - http.paths:
        - path: /api, pathType: Prefix, backend: service backend port 8000
        - path: /ws, pathType: Prefix, backend: service backend port 8000
        - path: /, pathType: Prefix, backend: service frontend port 80
    - spec.tls: (if .Values.ingress.tls is not empty)

15. k8s/charts/soc-agent/templates/NOTES.txt
    Purpose: Post-installation instructions
    Requirements:
    - Print deployment status
    - Show how to access the application:
      - "SOC Dashboard: http://localhost:8080" (for Kind)
      - "kubectl port-forward svc/{{ include "soc-agent.fullname" . }}-backend 8000:8000"
    - Show how to check pod status:
      - "kubectl get pods -l app=soc-backend"
      - "kubectl get pods -l app=redis"
      - "kubectl logs -l app=soc-backend --tail=50"
    - Show HPA status (if enabled):
      - "kubectl get hpa"
    - Show Redis connection status:
      - "kubectl exec -it <backend-pod> -- env | grep REDIS_URL"

16. k8s/deploy.sh
    Purpose: Automated deployment script for Kind cluster
    Requirements:
    - Shebang: #!/bin/bash
    - set -e (exit on error)
    - Echo banner: "=== SOC Agent System — Kubernetes Deployment ==="

    - Step 1: Check prerequisites
      - Verify kind, kubectl, helm, docker are installed
      - Print versions

    - Step 2: Create Kind cluster
      - kind create cluster --config kind-config.yaml --name soc-demo
      - Wait for cluster to be ready

    - Step 3: Build and load Docker images
      - cd to project root
      - docker build -t soc-backend:latest -f backend/Dockerfile backend/
      - docker build -t soc-frontend:latest -f frontend/Dockerfile frontend/
      - kind load docker-image soc-backend:latest --name soc-demo
      - kind load docker-image soc-frontend:latest --name soc-demo
      - Echo "✅ Images loaded into Kind cluster"

    - Step 4: Install nginx ingress controller
      - kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
      - kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s
      - Echo "✅ Nginx ingress controller ready"

    - Step 5: Install SOC Agent System
      - helm install soc-agent ./charts/soc-agent --wait --timeout 5m
      - Echo "✅ SOC Agent System deployed"

    - Step 6: Verify deployment
      - kubectl get pods -l app=soc-backend
      - kubectl get pods -l app=redis
      - kubectl get hpa
      - kubectl get ingress
      - Echo "Waiting for backend pods to be ready..."
      - kubectl wait --for=condition=ready pod -l app=soc-backend --timeout=120s

    - Step 7: Print access instructions
      - Echo "=== Deployment Complete ==="
      - Echo "SOC Dashboard: http://localhost:8080"
      - Echo "Backend API: http://localhost:8080/api/threats"
      - Echo "Health Check: curl http://localhost:8080/health"
      - Echo ""
      - Echo "Backend Pods: $(kubectl get pods -l app=soc-backend --no-headers | wc -l)"
      - Echo "Redis Status: $(kubectl get pods -l app=redis --no-headers)"
      - Echo ""
      - Echo "To view logs: kubectl logs -l app=soc-backend --tail=50 -f"
      - Echo "To check HPA: kubectl get hpa -w"
      - Echo "To teardown: ./teardown.sh"

15. k8s/teardown.sh
    Purpose: Clean up Kind cluster
    Requirements:
    - Shebang: #!/bin/bash
    - Echo "=== Tearing down SOC Agent System ==="
    - kind delete cluster --name soc-demo
    - Echo "✅ Cluster deleted"
    - Echo "Note: Docker images remain cached. Run 'docker rmi soc-backend:latest soc-frontend:latest' to remove."

16. k8s/charts/soc-agent/README.md
    Purpose: Helm chart documentation
    Requirements:
    - Title: "SOC Agent System Helm Chart"
    - Description: Multi-agent threat analysis platform with observability

    - Prerequisites section:
      - Kubernetes 1.24+
      - Helm 3.8+
      - Nginx ingress controller

    - Quick Start section:
      - Local (Kind): ./deploy.sh
      - Manual: helm install soc-agent ./charts/soc-agent

    - Configuration section:
      - Table of key values.yaml parameters
      - redis.enabled, redis.image.*, redis.resources
      - backend.replicaCount, backend.image.*, backend.resources, backend.hpa.*
      - backend.env.REDIS_URL (REQUIRED for multi-pod deployment)
      - frontend.replicaCount, frontend.image.*
      - ingress.enabled, ingress.className, ingress.hosts

    - Production Deployment section:
      - Use values-production.yaml as override
      - helm install soc-agent ./charts/soc-agent -f values-production.yaml
      - Update image.repository to your registry
      - Enable TLS with cert-manager
      - Configure resource limits based on load testing

    - Upgrading section:
      - helm upgrade soc-agent ./charts/soc-agent

    - Uninstalling section:
      - helm uninstall soc-agent

    - Architecture section:
      - Explain Redis requirement for multi-pod deployment
      - "Backend pods share state via Redis for cross-pod WebSocket broadcasting"
      - "Without Redis, each pod has isolated state (split-brain problem)"
      - "Integration tests validate this architecture (backend/tests/test_redis_pubsub_integration.py)"

CRITICAL ARCHITECTURE NOTES:

1. Redis is REQUIRED for multi-pod deployment:
   - Backend pods share state via Redis (threat storage)
   - WebSocket real-time updates use Redis Pub/Sub channel "threats:events"
   - Without Redis, each pod has isolated state (split-brain problem)
   - Falls back to in-memory store if Redis unavailable (single pod only)

2. Backend MUST have REDIS_URL environment variable:
   - Set to: redis://{{ include "soc-agent.fullname" . }}-redis:6379
   - Backend will fail health checks if Redis is unreachable
   - Health endpoint /ready checks Redis connectivity

3. Integration tests validate this architecture:
   - See backend/tests/test_redis_pubsub_integration.py
   - Tests simulate 3 pods with cross-pod WebSocket broadcasting
   - All 5 tests passing confirms Kubernetes-ready architecture
   - Test scenario: Deploy 3 pods → Connect 3 WebSocket clients → Trigger threat on Pod A → ALL 3 clients receive it

4. Horizontal Pod Autoscaling (HPA):
   - Backend can scale from 2 to 8 replicas
   - All replicas share Redis state
   - WebSocket clients can connect to any pod
   - All clients receive all threats via Redis Pub/Sub

5. Docker Images:
   - Backend: soc-backend:latest (built from backend/Dockerfile)
   - Frontend: soc-frontend:latest (built from frontend/Dockerfile)
   - Redis: redis:7-alpine (official image from Docker Hub)

CONSTRAINTS:
- All Kubernetes manifests must use Helm templating (no hardcoded values)
- Label selectors must be consistent across all resources (use _helpers.tpl)
- Chart must pass: helm lint ./charts/soc-agent
- Chart must be cloud-agnostic (no GCP/AWS/Azure specific resources)
- Images use pullPolicy: Never for Kind, Always for production
- All scripts must be executable (chmod +x)
- Scripts must have proper error handling (set -e, check prerequisites)

VERIFICATION CHECKLIST:
After generation, the following should work:

1. Helm validation:
   - cd k8s && helm lint ./charts/soc-agent
   - helm template soc-agent ./charts/soc-agent --debug

2. Kind deployment:
   - cd k8s && ./deploy.sh
   - kubectl get pods (all Running)
   - kubectl get hpa (shows configured HPA)
   - curl http://localhost:8080/health (returns 200)
   - kubectl logs -l app=soc-backend (shows JSON logs)

3. Cleanup:
   - ./teardown.sh
   - kind get clusters (should not show soc-demo)

4. Production values:
   - helm template soc-agent ./charts/soc-agent -f values-production.yaml
   - Verify replicas=4, resources increased, pullPolicy=Always

INTERVIEW TALKING POINTS:
Include these in README.md or NOTES.txt:

1. "This Helm chart is cloud-agnostic — same chart deploys to Kind, GKE, EKS, or AKS.
   I just swap values files for the target environment."

2. "I separated infrastructure provisioning (Terraform for cloud resources) from
   application deployment (Helm for K8s resources). For this demo, there's no cloud
   to provision, so Helm is the right and only tool needed."

3. "The HPA is configured but won't trigger on Kind without metrics-server. On a real
   cluster, I'd use 'kubectl top pods' during the Locust test to show CPU climbing
   toward the scale threshold."

4. "Resource requests and limits are production-ready — I sized them based on load
   testing results from Block 3. In production, I'd tune these further with VPA
   (VerticalPodAutoscaler) recommendations."

5. "Health probes are configured with appropriate delays — readiness probe starts
   checking after 5s (app initializes fast), liveness probe after 10s with 30s
   intervals (don't restart unnecessarily)."

6. "Redis is critical for multi-pod deployment — all backend pods share state via Redis.
   WebSocket clients can connect to any pod and receive all threats via Redis Pub/Sub.
   I validated this with integration tests that simulate 3 pods with cross-pod broadcasting.
   Without Redis, you'd have a split-brain problem where each pod has isolated state."

OUTPUT STRUCTURE:
k8s/
├── kind-config.yaml
├── deploy.sh (executable)
├── teardown.sh (executable)
└── charts/
    └── soc-agent/
        ├── Chart.yaml
        ├── values.yaml
        ├── values-production.yaml
        ├── README.md
        └── templates/
            ├── _helpers.tpl
            ├── backend-deployment.yaml
            ├── backend-service.yaml
            ├── backend-hpa.yaml
            ├── backend-configmap.yaml
            ├── redis-deployment.yaml (NEW - REQUIRED)
            ├── redis-service.yaml (NEW - REQUIRED)
            ├── frontend-deployment.yaml
            ├── frontend-service.yaml
            ├── ingress.yaml
            └── NOTES.txt

All files should be production-ready with proper comments, error handling, and documentation.
```

---

## Success Criteria

After Intent generates these files, you should be able to:

1. **Validate the Helm chart:**
   ```bash
   cd k8s
   helm lint ./charts/soc-agent
   helm template soc-agent ./charts/soc-agent --debug
   ```

2. **Deploy to Kind:**
   ```bash
   ./deploy.sh
   # Wait ~2 minutes for all pods to be ready
   ```

3. **Verify deployment:**
   ```bash
   kubectl get pods -l app=soc-backend
   kubectl get pods -l app=redis
   kubectl get hpa
   curl http://localhost:8080/health
   ```

4. **Test the application:**
   ```bash
   # Trigger a threat
   curl -X POST http://localhost:8080/api/threats/trigger \
     -H "Content-Type: application/json" \
     -d '{"threat_type": "bot_traffic"}'

   # Check logs
   kubectl logs -l app=soc-backend --tail=20

   # Verify Redis connection
   kubectl exec -it $(kubectl get pod -l app=soc-backend -o jsonpath='{.items[0].metadata.name}') -- env | grep REDIS_URL
   ```

5. **Clean up:**
   ```bash
   ./teardown.sh
   ```

---

## Interview Demo Flow

When presenting this to Alex/Gui:

1. **Show the Helm chart structure:**
   - "Here's the chart — notice values.yaml vs values-production.yaml"
   - "All templates use _helpers.tpl for consistent labeling"

2. **Deploy to Kind:**
   - Run `./deploy.sh` live
   - Explain each step as it executes

3. **Show Kubernetes resources:**
   - `kubectl get pods` — show 2 backend replicas + 1 Redis pod
   - `kubectl get hpa` — explain autoscaling configuration
   - `kubectl get ingress` — show routing rules
   - `kubectl get svc` — show backend, frontend, and Redis services

4. **Demonstrate health probes:**
   - `kubectl describe pod <backend-pod>` — show liveness/readiness config
   - Explain why these matter for zero-downtime deployments

5. **Show cloud-agnostic design:**
   - Open values-production.yaml
   - "Same chart, different values — this is how I'd deploy to GKE/EKS/AKS"

6. **Discuss production considerations:**
   - Resource limits based on load testing
   - HPA configuration for auto-scaling
   - Pod anti-affinity for high availability
   - ConfigMaps for environment-specific config

---

## Fallback Plan

If Kind deployment fails during the interview:

1. **Show the Helm chart code:**
   - Walk through the templates
   - Explain the Helm templating logic

2. **Run helm template:**
   - `helm template soc-agent ./charts/soc-agent`
   - Show the rendered Kubernetes manifests

3. **Discuss the architecture:**
   - Use the scaling diagram from Block 6
   - Explain how this would work in production

4. **Fall back to Docker Compose:**
   - "The Docker Compose stack is the primary demo"
   - "This Helm chart shows how I'd productionize it"

---

## Next Steps After Generation

1. **Test the deployment:**
   - Run through the verification checklist
   - Fix any issues with the generated files

2. **Commit to git:**
   ```bash
   git add k8s/
   git commit -m "feat: add Kubernetes deployment with Kind and Helm

   BLOCK 4: Kind + Helm Kubernetes Deployment

   - Kind cluster config with 3 nodes (1 control-plane, 2 workers)
   - Helm chart with production-ready templates
   - HPA for backend autoscaling (2-8 replicas)
   - Health probes for liveness and readiness
   - Resource requests and limits
   - ConfigMaps for environment variables
   - Nginx ingress for routing
   - Deploy and teardown scripts
   - values-production.yaml for cloud deployment

   Demonstrates cloud-agnostic K8s deployment strategy."
   ```

3. **Tag the commit:**
   ```bash
   git tag -a block-4-k8s-deployment -m "Block 4: Kubernetes deployment complete"
   ```

4. **Update the main README:**
   - Add section on Kubernetes deployment
   - Link to k8s/charts/soc-agent/README.md

---

## Estimated Timeline

- **Intent generation:** 10-15 minutes
- **Testing and fixes:** 1-2 hours
- **Documentation review:** 30 minutes
- **Total:** ~3 hours

---

## Dependencies Check

Before running Intent, verify:

- ✅ Block 1 completed (health endpoints exist)
- ✅ Block 2 completed (Dockerfiles exist)
- ✅ Docker is running
- ✅ Kind is installed: `kind version`
- ✅ Kubectl is installed: `kubectl version --client`
- ✅ Helm is installed: `helm version`

If any are missing, install them first.

