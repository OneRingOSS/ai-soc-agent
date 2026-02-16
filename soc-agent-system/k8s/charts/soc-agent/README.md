# SOC Agent System Helm Chart

Multi-agent threat analysis platform with real-time WebSocket broadcasting, Redis-backed shared state, and full observability stack. Deploys to any Kubernetes cluster — Kind for local development, GKE/EKS/AKS for production.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- Nginx ingress controller (installed automatically by `deploy.sh` for Kind)
- Docker (for building images locally)

## Quick Start

### Local Development (Kind)

The fastest way to get running locally:

```bash
cd soc-agent-system/k8s
./deploy.sh
```

This script will:
1. Check prerequisites (kind, kubectl, helm, docker)
2. Create a Kind cluster with ingress support
3. Build and load Docker images
4. Install the nginx ingress controller
5. Deploy the SOC Agent System via Helm
6. Verify all pods are running

Access the dashboard at **http://localhost:8080** after deployment.

### Manual Installation

```bash
# Install with default values (local dev)
helm install soc-agent ./charts/soc-agent

# Install with production values
helm install soc-agent ./charts/soc-agent -f values-production.yaml

# Install with custom overrides
helm install soc-agent ./charts/soc-agent --set backend.replicaCount=4
```

## Configuration

Key parameters in `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Deploy Redis for shared state | `true` |
| `redis.image.repository` | Redis image | `redis` |
| `redis.image.tag` | Redis image tag | `7-alpine` |
| `redis.service.port` | Redis service port | `6379` |
| `redis.resources.requests.cpu` | Redis CPU request | `50m` |
| `redis.resources.requests.memory` | Redis memory request | `128Mi` |
| `backend.replicaCount` | Number of backend pods | `2` |
| `backend.image.repository` | Backend image | `soc-backend` |
| `backend.image.tag` | Backend image tag | `latest` |
| `backend.image.pullPolicy` | Image pull policy | `Never` (Kind) |
| `backend.service.port` | Backend service port | `8000` |
| `backend.resources.requests.cpu` | Backend CPU request | `100m` |
| `backend.resources.requests.memory` | Backend memory request | `256Mi` |
| `backend.hpa.enabled` | Enable horizontal pod autoscaling | `true` |
| `backend.hpa.minReplicas` | Minimum backend replicas | `2` |
| `backend.hpa.maxReplicas` | Maximum backend replicas | `8` |
| `backend.hpa.targetCPUUtilizationPercentage` | CPU threshold for scaling | `70` |
| `backend.env.REDIS_URL` | Redis connection URL (**required** for multi-pod) | `redis://<release>-redis:6379` |
| `backend.env.OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint | `http://otel-collector:4317` |
| `backend.env.LOG_LEVEL` | Application log level | `INFO` |
| `frontend.replicaCount` | Number of frontend pods | `1` |
| `frontend.image.repository` | Frontend image | `soc-frontend` |
| `frontend.image.tag` | Frontend image tag | `latest` |
| `frontend.image.pullPolicy` | Image pull policy | `Never` (Kind) |
| `ingress.enabled` | Enable ingress routing | `true` |
| `ingress.className` | Ingress class | `nginx` |
| `ingress.hosts[0].host` | Ingress hostname | `localhost` |

## Architecture

### Why Redis is Required for Multi-Pod Deployment

Backend pods share state via Redis for cross-pod WebSocket broadcasting. This is the critical architectural decision that enables horizontal scaling:

- **Shared State**: All threat data is stored in Redis, so any pod can serve any request
- **WebSocket Broadcasting**: Real-time updates use Redis Pub/Sub channel `threats:events` — when a threat is detected on Pod A, all WebSocket clients connected to Pods B and C also receive the update
- **Without Redis**: Each pod has isolated in-memory state (split-brain problem) — clients connected to different pods see different data
- **Fallback**: The backend falls back to in-memory storage if Redis is unavailable, but this only works for single-pod deployments

### Integration Test Validation

This architecture is validated by integration tests (`backend/tests/test_redis_pubsub_integration.py`) that simulate 3 pods with cross-pod WebSocket broadcasting. All 5 tests confirm that:
- Threats created on one pod are visible from all pods
- WebSocket clients connected to any pod receive all real-time updates
- Redis Pub/Sub correctly broadcasts across pod boundaries

### Component Diagram

```
┌─────────────┐     ┌──────────────────────────────────┐
│   Browser    │────▶│         Nginx Ingress             │
└─────────────┘     │  /     → frontend:80               │
                    │  /api  → backend:8000               │
                    │  /ws   → backend:8000               │
                    └──────────────────────────────────┘
                              │              │
                    ┌─────────▼──┐    ┌──────▼───────┐
                    │  Frontend  │    │   Backend     │
                    │  (nginx)   │    │  Pod 1..N     │
                    │  port: 80  │    │  port: 8000   │
                    └────────────┘    └──────┬────────┘
                                             │
                                      ┌──────▼────────┐
                                      │    Redis       │
                                      │  (Pub/Sub +    │
                                      │   State Store) │
                                      │  port: 6379    │
                                      └───────────────┘
```

## Production Deployment

For production environments (GKE, EKS, AKS):

```bash
# Deploy with production values
helm install soc-agent ./charts/soc-agent -f values-production.yaml

# Or override specific values
helm install soc-agent ./charts/soc-agent \
  -f values-production.yaml \
  --set backend.image.repository=gcr.io/my-project/soc-backend \
  --set frontend.image.repository=gcr.io/my-project/soc-frontend
```

Production checklist:
- Update `image.repository` to your container registry (e.g., `gcr.io/my-project/soc-backend`)
- Set `image.pullPolicy: Always` to pull from registry
- Enable TLS with cert-manager (`ingress.tls` configuration)
- Configure resource limits based on load testing results
- Set `redis.persistence.enabled: true` for data durability
- Review HPA settings and adjust based on expected traffic

## Upgrading

```bash
# Upgrade with current values
helm upgrade soc-agent ./charts/soc-agent

# Upgrade with new values
helm upgrade soc-agent ./charts/soc-agent -f values-production.yaml

# Rollback if needed
helm rollback soc-agent
```

## Uninstalling

```bash
# Remove the Helm release
helm uninstall soc-agent

# For Kind clusters, use the teardown script (also deletes the cluster)
./teardown.sh
```

## Interview Talking Points

Key design decisions and trade-offs to discuss:

1. **Cloud-Agnostic Design**: This Helm chart is cloud-agnostic — the same chart deploys to Kind, GKE, EKS, or AKS. I just swap values files for the target environment.

2. **Infrastructure vs Application Separation**: I separated infrastructure provisioning (Terraform for cloud resources) from application deployment (Helm for K8s resources). For this demo, there's no cloud to provision, so Helm is the right and only tool needed.

3. **HPA on Kind**: The HPA is configured but won't trigger on Kind without metrics-server. On a real cluster, I'd use `kubectl top pods` during the Locust test to show CPU climbing toward the scale threshold.

4. **Resource Sizing**: Resource requests and limits are production-ready — I sized them based on load testing results from Block 3. In production, I'd tune these further with VPA (VerticalPodAutoscaler) recommendations.

5. **Health Probe Timing**: Health probes are configured with appropriate delays — readiness probe starts checking after 5s (app initializes fast), liveness probe after 10s with 30s intervals (don't restart unnecessarily).

6. **Redis for Multi-Pod State**: Redis is critical for multi-pod deployment — all backend pods share state via Redis. WebSocket clients can connect to any pod and receive all threats via Redis Pub/Sub. I validated this with integration tests that simulate 3 pods with cross-pod broadcasting. Without Redis, you'd have a split-brain problem where each pod has isolated state.

## Troubleshooting

```bash
# Check pod status
kubectl get pods -l app=soc-backend
kubectl get pods -l app=redis

# View backend logs
kubectl logs -l app=soc-backend --tail=50

# Check Redis connectivity from a backend pod
kubectl exec -it <backend-pod> -- env | grep REDIS_URL

# Check HPA status
kubectl get hpa

# Check ingress
kubectl get ingress
kubectl describe ingress

# Restart a deployment
kubectl rollout restart deployment/<release-name>-backend
```
