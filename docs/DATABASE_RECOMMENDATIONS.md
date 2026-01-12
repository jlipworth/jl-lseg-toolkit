# Database Recommendations for Multi-Machine Analytics

This document evaluates database options for storing timeseries market data and backtest results, with multi-machine access from both Python and C++.

## Requirements Summary

| Requirement | Priority |
|-------------|----------|
| Multi-machine read/write access | High |
| Complex JOINs (timeseries + backtest results) | High |
| Python client support | High |
| C++ client support (read + write) | High |
| Query flexibility / ad-hoc analysis | High |
| Operational simplicity | Medium |
| Raw query speed | Medium |

**Data scale**: ~20M rows timeseries (100 instruments × 20 years × 10-min ticks) + backtest results

---

## Comparison Matrix

| Feature | TimescaleDB | QuestDB | ClickHouse | DuckDB + Storage |
|---------|-------------|---------|------------|------------------|
| **Complex JOINs** | Excellent | Good (v9.1+) | Requires denorm | Excellent |
| **C++ Client** | libpq (mature) | Native client | Native client | Native client |
| **Python Client** | psycopg/SQLAlchemy | Native + PGWire | clickhouse-driver | Native |
| **Multi-writer** | Yes (ACID) | Yes | Yes | Limited |
| **K8s Deployment** | Helm + CNPG | Helm | Altinity Operator | N/A (embedded) |
| **Ops Complexity** | Medium | Low | High | Low |
| **Timeseries Features** | Hypertables, compression | ASOF JOIN, SAMPLE BY | MergeTree, TTL | Window functions |
| **Maturity** | High | Medium | High | High (embedded) |

---

## Option 1: TimescaleDB (Recommended)

**Best for**: Complex joins, PostgreSQL ecosystem, flexibility

TimescaleDB extends PostgreSQL with timeseries optimizations while retaining full SQL support. It excels at joining timeseries data with relational tables.

### Pros
- Full PostgreSQL JOIN semantics - no denormalization required
- Mature C++ support via libpq (battle-tested)
- Hypertables with automatic partitioning by time
- Continuous aggregates for rollups
- Compression (90%+ typical)
- Strong ecosystem (pgAdmin, Grafana, etc.)

### Cons
- Requires block storage (not SMB) for good performance
- Higher memory usage than columnar DBs for large scans
- PostgreSQL complexity for tuning

### K8s Deployment

**Option A: CloudNativePG Operator (Recommended)**
```bash
# Install CNPG operator
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm upgrade --install cnpg \
  --namespace cnpg-system \
  --create-namespace \
  cnpg/cloudnative-pg

# Create TimescaleDB cluster (see manifest below)
kubectl apply -f timescaledb-cluster.yaml
```

```yaml
# timescaledb-cluster.yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: timescaledb
spec:
  instances: 1  # Start with 1 for dev, 3 for HA
  imageName: timescale/timescaledb-ha:pg16
  storage:
    size: 50Gi
    storageClass: longhorn  # Your NVMe-backed storage class
  postgresql:
    parameters:
      shared_preload_libraries: timescaledb
      timescaledb.telemetry_level: "off"
      max_connections: "100"
      shared_buffers: "256MB"
      work_mem: "64MB"
```

**Option B: Official Helm Chart**
```bash
helm repo add timescale https://charts.timescale.com
helm install timescaledb timescale/timescaledb-single \
  --set persistentVolumes.data.storageClass=longhorn \
  --set persistentVolumes.data.size=50Gi
```

### Client Examples

**Python**:
```python
import psycopg2
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@timescaledb:5432/markets")
df = pd.read_sql("""
    SELECT t.*, b.pnl, b.sharpe
    FROM timeseries t
    JOIN backtest_results b ON t.instrument = b.instrument
    WHERE t.timestamp BETWEEN '2020-01-01' AND '2024-01-01'
""", engine)
```

**C++**:
```cpp
#include <libpq-fe.h>

PGconn* conn = PQconnectdb("host=timescaledb dbname=markets user=...");
PGresult* res = PQexec(conn, "SELECT * FROM timeseries WHERE instrument = 'AAPL'");
// Process results...
PQclear(res);
PQfinish(conn);
```

---

## Option 2: QuestDB

**Best for**: Timeseries-first workloads, simplicity, ASOF JOINs

QuestDB is purpose-built for timeseries with excellent ingestion performance and time-aware SQL extensions.

### Pros
- Native C++ client with high-throughput ILP ingestion
- ASOF JOIN for point-in-time queries (perfect for backtesting)
- Automatic table creation, schema evolution
- Very fast ingestion (millions of rows/second)
- Simple operations - single binary
- Full JOIN support as of v9.1

### Cons
- Smaller ecosystem than PostgreSQL
- Less mature than TimescaleDB for complex relational queries
- No Kubernetes operator (Helm only)

### K8s Deployment

```yaml
# questdb-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: questdb
spec:
  serviceName: questdb
  replicas: 1
  selector:
    matchLabels:
      app: questdb
  template:
    metadata:
      labels:
        app: questdb
    spec:
      containers:
      - name: questdb
        image: questdb/questdb:9.2.1
        ports:
        - containerPort: 9000  # Web console + REST
        - containerPort: 8812  # PostgreSQL wire protocol
        - containerPort: 9009  # ILP ingestion
        volumeMounts:
        - name: data
          mountPath: /var/lib/questdb
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "4"
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: longhorn
      resources:
        requests:
          storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: questdb
spec:
  selector:
    app: questdb
  ports:
  - name: http
    port: 9000
  - name: pgwire
    port: 8812
  - name: ilp
    port: 9009
```

### Client Examples

**Python**:
```python
from questdb.ingress import Sender, TimestampNanos
import psycopg2  # For queries via PGWire

# High-speed ingestion via ILP
with Sender('questdb', 9009) as sender:
    sender.row('timeseries',
        symbols={'instrument': 'AAPL'},
        columns={'open': 150.0, 'high': 152.0, 'low': 149.0, 'close': 151.0},
        at=TimestampNanos.now())
    sender.flush()

# Query via PostgreSQL wire protocol
conn = psycopg2.connect("host=questdb port=8812 dbname=qdb")
df = pd.read_sql("""
    SELECT * FROM timeseries
    ASOF JOIN backtest_signals ON (instrument)
    WHERE timestamp > '2020-01-01'
""", conn)
```

**C++**:
```cpp
#include <questdb/ilp/line_sender.hpp>

// Ingestion
auto sender = questdb::ilp::line_sender::from_conf("http::addr=questdb:9009;");
sender.table("timeseries")
    .symbol("instrument", "AAPL")
    .column("close", 151.0)
    .at(questdb::ilp::timestamp_nanos::now());
sender.flush();

// Query via libpq (PGWire compatible)
PGconn* conn = PQconnectdb("host=questdb port=8812 dbname=qdb");
```

---

## Option 3: ClickHouse

**Best for**: Maximum analytical query speed, large-scale aggregations

ClickHouse is the fastest columnar database for OLAP workloads but requires denormalized schemas for optimal performance.

### Pros
- Extremely fast analytical queries (billions of rows in milliseconds)
- Native C++ (it's written in C++)
- Excellent compression
- Mature K8s operator (Altinity)
- Strong community

### Cons
- JOINs require careful optimization or denormalization
- Higher operational complexity
- Requires pre-joining data for best performance
- More tuning required

### K8s Deployment

```bash
# Install Altinity ClickHouse Operator
kubectl apply -f https://raw.githubusercontent.com/Altinity/clickhouse-operator/master/deploy/operator/clickhouse-operator-install-bundle.yaml

# Deploy ClickHouse cluster
kubectl apply -f clickhouse-cluster.yaml
```

```yaml
# clickhouse-cluster.yaml
apiVersion: clickhouse.altinity.com/v1
kind: ClickHouseInstallation
metadata:
  name: markets
spec:
  configuration:
    clusters:
    - name: markets
      layout:
        shardsCount: 1
        replicasCount: 1  # Increase for HA
  defaults:
    templates:
      dataVolumeClaimTemplate: data-volume
  templates:
    volumeClaimTemplates:
    - name: data-volume
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: longhorn
        resources:
          requests:
            storage: 50Gi
```

### Data Modeling Strategy

For complex joins, denormalize at write time:

```sql
-- Instead of joining at query time, create a materialized view
CREATE MATERIALIZED VIEW timeseries_with_backtest
ENGINE = MergeTree()
ORDER BY (instrument, timestamp)
AS SELECT
    t.*,
    b.strategy_id,
    b.pnl,
    b.sharpe
FROM timeseries t
LEFT JOIN backtest_results b ON t.instrument = b.instrument
    AND t.timestamp BETWEEN b.start_time AND b.end_time;
```

Or use dictionaries for dimension lookups:

```sql
CREATE DICTIONARY instrument_meta (
    instrument String,
    sector String,
    currency String
)
PRIMARY KEY instrument
SOURCE(POSTGRESQL(...))
LAYOUT(HASHED());

SELECT *, dictGet('instrument_meta', 'sector', instrument) as sector
FROM timeseries;
```

### Client Examples

**Python**:
```python
import clickhouse_connect

client = clickhouse_connect.get_client(host='clickhouse', port=8123)
df = client.query_df("""
    SELECT * FROM timeseries_with_backtest
    WHERE instrument = 'AAPL' AND timestamp > '2020-01-01'
""")
```

**C++**:
```cpp
#include <clickhouse/client.h>

clickhouse::Client client(clickhouse::ClientOptions()
    .SetHost("clickhouse")
    .SetPort(9000));

client.Select("SELECT * FROM timeseries WHERE instrument = 'AAPL'",
    [](const clickhouse::Block& block) {
        for (size_t i = 0; i < block.GetRowCount(); ++i) {
            // Process rows
        }
    });
```

---

## Option 4: DuckDB + Shared Storage (Not Recommended for Multi-Writer)

**Best for**: Single-writer scenarios, embedded analytics

DuckDB excels at complex analytical queries but lacks native multi-writer support.

### Limitations
- Single writer process only
- No built-in server mode
- Requires coordination layer for multi-machine writes (Delta Lake, etc.)

### When It Makes Sense
- Python does all writes, C++ only reads Parquet files
- You add a coordination service (but then why not use a real DB?)

---

## Recommendation

### Primary: TimescaleDB

For your requirements (flexibility, complex joins, C++ read/write), **TimescaleDB** is the best fit:

1. **Complex JOINs work naturally** - No need to denormalize or restructure data
2. **Mature C++ support** - libpq is battle-tested, widely used
3. **Good K8s story** - CNPG operator or official Helm charts
4. **PostgreSQL ecosystem** - Tools, monitoring, backups all work
5. **Reasonable performance** - Fast enough for your data scale (~20M rows)

### Alternative: QuestDB

Consider QuestDB if:
- ASOF JOINs are central to your analysis workflow
- You want simpler operations (single binary)
- Ingestion speed is a priority

### When to Consider ClickHouse

Choose ClickHouse if:
- You find TimescaleDB too slow for aggregations
- You're willing to denormalize data for performance
- Your queries are mostly pre-defined (not ad-hoc)

---

## Deployment Checklist

### For TimescaleDB on Longhorn

1. **Create Longhorn storage class** (if not exists):
   ```yaml
   apiVersion: storage.k8s.io/v1
   kind: StorageClass
   metadata:
     name: longhorn
   provisioner: driver.longhorn.io
   parameters:
     numberOfReplicas: "2"
     staleReplicaTimeout: "30"
   ```

2. **Install CNPG operator**

3. **Deploy TimescaleDB cluster**

4. **Create databases and hypertables**:
   ```sql
   CREATE DATABASE markets;
   \c markets
   CREATE EXTENSION IF NOT EXISTS timescaledb;

   CREATE TABLE timeseries (
       timestamp TIMESTAMPTZ NOT NULL,
       instrument TEXT NOT NULL,
       open DOUBLE PRECISION,
       high DOUBLE PRECISION,
       low DOUBLE PRECISION,
       close DOUBLE PRECISION,
       volume BIGINT
   );

   SELECT create_hypertable('timeseries', 'timestamp');
   CREATE INDEX ON timeseries (instrument, timestamp DESC);

   -- Enable compression
   ALTER TABLE timeseries SET (
       timescaledb.compress,
       timescaledb.compress_segmentby = 'instrument'
   );
   SELECT add_compression_policy('timeseries', INTERVAL '7 days');
   ```

5. **Configure connection pooling** (optional but recommended):
   ```bash
   helm install pgbouncer bitnami/pgbouncer \
     --set postgresql.host=timescaledb-rw \
     --set postgresql.port=5432
   ```

---

## References

- [ClickHouse C++ Client](https://github.com/ClickHouse/clickhouse-cpp)
- [Altinity ClickHouse Operator](https://github.com/Altinity/clickhouse-operator)
- [ClickHouse JOIN Best Practices](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)
- [QuestDB C++ Client](https://questdb.com/docs/ingestion/clients/c-and-cpp/)
- [QuestDB JOIN Documentation](https://questdb.com/docs/reference/sql/join/)
- [TimescaleDB Helm Charts](https://github.com/timescale/helm-charts)
- [CloudNativePG Operator](https://cloudnative-pg.io/)
- [TimescaleDB vs ClickHouse Comparison](https://www.tinybird.co/blog/clickhouse-vs-timescaledb)
- [DuckDB Concurrency](https://duckdb.org/docs/stable/connect/concurrency)
