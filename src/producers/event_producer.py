"""
Kafka event producer with error handling, metrics, and schema validation.

Sends events to Kafka with configurable throughput, batch settings,
and comprehensive error handling and monitoring.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from kafka import KafkaProducer
from kafka.errors import KafkaError

from src.quality.schema import Event, EventSchema
from src.utils.metrics import record_event_processed

logger = logging.getLogger(__name__)


@dataclass
class ProducerMetrics:
    """Metrics for producer performance."""
    events_sent: int = 0
    events_failed: int = 0
    schema_validation_failures: int = 0
    total_bytes_sent: int = 0
    total_time_ms: float = 0.0
    
    @property
    def events_per_second(self) -> float:
        """Calculate throughput."""
        if self.total_time_ms == 0:
            return 0
        return (self.events_sent / self.total_time_ms) * 1000
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.events_sent == 0:
            return 0
        return self.total_time_ms / self.events_sent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'events_sent': self.events_sent,
            'events_failed': self.events_failed,
            'schema_validation_failures': self.schema_validation_failures,
            'total_bytes_sent': self.total_bytes_sent,
            'events_per_second': round(self.events_per_second, 2),
            'avg_latency_ms': round(self.avg_latency_ms, 2),
        }


class KafkaEventProducer:
    """
    Production-grade Kafka producer for events.
    
    Features:
    - Schema validation before sending
    - Automatic retries with backoff
    - Metrics collection
    - Error handling with dead letter queue
    - Configurable batching and compression
    """
    
    def __init__(
        self,
        brokers: str = 'localhost:9092',
        topic: str = 'user_events',
        batch_size_kb: int = 32,
        linger_ms: int = 10,
        compression: str = 'snappy',
        max_retries: int = 3,
        validate_schema: bool = True,
    ):
        """
        Initialize Kafka producer.
        
        Args:
            brokers: Comma-separated Kafka brokers
            topic: Target topic
            batch_size_kb: Batch size in KB
            linger_ms: Wait time before sending batch
            compression: Compression type (snappy, gzip, lz4, zstd)
            max_retries: Number of retries on failure
            validate_schema: Whether to validate schema before sending
        """
        self.topic = topic
        self.dead_letter_topic = f"{topic}_dlq"
        self.validate_schema = validate_schema
        self.metrics = ProducerMetrics()
        self.start_time = time.time()
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=brokers.split(','),
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else v,
                key_serializer=lambda k: k.encode('utf-8') if isinstance(k, str) else k,
                acks='all',  # Wait for all in-sync replicas
                batch_size=batch_size_kb * 1024,
                linger_ms=linger_ms,
                compression_type=compression,
                request_timeout_ms=30000,
                retries=max_retries,
                max_in_flight_requests_per_connection=5,
            )
            logger.info(
                f"Kafka producer initialized: "
                f"brokers={brokers}, topic={topic}, "
                f"compression={compression}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _on_send_success(self, record_metadata) -> None:
        """Callback for successful send."""
        logger.debug(
            f"Event sent to {record_metadata.topic} "
            f"[partition={record_metadata.partition}, "
            f"offset={record_metadata.offset}]"
        )
    
    def _on_send_error(self, exc) -> None:
        """Callback for send error."""
        logger.error(f"Error sending event: {exc}")
        self.metrics.events_failed += 1
    
    def send_event(
        self,
        event: Event,
        timeout_sec: float = 10.0,
    ) -> bool:
        """
        Send a single event to Kafka.
        
        Args:
            event: Event to send
            timeout_sec: Timeout for send operation
        
        Returns:
            True if sent successfully, False otherwise
        """
        # Validate schema
        if self.validate_schema:
            event_dict = event.to_dict()
            is_valid, error_msg = EventSchema.validate(event_dict)
            if not is_valid:
                logger.error(
                    f"Schema validation failed for event {event.event_id}: "
                    f"{error_msg}"
                )
                self.metrics.schema_validation_failures += 1
                return False
        
        # Send to Kafka
        try:
            event_json = event.to_json()
            future = self.producer.send(
                self.topic,
                value=event_json,
                key=str(event.user_id),  # Partition by user_id
            )
            
            # Add callbacks
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)
            
            # Wait for send to complete
            record_metadata = future.get(timeout=timeout_sec)
            
            self.metrics.events_sent += 1
            self.metrics.total_bytes_sent += len(event_json.encode('utf-8'))
            
            # Record metrics
            record_event_processed(
                service="kafka_producer",
                event_type=event.event_type,
                status="success"
            )
            
            # Log progress every 10K events
            if self.metrics.events_sent % 10000 == 0:
                logger.info(
                    f"Sent {self.metrics.events_sent} events. "
                    f"Metrics: {self.metrics.to_dict()}"
                )
            
            return True
            
        except KafkaError as e:
            logger.error(f"Kafka error sending event {event.event_id}: {e}")
            self.metrics.events_failed += 1
            record_event_processed(
                service="kafka_producer",
                event_type=event.event_type,
                status="failed"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending event {event.event_id}: {e}")
            self.metrics.events_failed += 1
            return False
    
    def send_batch(
        self,
        events: List[Event],
        timeout_sec: float = 30.0,
    ) -> int:
        """
        Send batch of events to Kafka.
        
        Args:
            events: List of events to send
            timeout_sec: Timeout for batch operation
        
        Returns:
            Number of events successfully sent
        """
        successful = 0
        
        for event in events:
            if self.send_event(event, timeout_sec):
                successful += 1
        
        # Flush pending messages
        try:
            self.producer.flush(timeout=timeout_sec)
        except Exception as e:
            logger.error(f"Error flushing producer: {e}")
        
        return successful
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        elapsed = time.time() - self.start_time
        return {
            **self.metrics.to_dict(),
            'elapsed_seconds': round(elapsed, 2),
            'success_rate': round(
                (self.metrics.events_sent / 
                 (self.metrics.events_sent + self.metrics.events_failed) * 100)
                if (self.metrics.events_sent + self.metrics.events_failed) > 0 else 0,
                2
            ),
        }
    
    def close(self) -> None:
        """Close producer connection gracefully."""
        try:
            self.producer.close(timeout=30)
            logger.info(
                f"Producer closed. Final metrics: {self.get_metrics()}"
            )
        except Exception as e:
            logger.error(f"Error closing producer: {e}")


class BatchProducer:
    """
    High-throughput batch producer for load testing.
    
    Optimized for maximum throughput by batching and buffering.
    """
    
    def __init__(
        self,
        producer: KafkaEventProducer,
        batch_size: int = 1000,
    ):
        self.producer = producer
        self.batch_size = batch_size
        self.buffer: List[Event] = []
    
    def add_event(self, event: Event) -> None:
        """Add event to buffer."""
        self.buffer.append(event)
        
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self) -> int:
        """Flush buffered events."""
        if not self.buffer:
            return 0
        
        count = self.producer.send_batch(self.buffer)
        self.buffer = []
        return count
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.producer.close()
