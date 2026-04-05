#!/usr/bin/env python3
"""Test build_redis_url() function for Tier 1F"""
import os
import sys


def build_redis_url() -> str:
    """
    Construct Redis URL from environment variables.
    Mirrors the OPENAI_API_KEY pattern: read from env, never hardcode.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_password = os.getenv("REDIS_PASSWORD", "").strip()

    if redis_password and "://" in redis_url:
        if "@" not in redis_url:
            scheme, rest = redis_url.split("://", 1)
            redis_url = f"{scheme}://:{redis_password}@{rest}"

    return redis_url


def test_redis_url():
    """Test suite for build_redis_url()"""
    # Test 1: With password
    os.environ["REDIS_URL"] = "redis://localhost:6379"
    os.environ["REDIS_PASSWORD"] = "testpass123"
    result = build_redis_url()
    expected = "redis://:testpass123@localhost:6379"
    assert result == expected, f"Test 1 failed: {result} != {expected}"
    print(f"✅ Test 1 (with password): {result}")

    # Test 2: Without password
    os.environ["REDIS_PASSWORD"] = ""
    result = build_redis_url()
    expected = "redis://localhost:6379"
    assert result == expected, f"Test 2 failed: {result} != {expected}"
    print(f"✅ Test 2 (no password): {result}")

    # Test 3: URL already has auth (backward compat)
    os.environ["REDIS_URL"] = "redis://:existingpass@localhost:6379"
    os.environ["REDIS_PASSWORD"] = "newpass"
    result = build_redis_url()
    # Should NOT double-inject password if @ already present
    assert "@" in result
    assert "newpass" not in result  # Should not inject new password
    print(f"✅ Test 3 (existing auth): {result}")

    # Test 4: Different Redis host
    os.environ["REDIS_URL"] = "redis://redis-service.soc-agent-demo.svc.cluster.local:6379"
    os.environ["REDIS_PASSWORD"] = "k8spassword"
    result = build_redis_url()
    expected = "redis://:k8spassword@redis-service.soc-agent-demo.svc.cluster.local:6379"
    assert result == expected, f"Test 4 failed: {result} != {expected}"
    print(f"✅ Test 4 (K8s service): {result}")

    # Test 5: Password masking for logs
    # Split before @ to hide password (redis://:password@host becomes redis://:password)
    masked = result.split("@")[0] if "@" in result else result
    # The masked part is "redis://:k8spassword" which still contains password!
    # Better masking: show only scheme + host
    if "@" in result:
        scheme_and_auth, host_part = result.split("@", 1)
        masked_for_logs = f"{scheme_and_auth.split(':')[0]}://***@{host_part}"
    else:
        masked_for_logs = result
    assert "k8spassword" not in masked_for_logs
    print(f"✅ Test 5 (log masking): {masked_for_logs}")

    print("\n✅ All build_redis_url() tests passed!")


if __name__ == "__main__":
    test_redis_url()
