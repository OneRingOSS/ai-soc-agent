"""OpenTelemetry instrumentation for SOC Agent System."""
import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)


def init_telemetry() -> Optional[TracerProvider]:
    """
    Initialize OpenTelemetry SDK with OTLP exporter.

    Returns:
        TracerProvider instance if successful, None otherwise
    """
    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: "soc-agent-system"
        })

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Only add OTLP exporter if not in testing mode
        # In testing mode, the test fixture will add an InMemorySpanExporter
        is_testing = os.getenv("TESTING", "false").lower() == "true"

        if not is_testing:
            # Get OTLP endpoint from environment (default for testing)
            otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

            # Create OTLP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True  # For local development/testing
            )

            # Add span processor
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)

            logger.info(f"✅ OpenTelemetry initialized (endpoint: {otlp_endpoint})")
        else:
            logger.info("✅ OpenTelemetry initialized (testing mode - no OTLP exporter)")

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        return provider
        
    except Exception as e:
        logger.warning(f"⚠️  OpenTelemetry initialization failed: {e}")
        logger.warning("   Continuing without distributed tracing")
        return None


def get_tracer(name: str = __name__) -> trace.Tracer:
    """
    Get a tracer instance for creating custom spans.
    
    Args:
        name: Name of the tracer (typically __name__ of the module)
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def instrument_fastapi(app):
    """
    Auto-instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✅ FastAPI auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"⚠️  FastAPI instrumentation failed: {e}")

