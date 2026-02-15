"""Structured JSON logging with OpenTelemetry correlation."""
import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace


class OTelJsonFormatter(jsonlogger.JsonFormatter):
    """
    JSON formatter that adds OpenTelemetry trace correlation fields.
    
    Automatically injects trace_id and span_id from the current OTel context
    into every log record.
    """
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to the log record."""
        # Call parent to add standard fields
        super().add_fields(log_record, record, message_dict)

        # Add standard fields with our preferred names
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['logger_name'] = record.name
        log_record['module'] = record.module

        # Add OpenTelemetry trace correlation
        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                log_record['trace_id'] = format(ctx.trace_id, '032x')
                log_record['span_id'] = format(ctx.span_id, '016x')


def setup_json_logging(level: str = "INFO"):
    """
    Setup structured JSON logging with OpenTelemetry correlation.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Configure JSON formatter with standard fields
    # Note: Don't use rename_fields - it causes issues. We'll add fields manually in add_fields()
    formatter = OTelJsonFormatter(
        '%(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for structured logging.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance configured for JSON output
    """
    return logging.getLogger(name)

