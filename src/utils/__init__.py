"""
Utility functions and helpers for the analytics platform.

Includes logging, metrics, configuration management, and common helpers.
"""

from src.utils.logger import setup_logger, log_event
from src.utils.metrics import Timer, record_event_processed

__all__ = [
    "setup_logger",
    "log_event",
    "Timer",
    "record_event_processed",
]
