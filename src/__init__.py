"""
Real-Time Analytics Platform

Enterprise-grade real-time data streaming and analytics platform for 
processing high-volume event streams with sub-second latency and exactly-once semantics.
"""

__version__ = "0.1.0"
__author__ = "Manali Verma"

from src.quality.schema import Event, EventSchema
from src.quality.validators import DataValidator
from src.producers.event_producer import KafkaEventProducer

__all__ = [
    "Event",
    "EventSchema",
    "DataValidator",
    "KafkaEventProducer",
]
