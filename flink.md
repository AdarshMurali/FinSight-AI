# FinSight AI — Flink Streaming Pipeline

---

## Setup & Run Guide (implemented 2026-06-18)

### Architecture

```
Windows Host
│
├── Python Producers (run in venv)
│   ├── finnhub_news_producer.py   ── polls Finnhub REST every 2 min ──► Kafka: market.news
│   └── finnhub_trade_producer.py  ── Finnhub WebSocket live trades ───► Kafka: market.trades
│
└── Docker (docker-compose-streaming.yml)
    ├── Zookeeper      :2181
    ├── Kafka          :9092
    ├── Kafka UI       :8080   ◄── http://localhost:8080
    ├── Flink JobManager :8082  ◄── http://localhost:8081 (internal) / http://localhost:8082 (host)
    └── Flink TaskManager
           ├── news_sentiment_job.py      ──► ChromaDB market_news
           └── volatility_detector_job.py ──► ChromaDB volatility_events
```

### Files

| File | Purpose |
|------|---------|
| `docker-compose-streaming.yml` | Docker stack (Zookeeper + Kafka + Kafka UI + Flink) |
| `backend/flink/Dockerfile` | Custom Flink image (Python 3 + Kafka JAR + pip deps) |
| `backend/flink/flink-sql-connector-kafka-3.1.0-1.18.jar` | Kafka connector (pre-downloaded, not in git) |
| `backend/flink/config.py` | Shared config (ports, topics, tickers, API keys) |
| `backend/flink/finnhub_news_producer.py` | Polls Finnhub news REST API → Kafka |
| `backend/flink/finnhub_trade_producer.py` | Finnhub WebSocket trades → Kafka |
| `backend/flink/news_sentiment_job.py` | PyFlink: Kafka → VADER sentiment → ChromaDB |
| `backend/flink/volatility_detector_job.py` | PyFlink: Kafka trades → 5-min window → ChromaDB |
| `backend/flink/requirements-flink.txt` | Producer deps for Windows venv |

### Ports

| Service | Host Port | Notes |
|---------|-----------|-------|
| Zookeeper | 2181 | Internal only |
| Kafka | 9092 | Used by Windows producers |
| Kafka UI | 8080 | Browser dashboard |
| Flink Web UI | 8082 | Host 8081 was taken; internal port stays 8081 |

---

## Step-by-Step: Start the Pipeline

### Step 1 — Start Docker stack

```powershell
# First time (builds custom Flink image — takes ~5 min)
docker compose -f docker-compose-streaming.yml up -d --build

# Subsequent starts (image already built — takes ~10 sec)
docker compose -f docker-compose-streaming.yml up -d
```

Verify all 5 containers are running:
```powershell
docker compose -f docker-compose-streaming.yml ps
```

Expected: `finsight-zookeeper`, `finsight-kafka`, `finsight-kafka-ui`, `finsight-flink-jobmanager`, `finsight-flink-taskmanager` — all `Up`.

Open browser and confirm:
- `http://localhost:8080` — Kafka UI shows cluster `finsight`
- `http://localhost:8082` — Flink UI shows 1 Task Manager, 4 slots available

### Step 2 — Install producer dependencies (once)

```powershell
.\finsightaivenv\Scripts\Activate.ps1
pip install kafka-python==2.0.2 websocket-client==1.8.0
```

### Step 3 — Start a news producer (keep terminal open)

```powershell
.\finsightaivenv\Scripts\Activate.ps1
cd backend\flink
python finnhub_news_producer.py
```

Polls Finnhub REST API every 2 minutes for all 50 tickers. New articles appear in Kafka UI under **Topics → market.news**.

Or for real-time trade data (WebSocket):
```powershell
python finnhub_trade_producer.py
```

### Step 4 — Submit Flink job (separate terminal)

**Use case 1: News + VADER sentiment → ChromaDB market_news**
```powershell
docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/news_sentiment_job.py
```

**Use case 2: Volatility detector → ChromaDB volatility_events**
```powershell
docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/volatility_detector_job.py
```

Monitor running jobs at `http://localhost:8082` → Jobs → Running Jobs.

---

## Stop & Restart

```powershell
# Stop all containers (volumes preserved)
docker compose -f docker-compose-streaming.yml down

# Stop and wipe all volumes (clean slate)
docker compose -f docker-compose-streaming.yml down -v

# Restart without rebuild
docker compose -f docker-compose-streaming.yml up -d
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Port 8081 already in use | Flink UI is mapped to 8082 on host — use `http://localhost:8082` |
| Kafka connector JAR missing | Download from `search.maven.org` → `flink-sql-connector-kafka 3.1.0-1.18` → copy to `backend/flink/` |
| `wget` fails in Docker build | JAR is pre-downloaded and copied via `COPY` in Dockerfile — no network needed at build time |
| Producer can't connect to Kafka | Ensure Docker stack is running (`docker compose ps`), producers connect via `localhost:9092` |
| Flink job can't reach ChromaDB | ChromaDB is on host; Flink jobs reach it via `host.docker.internal:8001` (set in `config.py`) |

---

## Original Task 2.3 Requirements

Goal: Set up real-time streaming for market data and events

Flink Jobs to Create:

1. Market Data Ingestion Job
  - Stream price updates from market data sources
  - Calculate real-time position values
  - Update portfolio metrics continuously
2. Event Stream Processing Job
  - Ingest news/events from external sources (APIs, feeds)
  - Classify and tag events by type (policy, geopolitical, sectoral)
  - Trigger impact analysis on affected portfolios
3. Anomaly Detection Job
  - Detect unusual position changes (significant weight shifts)
  - Alert on threshold breaches (concentration limits, volatility spikes)
  - Identify correlation breaks between securities

Required Deliverables:

- Flink job definitions (Python PyFlink or Java/Scala)
- Stream processing pipeline configuration
- Kafka or RabbitMQ integration (for message queuing)
- Docker setup for Flink (JobManager + TaskManager)

Infrastructure Components Needed:

- Apache Flink cluster (JobManager + TaskManager)
- Message Broker (Kafka or RabbitMQ) for event streaming
- Connectors to SQL Server for reading/writing processed data

Since you already have SQL Server running in Docker, the pending tasks would be:
1. Add Flink services to your Docker Compose
2. Set up Kafka (or start with RabbitMQ if preferred)
3. Create the Flink job definitions for the three jobs above
4. Configure connectors to read from SQL Server and stream updates
