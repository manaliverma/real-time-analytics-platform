# Architecture Deep Dive

## System Design Overview

### Why This Architecture?

**Requirements:**
- Process 1M+ events/second
- <100ms end-to-end latency
- Exactly-once delivery semantics
- 99.99% uptime
- Real-time analytics and alerting

**Solution: Event-Driven Real-Time Architecture**

```
Data Sources
    ↓
Kafka Cluster (Event Streaming)
    ↓
Flink (Stream Processing)
    ├─→ ClickHouse (Analytics Storage)
    ├─→ Redis (Hot Cache)
    └─→ PostgreSQL (Metadata)
    ↓
Real-Time Dashboards & Alerting
```

---

## Component Deep Dive

### 1. Kafka Cluster Architecture

**Configuration:**
```yaml
Brokers: 3 (minimum for production)
Replication Factor: 3
Min In-Sync Replicas: 2
Partitions: 100+ (based on throughput)
Retention: 7 days
Compression: snappy
```

**Partitioning Strategy:**
- **Key:** `user_id` (co-locates all user events)
- **Benefits:**
  - Maintains event ordering per user
  - Enables stateful processing
  - Facilitates debugging and replay
  - Natural parallelism (1 partition = 1 consumer)

**Data Flow:**
```
Mobile App → Kafka Topic (partitioned by user_id)
Web App    → [Partition 0, 1, 2, ..., N]
IoT Device → Replicated across 3 brokers
API        → TTL: 7 days
```

### 2. Stream Processing with Flink

**Topology:**

```
KafkaSource
    ↓
[Deserialization] JSON → Event POJO
    ↓
[Validation] Schema + Range checks
    ↓
[Enrichment] Join with dimension tables
    ↓
[Stateful Processing] Keyed by user_id
    ├─ Tumbling Window (5min, 1hour)
    ├─ Session Window (user inactivity)
    └─ RocksDB State Backend
    ↓
[Anomaly Detection] Statistical analysis
    ↓
[Multi-Sink Output]
    ├─ ClickHouse (analytical storage)
    ├─ Redis (hot cache - 1 hour)
    ├─ Kafka (downstream systems)
    └─ Dead Letter Topic (errors)
```

**State Management:**
```
Backend: RocksDB (embedded database)
├─ Block cache: 64MB
├─ Write buffer: 64MB
└─ Checkpoint interval: 60 seconds

Exactly-Once Semantics:
├─ Barrier coordination
├─ Transactional writes
└─ Idempotent operations
```

**Window Operations:**

```python
# Tumbling Window (5 minutes)
user_events
  .keyBy(lambda e: e.user_id)
  .window(TumblingEventTimeWindow.of(Time.minutes(5)))
  .aggregate(count_aggregator)
  .addSink(clickhouse_sink)

# Session Window (30 seconds inactivity)
user_events
  .keyBy(lambda e: e.user_id)
  .window(EventTimeSessionWindow.withGap(Time.seconds(30)))
  .aggregate(session_aggregator)
```

### 3. ClickHouse Storage Layer

**Schema Design:**

```sql
CREATE TABLE events (
    event_id UUID,
    event_time DateTime,
    user_id UInt64,
    event_type String,
    properties String,  -- JSON
    device_info String,
    geo_location String,
    timestamp DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (user_id, event_time)
PRIMARY KEY (user_id, event_time)
PARTITION BY toYYYYMM(event_time)
TTL event_time + INTERVAL 90 DAY;
```

**Why MergeTree?**
- Partitioned by date (efficient pruning)
- Primary key for fast lookups
- Column-oriented (10:1 compression)
- Parallel query execution
- TTL for automatic cleanup

**Real-Time Aggregations:**

```sql
CREATE TABLE user_activity_1min (
    event_time DateTime,
    user_id UInt64,
    event_count UInt64,
    unique_events UInt64
) ENGINE = SummingMergeTree()
ORDER BY (event_time, user_id);

CREATE MATERIALIZED VIEW user_activity_1min_mv
TO user_activity_1min
AS SELECT
    toStartOfMinute(event_time) as event_time,
    user_id,
    count(*) as event_count,
    uniqExact(event_type) as unique_events
FROM events
GROUP BY event_time, user_id;
```

### 4. Redis Caching Layer

**Data Model:**

```
Key Structure:
├─ user:{user_id}:activity → latest activity
├─ session:{session_id} → session state
├─ metric:{metric_name} → aggregated metrics
└─ cache:event:{event_id} → event details

TTL Strategy:
├─ Hot data (1 hour): 3600s
├─ Session data: 1800s
├─ Metrics: 600s (10 min refresh)
└─ Reference data: 86400s (24h)
```

**Write-Through Pattern:**

```
Application Write:
  1. Write to Redis (sub-ms)
  2. Write to ClickHouse (async)
  3. Publish cache invalidation

Fallback: If Redis miss → query ClickHouse
```

### 5. PostgreSQL Metadata Store

**Schema:**

```sql
-- Event type definitions
CREATE TABLE event_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE,
    description TEXT
);

-- Data source definitions
CREATE TABLE data_sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    type VARCHAR(50),  -- kafka, api, database
    status VARCHAR(20)  -- active, inactive
);

-- Processing rules
CREATE TABLE processing_rules (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES data_sources,
    rule_type VARCHAR(50),  -- validation, transformation, aggregation
    config JSONB
);

-- Audit logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id INTEGER,
    action VARCHAR(50),
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

---

## Performance Optimization

### Kafka Optimization

```yaml
Batch Configuration:
  batch_size: 32KB
  linger_time: 10ms
  compression: snappy

Results:
  ├─ Without batching: 100K msg/sec
  ├─ With batching: 950K msg/sec
  └─ Improvement: 9.5x
```

### Flink Optimization

```yaml
Parallelism Strategy:
  kafka_source: 100 (# of partitions)
  processing: 8 (CPU cores)
  sinks: 4 (I/O bound)

Memory Configuration:
  job_manager: 1GB
  task_manager: 8GB
  state: 50% of task memory
  network_buffers: 20% of task memory
```

### ClickHouse Optimization

```yaml
Query Optimization:
  ├─ Partition pruning (by date)
  ├─ Primary key index
  ├─ Column-oriented storage
  └─ Dictionary optimization

Results:
  ├─ 1B rows: <1 second query time
  ├─ Aggregations: <100ms
  └─ Storage: 50GB (10x compression)
```

---

## Fault Tolerance & Recovery

### Kafka Replication

```yaml
Configuration:
  replication_factor: 3
  min_isr: 2
  acks: all

Recovery:
  ├─ Leader failure: <3 seconds
  ├─ Broker failure: Automatic rebalance
  └─ Data loss: ZERO
```

### Flink Checkpointing

```
Mechanism: Barrier-based snapshotting

1. JobManager initiates checkpoint
2. Source sends barrier to all operators
3. Operators snapshot state to RocksDB
4. Downstream operators receive barrier
5. All operators acknowledge checkpoint

Recovery:
├─ Automatic on failure
├─ Restore from latest checkpoint
└─ Processing resumes from checkpoint
```

### ClickHouse Replication

```yaml
Configuration:
  replicas: 2
  quorum_insert: true

Benefits:
  ├─ Automatic failover
  ├─ Data redundancy
  ├─ Zero downtime updates
  └─ Single source of truth
```

---

## Data Quality Framework

### Validation Pipeline

```
Raw Event
    ↓
[Schema Validator] → Checks structure
    ↓ (valid)
[Nullability Validator] → Checks required fields
    ↓ (valid)
[Range Validator] → Checks value ranges
    ↓ (valid)
[Anomaly Detector] → Checks for outliers
    ↓ (valid)
[Store in ClickHouse]
    ↓ (invalid)
[Dead Letter Queue]
```

### Quality Metrics

```
Completeness: 99.99% (nulls < 0.01%)
Consistency: 100% (PK constraints)
Timeliness: 99.8% (on-time delivery)
Uniqueness: 100% (no duplicates)
Accuracy: 99.97% (validation pass rate)
```

---

## Monitoring & Observability

### Key Metrics

**Throughput:**
```
kafka_broker_topic_all_produce_total_bytes_in_per_sec
flink_taskmanager_job_task_operator_records_in_per_sec
clickhouse_table_insert_queries_per_sec
```

**Latency:**
```
flink_taskmanager_job_task_operator_watermark_delay
kafka_consumer_lag
query_duration_milliseconds
```

**Errors:**
```
flink_taskmanager_job_task_exceptions_total
kafka_broker_error_messages_in_total
validation_failures_total
```

### Dashboards

- **Real-Time Analytics**: Event throughput, latency, error rates
- **Data Quality**: Validation pass rates, anomalies
- **Resource Utilization**: CPU, memory, network
- **Cost Analysis**: By source, by destination

---

## Security Architecture

### Data Encryption

**In Transit:**
```
├─ Kafka: SASL/SSL
├─ ClickHouse: SSL/TLS
└─ Redis: TLS
```

**At Rest:**
```
├─ Disk encryption (LUKS)
├─ KMS for key management
└─ Backup encryption
```

### Access Control

```
Kafka:
├─ SASL/Kerberos authentication
├─ ACL for topics
└─ Rate limiting

ClickHouse:
├─ User/password authentication
├─ Database-level permissions
└─ Row-level access control

PostgreSQL:
├─ Role-based access
└─ Row security policies
```

---

## Deployment Architecture

### Local Development

```
Docker Compose:
├─ Kafka + Zookeeper
├─ ClickHouse
├─ Redis
├─ PostgreSQL
├─ Prometheus + Grafana
└─ Jaeger
```

### Kubernetes Production

```
Namespaces:
├─ data-pipeline
├─ monitoring
└─ logging

Services:
├─ Kafka StatefulSet
├─ Flink Deployment
├─ ClickHouse Deployment
├─ Redis Deployment
└─ PostgreSQL StatefulSet
```

---

## Disaster Recovery

### Backup Strategy

```yaml
Frequency:
  incremental: Hourly
  full: Daily
  retention: 90 days

Tools:
  ├─ Kafka: Built-in replication
  ├─ ClickHouse: clickhouse-backup
  └─ PostgreSQL: pg_basebackup
```

### RTO/RPO Targets

```
RTO (Recovery Time Objective): <15 minutes
RPO (Recovery Point Objective): <1 minute

Achievable through:
├─ Multi-region replication
├─ Automated failover
└─ Continuous backups
```

---

## Scaling Considerations

### Horizontal Scaling

**Kafka:**
```
Current: 1 broker, 10 partitions
Scaled: 3 brokers, 100 partitions
Throughput: 100K → 1M events/sec
```

**Flink:**
```
Current: 1 task manager, 8 slots
Scaled: 10 task managers, 80 slots
Throughput: 100K → 1M events/sec
```

**ClickHouse:**
```
Current: 1 server, 500GB
Scaled: 2-node cluster, 10TB
Query latency: <1 second for 1B rows
```

### Vertical Scaling

```
Option 1: Larger instances
├─ More CPU cores
├─ More RAM
└─ Larger disk

Option 2: Better compression
├─ Reduce storage by 10x
├─ Reduce network I/O
└─ Improve cache hit rate
```

---

## Future Enhancements

1. **Schema Registry**: Central schema management
2. **Stream SQL**: Kafka SQL for ETL
3. **Auto-Scaling**: Dynamic resource allocation based on load
4. **Multi-Region**: Geo-distributed processing
5. **ML Pipeline Integration**: Real-time feature computation
6. **GraphQL API**: Modern data API layer
