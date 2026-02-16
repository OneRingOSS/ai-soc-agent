# SOC Agent Kubernetes Integration Tests

Comprehensive integration test suite for validating the SOC Agent Kubernetes deployment using Helm charts.

## Overview

This test suite validates:
- ✅ Helm chart deployment to Kind cluster
- ✅ Pod health and readiness
- ✅ Service connectivity (backend, frontend, Redis)
- ✅ Backend API endpoints (/health, /ready, /metrics, /api/threats)
- ✅ Frontend accessibility
- ✅ End-to-end threat creation and retrieval
- ✅ Redis connectivity and cross-pod communication

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
├── integration_test.sh          # Main integration test suite
└── test_connectivity.sh         # Connectivity and E2E tests
```

## Running the Tests

### Option 1: Full Integration Test Suite

Runs complete deployment and validation:

```bash
cd soc-agent-system/k8s/tests
chmod +x *.sh
./integration_test.sh
```

This will:
1. Check prerequisites (kubectl, helm, kind)
2. Deploy Helm chart to test namespace
3. Wait for all pods to be ready
4. Verify services exist
5. Test backend health endpoint

### Option 2: Connectivity Tests Only

Assumes deployment already exists:

```bash
cd soc-agent-system/k8s/tests
./test_connectivity.sh
```

This will:
1. Port-forward to backend and frontend services
2. Test all backend API endpoints
3. Test frontend accessibility
4. Create a threat and verify E2E flow
5. Test Redis connectivity

### Option 3: Custom Namespace/Release

```bash
# Set custom namespace and release name
export NAMESPACE=my-test-namespace
export RELEASE_NAME=my-soc-agent

# Run tests
./integration_test.sh
./test_connectivity.sh
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

# 5. Cleanup (optional)
cd ..
./teardown.sh
kind delete cluster --name soc-agent-cluster
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

## Interview Talking Points

When discussing these tests in interviews:

1. **Production Readiness**: "We have comprehensive integration tests that validate the entire K8s deployment"
2. **Automation**: "Tests can run in CI/CD pipelines to catch deployment issues early"
3. **Coverage**: "We test pod health, service connectivity, API endpoints, and end-to-end flows"
4. **Observability**: "Tests validate health/ready probes and metrics endpoints"
5. **Scalability**: "Tests verify Redis-based state sharing across multiple backend replicas"

