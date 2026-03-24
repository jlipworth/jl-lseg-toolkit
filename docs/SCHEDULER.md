# Scheduler Documentation

The scheduler is a long-running daemon that automatically extracts LSEG timeseries data on configurable schedules.

## Quick Start

```bash
# Set up database credentials (via Infisical or env vars)
export POSTGRES_HOST=timescaledb.example.com
export POSTGRES_PORT=5433
export POSTGRES_USER=timescale
export POSTGRES_PASSWORD=xxx
export POSTGRES_DB=jlfinance

# Add a job
lseg-scheduler add-job \
  --name benchmark_daily \
  --group benchmark_fixings \
  --granularity daily \
  --cron "0 18 * * 1-5"

# Run manually to test
lseg-scheduler run benchmark_daily

# Start the daemon
lseg-scheduler start --foreground
```

## CLI Commands

### Job Management

```bash
# List available instrument groups
lseg-scheduler groups

# Add a new job
lseg-scheduler add-job \
  --name <name> \
  --group <instrument_group> \
  --granularity <daily|hourly|5min> \
  --cron "<cron_expression>" \
  [--priority <1-100>] \
  [--lookback <days>]

# List jobs
lseg-scheduler jobs [--all]

# Enable/disable jobs
lseg-scheduler enable <job_name>
lseg-scheduler disable <job_name>

# Delete a job
lseg-scheduler delete-job <job_name> [--force]

# Run a job manually
lseg-scheduler run <job_name>
```

### Monitoring

```bash
# Show daemon status
lseg-scheduler status

# Show extraction state for instruments
lseg-scheduler state [--job <name>] [--failed]

# Show job run history
lseg-scheduler history [--job <name>] [--limit <n>]

# Reset failure count for an instrument
lseg-scheduler reset --job <name> --symbol <symbol>
```

### Daemon Control

```bash
# Start daemon (foreground)
lseg-scheduler start --foreground

# Start daemon (background - requires systemd/supervisor)
lseg-scheduler start
```

## Instrument Groups

| Group | Count | Data Shape | Description |
|-------|-------|------------|-------------|
| `benchmark_fixings` | 4 | fixing | SOFR, ESTR, SARON, CORRA |
| `euribor_fixings` | 4 | fixing | EURIBOR tenors |
| `fx_spot` | 11 | quote | Major FX pairs |
| `treasury_futures` | 8 | ohlcv | US Treasury futures |
| `european_bond_futures` | 5 | ohlcv | Bund, BTP, OAT, etc. |
| `index_futures` | 25 | ohlcv | ES, NQ, YM, etc. |
| `commodity_futures` | 24 | ohlcv | CL, GC, NG, etc. |
| `ois_usd` | 23 | rate | USD OIS curve |
| `ois_eur` | 23 | rate | EUR OIS curve |
| `ois_gbp` | 14 | rate | GBP OIS curve |
| `irs_usd` | 10 | rate | USD IRS curve |
| `irs_eur` | 17 | rate | EUR IRS curve |
| `ust_yields` | 13 | bond | US Treasury yields |
| `de_yields` | 18 | bond | German Bund yields |
| `equity_indices` | 33 | ohlcv | SPX, DJI, etc. |
| `volatility_indices` | 8 | ohlcv | VIX, VSTOXX, etc. |

See full list with `lseg-scheduler groups`.

## Configuration

### Environment Variables

Database connection (TSDB_* or POSTGRES_*):
```bash
TSDB_HOST / POSTGRES_HOST      # Database host
TSDB_PORT / POSTGRES_PORT      # Database port (default: 5432)
TSDB_DATABASE / POSTGRES_DB    # Database name
TSDB_USER / POSTGRES_USER      # Database user
TSDB_PASSWORD / POSTGRES_PASSWORD  # Database password
```

Scheduler settings:
```bash
SCHEDULER_MAX_WORKERS          # Max concurrent extractions (default: 4)
SCHEDULER_RATE_LIMIT           # Delay between API calls (default: 0.05s)
SCHEDULER_MAX_RICS_PER_BATCH   # Max RICs per API call (default: 100)
SCHEDULER_INTRADAY_RETENTION   # Days to keep intraday data (default: 90)
```

### Using Infisical

If you use Infisical or another secret manager, inject your own
TimescaleDB/PostgreSQL credentials into the shell before running scheduler
commands. Keep the workflow environment-driven via `TSDB_*` or `POSTGRES_*`
rather than hardcoding a repo-specific secret path in shared docs.

```bash
# Start a shell with your own secret-manager configuration
infisical run ... -- bash

# Or prefix a single command
infisical run ... -- lseg-scheduler status
```

## Cron Schedule Examples

| Schedule | Cron Expression |
|----------|-----------------|
| Weekdays 6 PM ET | `0 18 * * 1-5` |
| Every hour | `0 * * * *` |
| Every 5 minutes | `*/5 * * * *` |
| Daily at midnight | `0 0 * * *` |
| Sunday 10 PM | `0 22 * * 0` |

## Database Schema

The scheduler uses three tables:

### scheduler_jobs
```sql
id              SERIAL PRIMARY KEY
name            TEXT UNIQUE NOT NULL
instrument_group TEXT NOT NULL
granularity     TEXT NOT NULL
schedule_cron   TEXT NOT NULL
priority        INTEGER DEFAULT 50
enabled         BOOLEAN DEFAULT TRUE
lookback_days   INTEGER DEFAULT 5
max_chunk_days  INTEGER DEFAULT 30
```

### scheduler_state
```sql
id              SERIAL PRIMARY KEY
job_id          INTEGER REFERENCES scheduler_jobs(id)
instrument_id   INTEGER REFERENCES instruments(id)
last_success_date DATE
consecutive_failures INTEGER DEFAULT 0
error_message   TEXT
UNIQUE (job_id, instrument_id)
```

### scheduler_runs
```sql
id              SERIAL PRIMARY KEY
job_id          INTEGER REFERENCES scheduler_jobs(id)
started_at      TIMESTAMPTZ
completed_at    TIMESTAMPTZ
status          TEXT  -- 'running', 'completed', 'failed', 'partial'
instruments_success INTEGER
instruments_failed INTEGER
rows_extracted  INTEGER
error_summary   TEXT
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   APScheduler   │────▶│  ExtractionJob  │────▶│   LSEGClient    │
│     Daemon      │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ scheduler_jobs  │     │ scheduler_state │     │   LSEG API      │
│ scheduler_runs  │     │ instruments     │     │   (Workspace)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  TimescaleDB    │
                        │  Hypertables    │
                        └─────────────────┘
```

### Flow

1. **Daemon startup**: Loads jobs from `scheduler_jobs`, schedules with APScheduler
2. **Job trigger**: APScheduler fires job at cron time
3. **Universe build**: Maps instrument group to list of RICs
4. **Gap detection**: Uses `detect_gaps()` to find missing data
5. **Extraction**: Fetches data from LSEG API in chunks
6. **Storage**: Saves to appropriate hypertable (ohlcv, quote, rate, etc.)
7. **State update**: Records success/failure in `scheduler_state`

### Failure Handling

- Exponential backoff on failures (base 60s, max 3600s)
- Per-instrument failure tracking (doesn't block other instruments)
- Zombie run cleanup on daemon restart
- Graceful shutdown on SIGTERM/SIGINT

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/lseg-scheduler.service`:
```ini
[Unit]
Description=LSEG Data Extraction Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=lseg
WorkingDirectory=/opt/lseg-toolkit
Environment=POSTGRES_HOST=timescaledb.example.com
Environment=POSTGRES_PORT=5433
Environment=POSTGRES_USER=timescale
Environment=POSTGRES_PASSWORD=xxx
Environment=POSTGRES_DB=jlfinance
ExecStart=/opt/lseg-toolkit/.venv/bin/lseg-scheduler start --foreground
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable lseg-scheduler
sudo systemctl start lseg-scheduler
```

### Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install uv && uv sync

ENV POSTGRES_HOST=timescaledb
ENV POSTGRES_PORT=5432
ENV POSTGRES_USER=timescale
ENV POSTGRES_DB=jlfinance

CMD ["uv", "run", "lseg-scheduler", "start", "--foreground"]
```

## Troubleshooting

### Job not running

1. Check job is enabled: `lseg-scheduler jobs`
2. Verify cron expression: Use https://crontab.guru
3. Check daemon status: `lseg-scheduler status`

### Extraction failures

1. Check state: `lseg-scheduler state --failed`
2. Look at error messages in state output
3. Reset failed instruments: `lseg-scheduler reset --job <name> --symbol <symbol>`

### Database connection issues

1. Verify env vars are set: `echo $POSTGRES_HOST`
2. Test connection: `psql "postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB"`
3. Check TimescaleDB is running and accessible

### LSEG session issues

1. Ensure LSEG Workspace is running on localhost:9000
2. Check session can be opened manually
3. Daemon will auto-reconnect on session drops
