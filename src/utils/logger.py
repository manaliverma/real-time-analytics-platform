"""
Centralized logging configuration for the real-time analytics platform.

Provides structured logging with correlation IDs, JSON formatting,
and configurable log levels.
"""

import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from pythonjsonlogger import jsonlogger


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to all log records."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self.correlation_id = correlation_id or "default"
    
    def filter(self, record):
        record.correlation_id = self.correlation_id
        record.timestamp = datetime.utcnow().isoformat()
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id


def setup_logger(
    name: str,
    level: int = logging.INFO,
    correlation_id: Optional[str] = None,
    json_output: bool = True,
) -> logging.Logger:
    """
    Setup and configure a logger with structured logging.
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (INFO, DEBUG, WARNING, ERROR)
        correlation_id: Optional correlation ID for tracing
        json_output: Whether to output as JSON (True) or text (False)
    
    Returns:
        Configured logger instance
    
    Example:
        logger = setup_logger(__name__, level=logging.DEBUG)
        logger.info("Processing event", extra={"event_id": "123"})
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Add correlation ID filter
    correlation_filter = CorrelationIDFilter(correlation_id)
    logger.addFilter(correlation_filter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if json_output:
        # JSON formatter for production
        formatter = StructuredFormatter()
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    **kwargs
) -> None:
    """
    Log an event with additional context.
    
    Args:
        logger: Logger instance
        event_type: Type of event (e.g., "event_processed", "error_occurred")
        message: Log message
        **kwargs: Additional context data
    
    Example:
        log_event(logger, "event_processed", 
                  "Successfully processed event",
                  event_id="123", processing_time_ms=45)
    """
    extra = {
        "event_type": event_type,
        **kwargs
    }
    logger.info(message, extra=extra)


# Silence noisy loggers
logging.getLogger("kafka").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("clickhouse_driver").setLevel(logging.WARNING)
