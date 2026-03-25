"""
Staging-Only Test Suite - Tests that can run in K8s staging environment.

This test suite excludes:
- Tests requiring local Redis connection
- Tests requiring local file system access
- Tests with pre-existing failures (adversarial test expectation mismatches)

Run with:
    export BACKEND_URL=http://localhost:8080
    python -m pytest tests/test_staging_only.py -v
"""
import pytest
import os

# Import all staging-compatible test modules
from test_staging_vt_integration import *

# Mark all tests in this file as staging tests
pytestmark = pytest.mark.staging


def test_staging_environment_configured():
    """Verify staging environment is properly configured."""
    backend_url = os.getenv("BACKEND_URL")
    assert backend_url is not None, "BACKEND_URL environment variable must be set"
    assert "localhost:8080" in backend_url or "staging" in backend_url, \
        f"BACKEND_URL should point to staging environment, got: {backend_url}"


# Additional staging tests can be added here
# These should only test the deployed K8s environment, not local services

