# Integration Tests for Redis Pub/Sub Cross-Pod Broadcasting

## Overview

The integration tests in `test_redis_pubsub_integration.py` verify the **critical production behavior** that enables horizontal scaling in Kubernetes:

- Multiple backend pods can share state via Redis
- WebSocket clients connected to different pods all receive the same threats
- Redis Pub/Sub correctly broadcasts across all subscribers

These tests simulate the exact Kubernetes deployment scenario with 3 replicas.

---

## Prerequisites

### 1. Start Redis

The integration tests require a running Redis instance:

```bash
# Using Docker
docker run -d -p 6379:6379 --name redis-test redis:7-alpine

# Or using Docker Compose (from observability/ directory)
cd ../observability
docker-compose up -d redis
```

### 2. Verify Redis is Running

```bash
# Test connection
redis-cli ping
# Should return: PONG

# Or using Docker
docker exec redis-test redis-cli ping
```

---

## Running the Tests

### Run All Integration Tests

```bash
cd backend

# Run integration tests only
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py -v -m integration

# Run with detailed output
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py -v -m integration -s
```

### Run Specific Tests

```bash
# Test basic save/retrieve
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py::test_redis_store_save_and_retrieve -v -m integration

# Test single subscriber
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py::test_redis_pubsub_single_subscriber -v -m integration

# Test multiple clients on same pod
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py::test_redis_pubsub_multiple_subscribers_same_pod -v -m integration

# 🚀 Test cross-pod broadcasting (THE CRITICAL TEST)
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py::test_redis_pubsub_cross_pod_broadcasting -v -m integration -s

# Test multiple threats ordering
PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py::test_redis_pubsub_multiple_threats_ordering -v -m integration
```

### Run All Tests (Unit + Integration)

```bash
# Run everything
PYTHONPATH=src pytest tests/ -v

# Skip integration tests (for CI/CD without Redis)
PYTHONPATH=src pytest tests/ -v -m "not integration"
```

---

## Test Scenarios

### Test 1: Basic Save and Retrieve
**Purpose**: Verify Redis storage works correctly  
**What it tests**: `save_threat()` → `get_threat()`

### Test 2: Single Subscriber
**Purpose**: Verify Pub/Sub delivers to one subscriber  
**What it tests**: `save_threat()` → `publish()` → `subscribe_threats()`

### Test 3: Multiple Subscribers on Same Pod
**Purpose**: Simulate multiple WebSocket clients on the same backend pod  
**What it tests**: 3 clients on 1 pod all receive the threat

### Test 4: Cross-Pod Broadcasting ⭐ **CRITICAL**
**Purpose**: Simulate Kubernetes deployment with 3 replicas  
**What it tests**:
- 3 separate Redis connections (simulating 3 pods)
- 3 WebSocket clients connected to different pods
- Threat triggered on Pod A
- **ALL 3 clients receive the threat via Redis Pub/Sub**

**This is equivalent to**:
```bash
kubectl scale deployment soc-backend --replicas=3
# Connect 3 WebSocket clients to different pods
curl -X POST http://pod-a:8000/api/threats/trigger
# ALL 3 WebSocket clients receive the threat! ✅
```

### Test 5: Multiple Threats Ordering
**Purpose**: Verify threats are received in correct order  
**What it tests**: Sequential threat publishing and ordering

---

## Expected Output

When running the cross-pod broadcasting test, you should see:

```
tests/test_redis_pubsub_integration.py::test_redis_pubsub_cross_pod_broadcasting 
🚨 Triggering threat on Pod A...
⏳ Waiting for all WebSocket clients to receive the threat...

✅ Verifying cross-pod broadcasting...
✅ SUCCESS: All 3 WebSocket clients (on different pods) received the threat!
   - Client on Pod A: cross-pod-test-threat
   - Client on Pod B: cross-pod-test-threat
   - Client on Pod C: cross-pod-test-threat
PASSED
```

---

## Troubleshooting

### Redis Connection Refused

**Error**: `redis.exceptions.ConnectionError: Error 61 connecting to localhost:6379. Connection refused.`

**Solution**: Start Redis:
```bash
docker run -d -p 6379:6379 --name redis-test redis:7-alpine
```

### Tests Skipped

**Message**: `SKIPPED [1] tests/test_redis_pubsub_integration.py: Redis not available`

**Reason**: Tests are marked with `@pytest.mark.integration` and require Redis

**Solution**: 
1. Start Redis (see above)
2. Run with `-m integration` flag

### Timeout Errors

**Error**: `asyncio.exceptions.TimeoutError`

**Possible causes**:
1. Redis not running
2. Redis connection slow
3. Pub/Sub subscription not ready

**Solution**: Increase timeout or check Redis health

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Run integration tests
        run: |
          cd backend
          PYTHONPATH=src pytest tests/test_redis_pubsub_integration.py -v -m integration
```

---

## Why These Tests Matter

1. **Production Behavior**: Tests the exact architecture used in Kubernetes
2. **Horizontal Scaling**: Verifies multi-pod deployment works correctly
3. **No Split-Brain**: Ensures all pods share the same state
4. **Real-World Scenario**: Simulates actual user experience with multiple clients
5. **Interview Value**: Demonstrates understanding of distributed systems testing

---

## Next Steps

After integration tests pass:

1. **Deploy to Kubernetes** (Block 4)
2. **Test with real pods**: `kubectl scale deployment soc-backend --replicas=3`
3. **Load testing**: Use Locust to simulate hundreds of WebSocket clients
4. **Observability**: Monitor traces in Jaeger, metrics in Prometheus

---

**These integration tests prove that the SOC Agent System is production-ready for Kubernetes!** 🚀

