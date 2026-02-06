# Design Decisions & Trade-offs

## Executive Summary

This document outlines key architectural decisions and their rationale.

---

## 1. Message Queue: Kafka vs. RabbitMQ vs. Pulsar

### Decision: **Apache Kafka**

| Aspect | Kafka | RabbitMQ | Pulsar |
|--------|-------|----------|--------|
| Throughput | 1M+ msg/s | 100K msg/s | 1M+ msg/s |
| Latency | 10-50ms | <10ms | 20-100ms |
| Persistence | Disk-based | Memory+disk | Disk-based |
| Replication | Built-in | Plugins | Built-in |
| Scalability | Horizontal | Vertical | Horizontal |
| Maturity | 10y+ | 15y+ | 5y+ |

### Why Kafka?

✅ **1M+ throughput**: Proven at hyperscale
✅ **Built-in replication**: No external dependencies
✅ **Topic partitioning**: Natural data parallelism
✅ **Excellent ecosystem**: Schema Registry, Kafka Streams, Connectors
✅ **Community**: Largest community + 1000s of tools
✅ **Used at Meta/Google**: Alignment with target companies

### Trade-offs Accepted

❌ **Slightly higher latency** than RabbitMQ (50ms vs <10ms)
❌ **More operational overhead** than RabbitMQ
❌ **Higher memory usage** for large clusters

### Why Not?

**RabbitMQ**: Limited to 100K msg/sec, not data streaming focused
**Pulsar**: Newer adoption risk, smaller community, steeper learning curve

---

## 2. Stream Processing: Flink vs. Spark vs. Kafka Streams

### Decision: **Apache Flink**

| Aspect | Flink | Spark | Kafka Streams |
|--------|-------|-------|---------------|
| Processing | Native streaming | Micro-batching | Native streaming |
| Latency | 10-100ms | 500ms-2s | 10-100ms |
| State Management | RocksDB | Memory | In-memory only |
| Exactly-once | Native | Native | With limitations |

### Why Flink?

✅ **Native streaming**: Not micro-batching like Spark
✅ **<100ms latency**: Spark's minimum 500ms unsuitable
✅ **Superior state**: RocksDB can hold 100GB+ per task
✅ **Complex processing**: Window operations, joins, pattern detection
✅ **Job management**: Long-running jobs (100+) with minimal overhead

### Trade-offs Accepted

❌ **Steeper learning curve** than Kafka Streams
❌ **More infrastructure** than Kafka Streams
❌ **Resource overhead** vs pure Kafka Streams

### Why Not?

**Spark Streaming**: Micro-batching unsuitable for <100ms requirement
**Kafka Streams**: Limited state (in-memory only), hard to scale beyond 100 topics

---

## 3. Data Warehouse: ClickHouse vs. Snowflake vs. BigQuery

### Decision: **ClickHouse (Open-Source)**

| Aspect | ClickHouse | Snowflake | BigQuery |
|--------|-----------|-----------|----------|
| Cost (1B rows) | ~$50/month | ~$2K/month | ~$1.5K/month |
| Control | Full | Limited | Limited |
| Vendor Lock-in | None | High | High |
| Query Speed | Sub-second | 1-3 seconds | 1-3 seconds |
| Compression | 10:1 | 8:1 | 10:1 |

### Why ClickHouse?

✅ **Cost-effective**: Open-source + cheap infrastructure
✅ **Sub-second queries**: Even on 1B+ rows
✅ **No vendor lock-in**: Full control, data portability
✅ **Time-series optimized**: Native DateTime support
✅ **Amazing compression**: 10:1 typical (exceptional)
✅ **Self-hosted**: No dependency on cloud provider

### Trade-offs Accepted

❌ **Operational overhead**: Must manage infrastructure
❌ **Less polished** UI than Snowflake
❌ **Smaller ecosystem** than Snowflake
❌ **Scaling complexity**: Vertical easier than horizontal

### Why Not?

**Snowflake**: $4/compute credit = $5K+/month minimum cost
**BigQuery**: Similar costs + data egress fees

### Hybrid Recommendation

```
Primary: ClickHouse (hot data 1-7 days)
Secondary: BigQuery (analytics 1-2 years)
Archive: S3 Glacier (90+ days)

Benefits:
✅ Cost optimization (tiered storage)
✅ Flexibility (can switch later)
✅ Compliance (data residency)
```

---

## 4. Caching Layer: Redis vs. Memcached vs. DynamoDB

### Decision: **Redis**

| Aspect | Redis | Memcached | DynamoDB |
|--------|-------|-----------|----------|
| Data Types | 5+ types | Strings only | Key-value only |
| Persistence | RDB + AOF | None | Auto (managed) |
| Pub/Sub | ✅ | ❌ | ❌ |
| Transactions | ✅ | ❌ | Limited |
| Cost | Low | Low | High ($300+/month) |

### Why Redis?

✅ **Rich data types**: Strings, lists, sets, sorted sets, hashes
✅ **Pub/Sub**: Built-in event publishing
✅ **Persistence**: RDB snapshots for durability
✅ **Transactions**: MULTI/EXEC for atomicity
✅ **Single-threaded**: Easy to reason about
✅ **Maturity**: Hyperscale-proven (billions of ops/day)

### Trade-offs Accepted

❌ **Memory limitation**: Primarily in-memory
❌ **Single-threaded**: Can be bottleneck (use pipelining)
❌ **Manual failover** vs managed services

### Why Not?

**Memcached**: No persistence, no pub/sub, only for ephemeral data
**DynamoDB**: Overkill for caching, AWS lock-in, high cost

---

## 5. State Backend: RocksDB vs. In-Memory vs. External

### Decision: **RocksDB**

| Aspect | RocksDB | In-Memory | External |
|--------|---------|-----------|----------|
| Size Limit | 100GB+ | 8GB RAM | Network I/O |
| Latency | 1-10ms | <1ms | 10-50ms |
| Durability | ✅ | ❌ | Depends |
| Cost | Low | Low | Moderate |
| Recovery | Fast | Medium | Medium |

### Why RocksDB?

✅ **Large state**: 100GB+ per task possible
✅ **Embedded**: No external dependency
✅ **Fast local access**: 1-10ms latency
✅ **Efficient memory**: LRU cache within RocksDB
✅ **Flink native**: First-class integration

### Trade-offs Accepted

❌ **Slightly slower** than in-memory
❌ **Disk I/O overhead** for hot paths
❌ **More complex debugging**

### Why Not?

**In-Memory**: Limited to 8GB, insufficient for user sessions
**External Redis**: Network latency, additional operational complexity

---

## 6. Serialization: JSON vs. Avro vs. Protobuf

### Decision: **JSON with Schema Registry**

| Aspect | JSON | Avro | Protobuf |
|--------|------|------|----------|
| Size | 1KB | 200B (20%) | 150B (15%) |
| Human Readable | ✅ | ❌ | ❌ |
| Schema Evolution | Good | Excellent | Excellent |
| Speed | Moderate | Fast | Fast |
| Debugging | Easy | Hard | Hard |

### Why JSON?

✅ **Human readable**: Easy debugging and monitoring
✅ **Industry standard**: Works everywhere
✅ **Good tooling**: JSON Schema validators
✅ **Easy integration**: No code generation
✅ **Browser native**: Can inspect in UI

### Size Mitigation

```
JSON (original): ~1KB
  ↓ Kafka compression (snappy)
  ↓
Compressed: ~100B (100:1 ratio with snappy!)

Result: Comparable to Avro after compression
```

### Trade-offs Accepted

❌ **Larger payload** (mitigated via compression)
❌ **Slower parsing** (modern JSON parsers fast enough)

---

## 7. Monitoring: Prometheus + Grafana vs. SaaS

### Decision: **Open-Source Stack**

| Aspect | Our Stack | Datadog | New Relic |
|--------|-----------|---------|-----------|
| Cost (1000 metrics) | ~$50/month | ~$300/month | ~$200/month |
| Vendor Lock-in | None | High | High |
| Data Retention | Unlimited | Limited | Limited |
| Flexibility | High | Medium | Medium |
| Ops Burden | Medium | Low | Low |

### Why Open-Source?

✅ **Cost**: 10x cheaper than SaaS
✅ **Control**: Full control over data and retention
✅ **Flexibility**: Customize as needed
✅ **Compliance**: On-premise option for data privacy

### Trade-offs Accepted

❌ **Ops burden**: Must manage infrastructure
❌ **Less polish**: Than commercial solutions
❌ **Smaller community**: Than Datadog

### Components

```
Prometheus: Metrics collection + time-series DB
Grafana: Visualization and dashboarding
Jaeger: Distributed tracing
ELK: Log aggregation
```

---

## 8. Deployment: Docker Compose vs. Kubernetes vs. EC2

### Decision: **Docker Compose (dev), Kubernetes (prod)**

**Development:**
```
Why Docker Compose?
✅ Easy setup (docker-compose up)
✅ No cluster management
✅ Reproduces prod locally
✅ Fast feedback loop
```

**Production:**
```
Why Kubernetes?
✅ Auto-scaling
✅ Self-healing
✅ Rolling updates
✅ Persistent storage
✅ Service discovery
✅ Resource quotas
```

### Why Not?

**EC2 directly**: Manual scaling, manual failures, complex orchestration

---

## 9. Event Partitioning: By user_id vs. By timestamp vs. Random

### Decision: **By user_id**

| Strategy | Ordering | Scalability | Debugging | Co-location |
|----------|----------|-------------|-----------|------------|
| user_id | ✅ per user | ✅ | ✅ | ✅ |
| timestamp | ✅ global | ✅ | ❌ | ❌ |
| random | ❌ | ✅ | ❌ | ❌ |

### Why user_id?

✅ **Maintains ordering**: Per-user event ordering
✅ **Co-locates events**: Same user on same partition
✅ **Stateful processing**: Flink state keyed by user_id
✅ **Debugging**: Track user journey easily
✅ **Skew handling**: Natural load balancing (many users)

### Trade-offs Accepted

❌ **Requires knowledge**: Must know partitioning key upfront
❌ **Potential skew**: If one user super active (unlikely)

---

## Summary Decision Matrix

| Component | Choice | Confidence | Risk |
|-----------|--------|-----------|------|
| Message Queue | Kafka | Very High | Low |
| Stream Processing | Flink | High | Low |
| Data Warehouse | ClickHouse | High | Medium (ops) |
| Cache | Redis | Very High | Low |
| State Backend | RocksDB | Very High | Low |
| Serialization | JSON | High | Low |
| Monitoring | Open-source | High | Medium (ops) |
| Deployment | K8s (prod) | Very High | Low |

---

## Future Reconsideration Points

1. **At 10M+ events/sec**: Consider Kafka + Flink on GCP Dataflow
2. **If cloud-native preferred**: Migrate to BigQuery + Dataflow
3. **For multi-region**: Add Kafka mirror maker + DynamoDB
4. **For higher reliability**: Add disaster recovery region
