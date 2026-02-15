"""Test helper functions for SOC Agent System tests."""
import time
import json
from typing import Dict, Any, Optional
from httpx import AsyncClient


async def trigger_threat(client: AsyncClient, signal_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a POST request to /api/threats/trigger with a threat signal.
    
    Args:
        client: AsyncClient instance
        signal_dict: Dictionary containing threat signal data
        
    Returns:
        Response JSON as dictionary
    """
    response = await client.post("/api/threats/trigger", json=signal_dict)
    response.raise_for_status()
    return response.json()


async def get_metrics(client: AsyncClient) -> str:
    """
    Send a GET request to /metrics endpoint.
    
    Args:
        client: AsyncClient instance
        
    Returns:
        Prometheus metrics text
    """
    response = await client.get("/metrics")
    response.raise_for_status()
    return response.text


def parse_prometheus_metric(metrics_text: str, metric_name: str) -> Optional[float]:
    """
    Extract a metric value from Prometheus text format.
    
    Args:
        metrics_text: Full Prometheus metrics text
        metric_name: Name of the metric to extract
        
    Returns:
        Metric value as float, or None if not found
    """
    for line in metrics_text.split('\n'):
        if line.startswith(metric_name):
            # Parse format: metric_name{labels} value
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return float(parts[-1])
                except ValueError:
                    continue
    return None


async def get_health(client: AsyncClient) -> Dict[str, Any]:
    """
    Send a GET request to /health endpoint.
    
    Args:
        client: AsyncClient instance
        
    Returns:
        Health check response as dictionary
    """
    response = await client.get("/health")
    response.raise_for_status()
    return response.json()


async def get_ready(client: AsyncClient) -> Dict[str, Any]:
    """
    Send a GET request to /ready endpoint.
    
    Args:
        client: AsyncClient instance
        
    Returns:
        Readiness check response as dictionary
    """
    response = await client.get("/ready")
    response.raise_for_status()
    return response.json()


def assert_json_log_format(log_line: str) -> Dict[str, Any]:
    """
    Validate that a log line is in JSON format and return parsed dict.
    
    Args:
        log_line: Single line of log output
        
    Returns:
        Parsed JSON log as dictionary
        
    Raises:
        AssertionError: If log line is not valid JSON
    """
    try:
        log_dict = json.loads(log_line)
        assert isinstance(log_dict, dict), "Log line must be a JSON object"
        return log_dict
    except json.JSONDecodeError as e:
        raise AssertionError(f"Log line is not valid JSON: {e}")


def wait_for_spans(exporter, expected_count: int, timeout: float = 5.0) -> bool:
    """
    Poll the InMemorySpanExporter until expected number of spans are collected.
    
    Args:
        exporter: InMemorySpanExporter instance
        expected_count: Number of spans to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if expected spans were collected, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        spans = exporter.get_finished_spans()
        if len(spans) >= expected_count:
            return True
        time.sleep(0.1)
    return False

