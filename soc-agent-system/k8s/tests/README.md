# SOC Agent Kubernetes Integration Tests

Comprehensive integration test suite for validating the SOC Agent Kubernetes deployment using Helm charts.

## Overview

This comprehensive test suite validates production-ready Kubernetes deployments with:

### Core Integration Tests
- ✅ Helm chart deployment to Kind cluster
- ✅ Pod health and readiness
- ✅ Service connectivity (backend, frontend, Redis)
- ✅ Backend API endpoints (/health, /ready, /metrics, /api/threats)
- ✅ Frontend accessibility
- ✅ End-to-end threat creation and retrieval
- ✅ Redis connectivity and cross-pod communication

### Advanced Test Suites
- ✅ **Observability Stack**: Prometheus, Grafana, Jaeger, Loki integration
- ✅ **Horizontal Pod Autoscaling (HPA)**: Load-based scaling (2-8 replicas)
- ✅ **Ingress Routing**: Frontend, API, and WebSocket routing
- ✅ **Resilience Testing**: Pod failures, fallback mechanisms, rolling updates
- ✅ **Performance Testing**: Locust load tests, cross-pod state sharing

## Prerequisites

Before running the tests, ensure you have:

1. **Docker** - For running Kind cluster
2. **kubectl** - Kubernetes CLI tool
3. **helm** - Helm package manager (v3+)
4. **kind** - Kubernetes in Docker
5. **curl** - For HTTP testing

### Install Prerequisites (macOS)

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install tools
brew install kubectl helm kind

# Verify installations
kubectl version --client
helm version
kind version
```

## Test Suite Structure

```
tests/
├── README.md                    # This file
├── run_all_tests.sh             # Master test runner (runs all suites)
├── integration_test.sh          # Main integration test suite (9 tests)
├── test_connectivity.sh         # Connectivity and E2E tests (10 tests)
├── test_observability.sh        # Observability stack tests (5 tests)
├── test_hpa.sh                  # HPA autoscaling tests (6 tests)
├── test_ingress.sh              # Ingress routing tests (5 tests)
├── test_resilience.sh           # Resilience and recovery tests (4 tests)
├── test_performance.sh          # Performance and load tests (5 tests)
├── cleanup.sh                   # Cleanup script for test environment
├── check_prerequisites.sh       # Prerequisites checker
└── setup_and_test.sh            # Combined setup and test runner
```

**Total: 44 automated tests across 7 test suites**

## Running the Tests

### Quick Start: Run All Tests

Run the complete test suite with a single command:

```bash
cd soc-agent-system/k8s/tests
chmod +x *.sh
./run_all_tests.sh              # Run all tests, leave deployments running
./run_all_tests.sh --cleanup    # Run all tests, cleanup after each
```

This master runner executes all 7 test suites in sequence:
1. Integration Tests (9 tests)
2. Connectivity Tests (10 tests)
3. Observability Stack Tests (5 tests)
4. HPA Tests (6 tests)
5. Ingress Tests (5 tests)
6. Resilience Tests (4 tests)
7. Performance Tests (5 tests)

### Individual Test Suites

#### 1. Integration Tests (Basic Deployment)

```bash
./integration_test.sh              # Run tests, leave deployment running
./integration_test.sh --cleanup    # Run tests, then cleanup deployment
```

**Tests:**
- ✅ Prerequisites check (kubectl, helm, kind)
- ✅ Helm chart deployment
- ✅ Pod health and readiness
- ✅ Service existence
- ✅ Backend health endpoint

#### 2. Connectivity Tests (E2E Scenarios)

```bash
./test_connectivity.sh
```

**Tests:**
- ✅ Backend API endpoints (/health, /ready, /metrics, /api/threats)
- ✅ Frontend accessibility
- ✅ Threat creation and retrieval (E2E)
- ✅ Redis connectivity
- ✅ WebSocket connections

#### 3. Observability Stack Tests

```bash
./test_observability.sh              # Run tests, leave stack running
./test_observability.sh --cleanup    # Run tests, then cleanup
```

**Tests:**
- ✅ Deploy Prometheus, Grafana, Jaeger, Loki
- ✅ Prometheus metrics scraping
- ✅ Grafana dashboard accessibility
- ✅ Jaeger trace collection
- ✅ Loki log aggregation

**Prerequisites:** Docker Compose must be installed

#### 4. HPA Tests (Horizontal Pod Autoscaler)

```bash
./test_hpa.sh              # Run tests, leave deployment running
./test_hpa.sh --cleanup    # Run tests, then cleanup
```

**Tests:**
- ✅ Deploy with HPA enabled (min 2, max 8 replicas)
- ✅ Verify HPA configuration
- ✅ Generate load to trigger scale-up
- ✅ Verify pods scale up (2 → 8 replicas)
- ✅ Test Redis Pub/Sub across replicas
- ✅ Verify scale-down after load decreases

#### 5. Ingress Tests (Routing)

```bash
./test_ingress.sh              # Run tests, leave deployment running
./test_ingress.sh --cleanup    # Run tests, then cleanup
```

**Tests:**
- ✅ Install nginx ingress controller
- ✅ Deploy with Ingress enabled
- ✅ Test frontend routing (/)
- ✅ Test backend API routing (/api/*)
- ✅ Test WebSocket routing (/ws)

**Note:** Add `127.0.0.1 soc-agent.local` to `/etc/hosts`

#### 6. Resilience Tests (Failures & Recovery)

```bash
./test_resilience.sh              # Run tests, leave deployment running
./test_resilience.sh --cleanup    # Run tests, then cleanup
```

**Tests:**
- ✅ Kill Redis pod, verify backend fallback to in-memory store
- ✅ Kill backend pod, verify automatic recovery
- ✅ Test rolling update with zero downtime
- ✅ Continuous health checks during updates

#### 7. Performance Tests (Load Testing)

```bash
./test_performance.sh              # Run tests, leave deployment running
./test_performance.sh --cleanup    # Run tests, then cleanup
```

**Tests:**
- ✅ Deploy with 3 backend replicas
- ✅ Run Locust load test (60s, 10 users)
- ✅ Verify cross-pod state sharing via Redis
- ✅ Measure response times
- ✅ Generate HTML/CSV reports

**Prerequisites:** Locust must be installed (`pip install locust`)

### Custom Namespace/Release

```bash
# Set custom namespace and release name
export NAMESPACE=my-test-namespace
export RELEASE_NAME=my-soc-agent

# Run any test suite
./integration_test.sh
./test_connectivity.sh
./test_hpa.sh
```

## Building Docker Images for Kind

Before deploying to Kind, you need to build and load the Docker images:

```bash
# Navigate to project root
cd soc-agent-system

# Build backend image
cd backend
docker build -t soc-backend:latest -f Dockerfile .

# Build frontend image
cd ../frontend
docker build -t soc-frontend:latest -f Dockerfile .

# Load images into Kind cluster
kind load docker-image soc-backend:latest --name soc-agent-cluster
kind load docker-image soc-frontend:latest --name soc-agent-cluster
```

## Complete End-to-End Test Flow

```bash
# 1. Create Kind cluster (if not exists)
cd soc-agent-system/k8s
kind create cluster --name soc-agent-cluster --config kind-config.yaml

# 2. Build and load Docker images
cd ../backend
docker build -t soc-backend:latest -f Dockerfile .
cd ../frontend
docker build -t soc-frontend:latest -f Dockerfile .

kind load docker-image soc-backend:latest --name soc-agent-cluster
kind load docker-image soc-frontend:latest --name soc-agent-cluster

# 3. Run integration tests
cd ../k8s/tests
chmod +x *.sh
./integration_test.sh

# 4. Run connectivity tests
./test_connectivity.sh

# 5. Cleanup (see Cleanup section below)
cd tests
./cleanup.sh                        # Cleanup deployment only
./cleanup.sh --delete-cluster       # Cleanup deployment and Kind cluster
```

## Test Output

### Successful Test Run

```
[INFO] =========================================
[INFO] SOC Agent K8s Integration Test Suite
[INFO] =========================================

[INFO] Checking prerequisites...
[✓] kubectl found
[✓] helm found
[✓] Connected to Kubernetes cluster
[INFO] Deploying Helm chart...
[✓] Helm chart deployed successfully
[INFO] Checking if all pods are running...
[✓] All pods are running
[INFO] Checking if services exist...
[✓] Service backend exists
[✓] Service frontend exists
[✓] Service redis exists
[INFO] Testing backend health endpoint...
[✓] Backend health check passed

[INFO] =========================================
[INFO] Test Summary
[INFO] =========================================
[✓] Tests passed: 9
[✓] All tests passed!
```

### Failed Test Run

```
[✗] Backend health check failed
[✗] Tests failed: 1

[✗] Failed tests:
  - Backend health check failed
```

## Cleanup

After running tests, you should clean up the test environment to free up resources.

### Option 1: Cleanup Deployment Only

Removes the Helm release and namespace, but keeps the Kind cluster running:

```bash
cd soc-agent-system/k8s/tests
./cleanup.sh
```

This is useful if you want to run tests again without recreating the cluster.

### Option 2: Cleanup Everything

Removes the Helm release, namespace, AND deletes the Kind cluster:

```bash
cd soc-agent-system/k8s/tests
./cleanup.sh --delete-cluster
```

This completely removes all test resources.

### Option 3: Cleanup During Test Run

Run tests and automatically cleanup afterwards:

```bash
cd soc-agent-system/k8s/tests
./integration_test.sh --cleanup
```

### Manual Cleanup

If the cleanup script fails, you can manually clean up:

```bash
# Uninstall Helm release
helm uninstall soc-agent-test -n soc-agent-test

# Delete namespace
kubectl delete namespace soc-agent-test

# Delete Kind cluster
kind delete cluster --name soc-agent-cluster

# Kill any port-forwards
pkill -f "kubectl port-forward"
```

### What Gets Cleaned Up

The cleanup process removes:
- ✅ All Kubernetes pods (backend, frontend, Redis)
- ✅ All Kubernetes services
- ✅ ConfigMaps and Secrets
- ✅ Helm release
- ✅ Kubernetes namespace
- ✅ Port-forward processes
- ✅ (Optional) Kind cluster and Docker containers

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n soc-agent-test

# Check pod logs
kubectl logs -n soc-agent-test <pod-name>

# Describe pod for events
kubectl describe pod -n soc-agent-test <pod-name>
```

### Images Not Found

```bash
# Verify images are loaded in Kind
docker exec -it soc-agent-cluster-control-plane crictl images

# Reload images if needed
kind load docker-image soc-backend:latest --name soc-agent-cluster
kind load docker-image soc-frontend:latest --name soc-agent-cluster
```

### Port-Forward Issues

```bash
# Kill existing port-forwards
pkill -f "kubectl port-forward"

# Manually test port-forward
kubectl port-forward -n soc-agent-test service/soc-agent-test-backend 8080:8000
curl http://localhost:8080/health
```

## Cleanup

```bash
# Delete test namespace
kubectl delete namespace soc-agent-test

# Or use teardown script
cd soc-agent-system/k8s
./teardown.sh

# Delete Kind cluster
kind delete cluster --name soc-agent-cluster
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run K8s Integration Tests
  run: |
    kind create cluster --config k8s/kind-config.yaml
    docker build -t soc-backend:latest backend/
    docker build -t soc-frontend:latest frontend/
    kind load docker-image soc-backend:latest
    kind load docker-image soc-frontend:latest
    cd k8s/tests && ./integration_test.sh
```

## Test Coverage Summary

| Test Suite | Tests | Coverage |
|------------|-------|----------|
| Integration Tests | 9 | Basic deployment, pod health, services |
| Connectivity Tests | 10 | API endpoints, E2E flows, WebSocket |
| Observability Tests | 5 | Prometheus, Grafana, Jaeger, Loki |
| HPA Tests | 6 | Autoscaling, load generation, Redis Pub/Sub |
| Ingress Tests | 5 | Routing, frontend/backend/WebSocket |
| Resilience Tests | 4 | Pod failures, fallback, rolling updates |
| Performance Tests | 5 | Load testing, cross-pod state, response times |
| **Total** | **44** | **Complete production-ready validation** |

## Interview Talking Points

When discussing these tests in interviews:

1. **Production Readiness**: "We have 44 automated tests across 7 test suites validating the entire K8s deployment"
2. **Automation**: "Tests can run in CI/CD pipelines with a single command to catch deployment issues early"
3. **Coverage**: "We test everything from basic deployment to advanced scenarios like HPA, resilience, and performance"
4. **Observability**: "Full observability stack integration with Prometheus, Grafana, Jaeger, and Loki"
5. **Scalability**: "HPA tests verify automatic scaling from 2 to 8 replicas based on load"
6. **Resilience**: "Tests validate graceful degradation (Redis fallback) and zero-downtime rolling updates"
7. **Performance**: "Locust load tests measure response times and verify cross-pod state sharing via Redis"
8. **Cleanup**: "All tests include cleanup flags to ensure no resource leaks"

