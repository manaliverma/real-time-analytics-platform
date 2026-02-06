"""
Metrics collection and exposure for Prometheus monitoring.

Provides metrics for throughput, latency, errors, and custom business metrics.
"""

from prometheus_client import Counter, Histogram, Gauge
from typing import Dict, Optional
import time


# ============= THROUGHPUT METRICS =============

events_processed_total = Counter(
    'events_processed_total',
    'Total number of events processed',
    ['service', 'event_type', 'status']
)

events_ingested_total = Counter(
    'events_ingested_total',
    'Total number of events ingested from Kafka',
    ['topic', 'partition']
)

events_failed_total = Counter(
    'events_failed_total',
    'Total number of events that failed processing',
    ['service', 'error_type']
)


# ============= LATENCY METRICS =============

processing_latency_seconds = Histogram(
    'processing_latency_seconds',
    'Event processing latency in seconds',
    ['service', 'operation'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0)
)

kafka_lag_records = Gauge(
    'kafka_lag_records',
    'Kafka consumer lag in records',
    ['topic', 'partition', 'consumer_group']
)

watermark_delay_seconds = Histogram(
    'watermark_delay_seconds',
    'Watermark delay in seconds (Flink)',
    ['job_name', 'operator'],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0)
)


# ============= DATA QUALITY METRICS =============

validation_failures_total = Counter(
    'validation_failures_total',
    'Total validation failures',
    ['validator', 'failure_reason']
)

data_quality_score = Gauge(
    'data_quality_score',
    'Overall data quality score (0-100)',
    ['source', 'metric_type']
)

schema_violations_total = Counter(
    'schema_violations_total',
    'Total schema violations',
    ['schema_name', 'violation_type']
)


# ============= RESOURCE METRICS =============

memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    ['component']
)


# ============= BUSINESS METRICS =============

revenue_total_usd = Counter(
    'revenue_total_usd',
    'Total revenue in USD',
    ['currency', 'region']
)

active_users_gauge = Gauge(
    'active_users_gauge',
    'Number of active users',
    ['platform', 'region']
)

user_session_duration_seconds = Histogram(
    'user_session_duration_seconds',
    'User session duration in seconds',
    ['platform'],
    buckets=(10, 30, 60, 300, 900, 3600)
)


# ============= HELPER FUNCTIONS =============

class Timer:
    """Context manager for measuring operation latency."""
    
    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.histogram.labels(**self.labels).observe(duration)


def record_event_processed(
    service: str,
    event_type: str,
    status: str = "success",
    processing_time_seconds: Optional[float] = None
) -> None:
    """
    Record a processed event metric.
    
    Args:
        service: Service name (e.g., "flink_processor")
        event_type: Type of event (e.g., "purchase", "page_view")
        status: Status of processing ("success", "failed", "filtered")
        processing_time_seconds: Time taken to process
    """
    events_processed_total.labels(
        service=service,
        event_type=event_type,
        status=status
    ).inc()
    
    if processing_time_seconds:
        processing_latency_seconds.labels(
            service=service,
            operation="process_event"
        ).observe(processing_time_seconds)


def record_validation_failure(
    validator: str,
    failure_reason: str
) -> None:
    """
    Record a validation failure.
    
    Args:
        validator: Name of validator (e.g., "schema_validator")
        failure_reason: Reason for failure (e.g., "missing_field", "invalid_type")
    """
    validation_failures_total.labels(
        validator=validator,
        failure_reason=failure_reason
    ).inc()


def record_data_quality_score(
    source: str,
    metric_type: str,
    score: float
) -> None:
    """
    Record data quality score (0-100).
    
    Args:
        source: Data source
        metric_type: Type of metric (e.g., "completeness", "accuracy")
        score: Quality score (0-100)
    """
    data_quality_score.labels(
        source=source,
        metric_type=metric_type
    ).set(score)
