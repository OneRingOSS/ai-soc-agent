"""Logging configuration for different verbosity levels."""
import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(level: str = "INFO", colored: bool = True):
    """
    Setup logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        colored: Whether to use colored output
    """
    log_format = '%(asctime)s | %(levelname)-8s | %(message)s'
    date_format = '%H:%M:%S'
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if colored and sys.stdout.isatty():
        formatter = ColoredFormatter(log_format, datefmt=date_format)
    else:
        formatter = logging.Formatter(log_format, datefmt=date_format)
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Convenience functions for different demo modes
def demo_mode_minimal():
    """Minimal logging - only show key events."""
    setup_logging("INFO", colored=True)


def demo_mode_detailed():
    """Detailed logging - show all agent activity."""
    setup_logging("DEBUG", colored=True)
    
    # Enable agent-specific loggers
    logging.getLogger("agents.coordinator").setLevel(logging.DEBUG)
    logging.getLogger("agents.base_agent").setLevel(logging.DEBUG)


def demo_mode_production():
    """Production-like logging - structured without colors."""
    setup_logging("INFO", colored=False)

