# FinSight AI — Startup Guide

After every system restart, follow these steps **in order**. Each service depends on the ones above it.

---

## Step 0 — Prerequisites

Ensure **Docker Desktop** is running before anything else.  
Check the system tray — the Docker icon should be solid (not spinning).

---

## Step 1 — SQL Server

SQL Server must come up first because the FastAPI backend connects to it on startup.

### Start (if container already exists)
```powershell
docker start sqlserver1
```

### Recreate from scratch (if container was deleted)
```powershell
docker run -d `
  --name sqlserver1 `
  --memory 1g `
  -e "ACCEPT_EULA=Y" `
  -e "MSSQL_SA_PASSWORD=Pakasu@5" `
  -e "MSSQL_PID=developer" `
  -e "MSSQL_MEMORY_LIMIT_MB=768" `
  -p 1433:1433 `
  -v sqlserver_data:/var/opt/mssql `
  --restart unless-stopped `
  mcr.microsoft.com/mssql/server:2022-latest
```

### Wait for SQL Server to be ready (~15-20 seconds), then verify
```powershell
docker exec sqlserver1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Pakasu@5" -No -Q "SELECT name FROM sys.databases WHERE name = 'FinSight_AI';"
```
Expected output: `FinSight_AI`

> **Memory note**: SQL Server is capped at 1GB Docker memory and 768MB internally.  
> If it crashes with OOM errors, recreate with the command above — data is safe in the `sqlserver_data` volume.

---

## Step 2 — ChromaDB

ChromaDB holds 24,000+ document embeddings used by all AI features (AI Insights, AI Chat, recommendations).

### Start (if container already exists)
```powershell
docker start FinSight_AI_chromadb
```

### Recreate from scratch (if container was deleted)
```powershell
docker run -d `
  --name FinSight_AI_chromadb `
  -p 8001:8000 `
  -v chroma_data:/data `
  ghcr.io/chroma-core/chroma:latest
```

### Verify
```powershell
Invoke-RestMethod http://localhost:8001/api/v2/heartbeat
```
Expected: `{"nanosecond heartbeat": <number>}`

> **Memory note**: ChromaDB lazy-loads vector indexes into RAM only when queried.  
> Memory starts at ~13MB and grows to ~250-500MB as collections are accessed. This is normal.

---

## Step 3 — Streaming Stack (Kafka + Flink)

Optional for most features. Required only if you want:
- Live Finnhub news flowing into ChromaDB (RAG enrichment)
- Real market event alerts pushed to the Dashboard via WebSocket

> **Without Kafka/Flink**: The Dashboard still shows live portfolio value ticks — the backend
> price simulator runs automatically and requires no external services.

```powershell
cd C:\Agentic_AI\FinSight-AI
docker compose -f docker-compose-streaming.yml up -d
```

### Verify all 5 containers are up
```powershell
docker compose -f docker-compose-streaming.yml ps
```

Expected containers — all `Up`:

| Container | Port | UI |
|---|---|---|
| `finsight-zookeeper` | 2181 | — |
| `finsight-kafka` | 9092 | — |
| `finsight-kafka-ui` | 8080 | http://localhost:8080 |
| `finsight-flink-jobmanager` | 8082 | http://localhost:8082 |
| `finsight-flink-taskmanager` | — | — |

---

## Step 4 — FastAPI Backend

Open a **dedicated terminal** (keep it running):

```powershell
C:\Agentic_AI\finsightaivenv\Scripts\Activate.ps1
cd C:\Agentic_AI\FinSight-AI\backend
uvicorn main:app --reload
```

### Verify
```powershell
Invoke-RestMethod http://localhost:8000/health
```
Expected: `{"status": "healthy", "database": "connected"}`

> If you see `"database": "disconnected"`, SQL Server is still starting up. Wait 10 seconds and retry.

### Startup log — what to expect
When the backend starts you should see:
```
Starting FinSight AI API...
[OK]   Database connected
[OK]   WebSocket background tasks started (price simulator + Kafka bridge)
```
The price simulator and Kafka bridge start automatically — no manual action needed.

### Key API endpoints
| Endpoint | Description |
|---|---|
| `GET /docs` | Swagger UI — all endpoints |
| `GET /api/portfolios` | List portfolios |
| `POST /api/analysis/ai/explain-portfolio` | AI portfolio explanation |
| `POST /api/analysis/ai/narrate-changes` | AI position change narrative |
| `POST /api/analysis/ai/recommendations` | AI-enhanced recommendations |
| `POST /api/analysis/ai/chat` | Streaming chat SSE endpoint (Task 4.3) |
| `GET /api/analysis/ai/chat/suggested-questions` | Suggested chat questions |
| `ws://localhost:8000/ws` | **WebSocket — real-time portfolio + event feed (Task 4.2)** |
| `GET /ws/stats` | Active WebSocket connection count (debug) |

---

## Step 5 — Next.js Frontend

Open a **second dedicated terminal** (keep it running):

```powershell
cd C:\Agentic_AI\FinSight-AI\frontend
npm run dev
```

Open browser: **http://localhost:3000**

### Pages available

| Route | Live data? | Description |
|---|---|---|
| `/` | ✅ WebSocket | Dashboard — portfolio values flash green/red on every tick; Total AUM updates live; Kafka event alerts appear as toasts |
| `/portfolios` | — | Portfolio list with strategy and value |
| `/portfolios/[id]` | ✅ WebSocket | Portfolio detail — Total Value flashes with live Δ%; Wifi icon shows WS connection |
| `/ai-insights` | — | AI Insights — 3-panel analysis (Explanation · Narrative · Recommendations) |
| `/chat` | — | AI Chat — conversational Q&A with streaming GPT-4o responses |
| `/market-events` | — | Market event timeline with impact levels |
| `/market-events/[id]` | — | Event detail with affected portfolio list |

> **UI theme**: Bloomberg Terminal style — pure black background, orange `#F5821F` accents, monospace font throughout.

> **WebSocket**: connects automatically when the page loads. The indicator in the top bar shows
> **● LIVE** (green) when connected and **● RECONNECTING** (amber) while retrying.
> No configuration needed — it points to `ws://localhost:8000/ws` by default.

---

## Step 6 — Flink Streaming Pipeline (Optional — for live data)

Only needed if you want live news sentiment and volatility data flowing into ChromaDB.  
All AI features work without this using the existing batch-loaded RAG data.

### 6a — News Producer (24/7, polls every 2 minutes)
Open a **third terminal**:
```powershell
C:\Agentic_AI\finsightaivenv\Scripts\Activate.ps1
cd C:\Agentic_AI\FinSight-AI\backend\flink
python finnhub_news_producer.py
```

### 6b — Submit Flink News Sentiment Job
```powershell
docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/news_sentiment_job.py
```

Verify at http://localhost:8082 → Jobs → Running Jobs: `FinSight News Sentiment Stream` should show `RUNNING`.

### 6c — Trade Producer + Volatility Detector (market hours only — 9:30 AM–4:00 PM ET)
```powershell
# Terminal: start trade producer
python finnhub_trade_producer.py

# Submit volatility detector job
docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/volatility_detector_job.py
```

---

## Quick Health Check (all services at once)

Run this after startup to verify everything is up:

```powershell
# Docker containers
docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}" | Select-String "sqlserver1|chromadb|finsight"

# FastAPI (also confirms DB connection)
Invoke-RestMethod http://localhost:8000/health

# ChromaDB
Invoke-RestMethod http://localhost:8001/api/v2/heartbeat

# WebSocket active connections (should be 0 before browser opens, >0 after)
Invoke-RestMethod http://localhost:8000/ws/stats

# AI Chat endpoint (quick smoke test)
Invoke-RestMethod http://localhost:8000/api/analysis/ai/chat/suggested-questions
```

---

## Service Map

| Service | URL | Notes |
|---|---|---|
| **Frontend** | http://localhost:3000 | Next.js app — Bloomberg Terminal UI |
| **Backend API** | http://localhost:8000 | FastAPI + Swagger at `/docs` |
| **WebSocket feed** | ws://localhost:8000/ws | Real-time portfolio ticks + event alerts |
| **WS stats** | http://localhost:8000/ws/stats | Active connection count |
| **AI Chat** | http://localhost:3000/chat | Streaming conversational Q&A |
| **AI Insights** | http://localhost:3000/ai-insights | 3-panel portfolio analysis |
| **Kafka UI** | http://localhost:8080 | Monitor Kafka topics (optional) |
| **Flink UI** | http://localhost:8082 | Monitor streaming jobs (optional) |
| **ChromaDB** | http://localhost:8001 | Vector database (24,000+ docs) |
| **SQL Server** | localhost:1433 | SA password: `Pakasu@5` |

---

## Environment Variables (backend/.env)

| Variable | Used for |
|---|---|
| `OPENAI_API_KEY` | GPT-4o analysis, chat streaming, embeddings |
| `FINNHUB_API_KEY` | Live news/trades Kafka producer |
| `FRED_API_KEY` | Macroeconomic indicator RAG data |
| `AlphaVantage_API_KEY` | Additional market data |
| `DB_SERVER` / `DB_NAME` / `DB_USER` | SQL Server connection |

> Never commit `backend/.env` to git — it is excluded by `.gitignore`.

---

## Troubleshooting

### SQL Server OOM (out of memory)
Symptom: backend logs `TCP Provider: An existing connection was forcibly closed`
```powershell
docker stop sqlserver1; docker rm sqlserver1
# Then recreate using the command in Step 1 above
```
Data is safe — stored in Docker volume `sqlserver_data`.

### ChromaDB low memory (~13MB after restart)
Normal — it lazy-loads. Memory climbs to 250–500MB as collections are queried.

### AI Chat returns empty or stalls
1. Confirm backend is running: `Invoke-RestMethod http://localhost:8000/health`
2. Confirm ChromaDB is up: `Invoke-RestMethod http://localhost:8001/api/v2/heartbeat`
3. Check `OPENAI_API_KEY` is valid in `backend/.env`
4. Check browser console for SSE connection errors (should see `text/event-stream` response)

### AI Insights / AI Chat: "AI analysis failed"
- Most common cause: invalid or expired `OPENAI_API_KEY`
- Check backend terminal for the Python traceback

### Dashboard shows RECONNECTING instead of LIVE
The WebSocket connection to `ws://localhost:8000/ws` failed.
1. Confirm the backend is running: `Invoke-RestMethod http://localhost:8000/health`
2. Check the browser console (F12) for WebSocket errors
3. The hook retries automatically with exponential backoff — it will reconnect once the backend is up
4. After reconnecting the indicator turns green automatically with no page refresh needed

### Dashboard values not ticking / no green-red flashes
The price simulator starts automatically with the backend but only broadcasts when at least one
browser tab is open on the Dashboard or Portfolio Detail page.
1. Check `Invoke-RestMethod http://localhost:8000/ws/stats` — should show `{"active_connections": N}`
   where N > 0 after you open the browser
2. If N = 0 with the browser open, the WebSocket connection is failing (see above)
3. Ticks arrive every ~4 seconds — wait a few seconds before assuming it's broken

### Kafka event toasts not appearing on Dashboard
The amber event toasts require the Kafka + Flink pipeline to be running (Step 3 + Step 6).
Without Kafka, the price simulator still runs and portfolio values still tick — only the
real-time Kafka event notifications are missing.

### Kafka topic `market.trades` missing
Normal — topic auto-creates when the first trade message arrives. Run `finnhub_trade_producer.py` during market hours (Mon–Fri 9:30 AM–4:00 PM ET, excluding US holidays).

### Flink job shows `read-records: 0`
All operators are chained into one vertex — this metric is always 0 even when processing. Check TaskManager logs instead:
```powershell
docker logs finsight-flink-taskmanager --tail 30
```
Look for lines like `OK:NVDA:Bullish:0.813`.

### Frontend stuck on "Loading..."
Backend is not responding. Check Step 4 health check and confirm SQL Server is up.

### Docker Desktop crash
Restart Docker Desktop from system tray. Then restart all containers starting from Step 1.

---

## Docker Volumes (data persistence)

All data persists across container restarts in named Docker volumes. **Never delete these.**

| Volume | Used by | Contains |
|---|---|---|
| `sqlserver_data` | SQL Server | Portfolios, positions, transactions, market events |
| `chroma_data` | ChromaDB | 24,000+ document embeddings across 10 collections |
| `finsight_kafka_data` | Kafka | Message history (`market.news`, `market.trades`) |
| `finsight_zookeeper_data` | Zookeeper | Kafka cluster metadata |
| `finsight_flink_checkpoints` | Flink | Job state checkpoints |

> To list all volumes: `docker volume ls`  
> To check disk usage: `docker system df -v`

---

## Minimal Startup (no streaming, no Kafka/Flink)

If you only need the core app and AI features, just run Steps 1, 2, 4, and 5:

```
Step 1 → SQL Server
Step 2 → ChromaDB
Step 4 → FastAPI backend   ← price simulator + Kafka bridge start automatically
Step 5 → Next.js frontend
```

**What works without Kafka/Flink:**
- ✅ All pages load and function fully
- ✅ Dashboard portfolio values tick live (price simulator, every 4 seconds)
- ✅ Portfolio Detail Total Value flashes with live Δ%
- ✅ AI Insights, AI Chat, AI Recommendations (use existing batch-loaded RAG data)
- ✅ WebSocket LIVE indicator shows green

**What requires Kafka/Flink (Step 3 + Step 6):**
- ❌ Real-time Finnhub news flowing into ChromaDB for RAG enrichment
- ❌ Kafka market event toast alerts on the Dashboard