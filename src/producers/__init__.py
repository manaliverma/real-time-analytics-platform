"""
Event producers for ingesting data into Kafka.

Provides realistic event generation and Kafka producer integration
for sending events to the real-time analytics platform.
"""

from src.producers.event_generator import RealisticEventGenerator
from src.producers.event_producer import KafkaEventProducer

__all__ = [
    "RealisticEventGenerator",
    "KafkaEventProducer",
]
