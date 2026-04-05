#!/bin/bash
# Docker Networking Diagnostic Script
# Run this to diagnose why Docker builds are failing

echo "═══════════════════════════════════════════════════════════"
echo "  Docker Networking Diagnostics"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Test 1: Docker daemon running
echo "[Test 1/7] Checking if Docker daemon is running..."
if docker info &>/dev/null; then
    echo "✅ PASS: Docker daemon is running"
else
    echo "❌ FAIL: Docker daemon not running"
    echo "Fix: Restart Docker Desktop"
    exit 1
fi
echo ""

# Test 2: Internet connectivity from Docker
echo "[Test 2/7] Testing internet connectivity from Docker..."
if docker run --rm alpine ping -c 3 google.com &>/dev/null; then
    echo "✅ PASS: Docker can reach internet"
else
    echo "❌ FAIL: Docker cannot reach internet"
    echo "Fix: Check VPN, firewall, or Docker network settings"
    exit 1
fi
echo ""

# Test 3: Docker Hub connectivity
echo "[Test 3/7] Testing Docker Hub connectivity..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://registry-1.docker.io/v2/)
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "200" ]; then
    echo "✅ PASS: Docker Hub is reachable (HTTP $HTTP_CODE)"
else
    echo "❌ FAIL: Cannot reach Docker Hub (HTTP $HTTP_CODE)"
    echo "Fix: Check firewall, VPN, or DNS"
    exit 1
fi
echo ""

# Test 4: DNS resolution
echo "[Test 4/7] Testing DNS resolution from Docker..."
if docker run --rm alpine nslookup docker.io &>/dev/null; then
    echo "✅ PASS: Docker can resolve docker.io"
    docker run --rm alpine nslookup docker.io 2>/dev/null | grep -A 2 "Name:"
else
    echo "❌ FAIL: Docker cannot resolve docker.io"
    echo "Fix: Change Docker DNS to 8.8.8.8"
    exit 1
fi
echo ""

# Test 5: Docker Hub rate limiting
echo "[Test 5/7] Checking Docker Hub rate limit..."
TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull" | jq -r .token 2>/dev/null)
if [ -n "$TOKEN" ]; then
    RATE_LIMIT=$(curl -s -H "Authorization: Bearer $TOKEN" https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest -I 2>/dev/null | grep -i "ratelimit-remaining" | cut -d: -f2 | cut -d\; -f1 | tr -d ' ')
    if [ -n "$RATE_LIMIT" ] && [ "$RATE_LIMIT" -gt 0 ]; then
        echo "✅ PASS: Rate limit OK ($RATE_LIMIT pulls remaining)"
    else
        echo "⚠️  WARNING: Rate limit exhausted or cannot determine"
        echo "Fix: Login to Docker Hub with 'docker login'"
    fi
else
    echo "⚠️  WARNING: Cannot check rate limit (jq not installed or auth failed)"
fi
echo ""

# Test 6: Can pull a small image
echo "[Test 6/7] Testing image pull (alpine:latest)..."
if timeout 30 docker pull alpine:latest &>/dev/null; then
    echo "✅ PASS: Can pull images from Docker Hub"
else
    echo "❌ FAIL: Cannot pull images (timeout or error)"
    echo "Fix: Restart Docker, clear cache, or check network"
    exit 1
fi
echo ""

# Test 7: Build cache status
echo "[Test 7/7] Checking Docker build cache..."
BUILD_CACHE=$(docker system df -v 2>/dev/null | grep "Build Cache" | awk '{print $3}')
if [ -n "$BUILD_CACHE" ]; then
    echo "Build cache size: $BUILD_CACHE"
    echo "💡 TIP: If cache is very large, try: docker builder prune -a -f"
else
    echo "⚠️  Cannot determine build cache size"
fi
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  ✅ All critical tests passed!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Docker networking is healthy. The build timeout was likely:"
echo "  1. Temporary Docker Hub slowness (retry build)"
echo "  2. VPN/network instability (restart network)"
echo "  3. Docker Desktop issue (restart Docker Desktop)"
echo ""
echo "Try rebuilding with:"
echo "  cd soc-agent-system/backend"
echo "  docker build -t soc-backend:latest . --progress=plain"
echo "  (--progress=plain shows detailed output)"
