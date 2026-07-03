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
| `POST /api/analysis/ai/chat` | Agentic streaming chat SSE — GPT-4o calls tools autonomously (Task 3.4a) |
| `GET /api/analysis/ai/chat/suggested-questions` | Suggested chat questions |
| `GET /api/risk/{portfolio_id}` | Latest risk metrics (VaR, stress tests, factor exposure) |
| `POST /api/risk/{portfolio_id}/refresh` | Recompute risk metrics on demand (~10–30s) |
| `GET /api/alerts` | All alerts — optional: `portfolio_id`, `unread_only`, `limit` |
| `GET /api/alerts/unread-count` | Unread alert badge count `{"count": N}` |
| `PATCH /api/alerts/{id}/read` | Mark single alert as read |
| `PATCH /api/alerts/read-all` | Mark all read, optional `portfolio_id` filter |
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
| `/chat` | — | AI Chat — agentic GPT-4o: calls portfolio/RAG/risk tools on demand, streams answer |
| `/market-events` | — | Market event timeline with impact levels |
| `/market-events/[id]` | — | Event detail with affected portfolio list |
| `/portfolios/[id]` → Risk tab | — | VaR grid, stress test cards, factor exposure, inline alert panel |

> **Alerts**: The sidebar bell icon polls every 60s for unread alerts. Run the risk job (Step 7) at least once to generate data. Alert panel also appears inline on each portfolio's Risk Analytics tab.

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

> **Important**: Submit jobs one at a time. Both jobs share the same 4-slot TaskManager.
> Submitting simultaneously causes resource contention and heartbeat timeouts.

```powershell
# Terminal: start trade producer
python finnhub_trade_producer.py

# Submit volatility detector job
docker exec finsight-flink-jobmanager flink run -py /opt/flink/jobs/volatility_detector_job.py
```

Wait ~5 minutes for the first window to fire, then run the verification below.

### 6d — Verify Flink → ChromaDB Data Flow

Run these checks in order. Each confirms a different stage of the pipeline.

#### Stage 1 — Trade producer is publishing to Kafka
```powershell
docker exec finsight-kafka /bin/kafka-run-class kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic market.trades --time -1
```
Expected: `market.trades:0:<N>` where N grows each time you run it.  
If N is 0 or missing, the trade producer terminal has exited — restart it.

#### Stage 2 — Flink job is RUNNING (not FAILED)
```powershell
Invoke-RestMethod http://localhost:8082/jobs/overview | Select-Object -ExpandProperty jobs |
  Select-Object name, state, @{n='started';e={[DateTimeOffset]::FromUnixTimeMilliseconds($_.'start-time').LocalDateTime}} |
  Format-Table
```
Expected: `FinSight Volatility Detector` shows `RUNNING`.  
If it shows `FAILED`, check for the zombie loop (see Troubleshooting below) and restart the streaming stack.

#### Stage 3 — Flink is consuming trade messages
```powershell
$jid = (Invoke-RestMethod http://localhost:8082/jobs/overview).jobs |
  Where-Object { $_.state -eq "RUNNING" -and $_.name -like "*Volatility*" } |
  Select-Object -ExpandProperty jid
$vid = (Invoke-RestMethod "http://localhost:8082/jobs/$jid").vertices[0].id
Invoke-RestMethod "http://localhost:8082/jobs/$jid/vertices/$vid/metrics?get=1.Source__Finnhub_Trade_Source.KafkaSourceReader.KafkaConsumer.records-consumed-total,1.numRecordsOutPerSecond"
```
Expected: `records-consumed-total` is non-zero and growing; `numRecordsOutPerSecond` > 0.  
If both are 0, Flink started but cannot reach Kafka — restart the streaming stack.

#### Stage 4 — Windows are firing (sink has received results)
```powershell
$jid = (Invoke-RestMethod http://localhost:8082/jobs/overview).jobs |
  Where-Object { $_.state -eq "RUNNING" -and $_.name -like "*Volatility*" } |
  Select-Object -ExpandProperty jid
$vid = (Invoke-RestMethod "http://localhost:8082/jobs/$jid").vertices[1].id
Invoke-RestMethod "http://localhost:8082/jobs/$jid/vertices/$vid/metrics?get=0.Sink__Print_to_Std__Out.numRecordsIn"
```
Expected: `numRecordsIn` > 0 after the first 5-minute window closes.  
This confirms windows are firing. If still 0 after 10 minutes, no trades are flowing through.

#### Stage 5 — ChromaDB is receiving documents
```powershell
$volId = "2149b560-44a8-42b5-97ab-ef8f6b140527"
Invoke-RestMethod "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/$volId/count"
```
Expected: a positive number that grows every ~5 minutes.  
If Stage 4 shows windows firing but this stays 0, the OpenAI embedding or ChromaDB write is failing — check `docker logs finsight-flink-taskmanager --tail 50` for `ERROR:` lines.

#### Stage 6 — Spot-check actual record content
```powershell
$volId = "2149b560-44a8-42b5-97ab-ef8f6b140527"
$body = @{ limit = 3; include = @("documents","metadatas") } | ConvertTo-Json
$r = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/$volId/get" `
  -ContentType "application/json" -Body $body
for ($i = 0; $i -lt $r.documents.Count; $i++) {
    Write-Host "[$($r.metadatas[$i].ticker)] $($r.documents[$i])"
    Write-Host "  price_move: $($r.metadatas[$i].price_move_pct)%  vol_ratio: $($r.metadatas[$i].volume_ratio)x  detected: $($r.metadatas[$i].detected_at)"
}
```
Expected: readable sentences like `NVDA experienced a volatility event on 2026-06-22...` with plausible prices and volume ratios.

---

## Step 7 — Risk Job (Manual Run / On-Demand)

The daily risk job runs automatically on AWS via EventBridge Scheduler at 17:30 ET Mon–Fri.
Run it manually locally whenever you want to populate `Risk_Metrics` and generate alerts for all portfolios.

```powershell
cd "C:\Agentic_AI\FinSight-AI\backend"
& "C:\Agentic_AI\FinSight-AI\finsightaivenv\Scripts\python.exe" scripts/risk_job.py
```

### What it does (in order, per portfolio)
1. Computes VaR, stress tests, factor exposure (via yfinance — needs internet)
2. Saves results to `Risk_Metrics` table (one row per portfolio per day)
3. Evaluates alert thresholds → inserts `Alert` rows for any breaches
4. Logs: `[RiskJob] Complete — N succeeded, M failed, K alerts generated`

### After running the job
- **Risk Analytics tab** on any portfolio page will show real data (previously shows "not computed")
- **Sidebar bell icon** will show a badge if any thresholds were breached
- **Risk Alerts inline panel** will appear above the VaR grid on the Risk tab

### AWS EventBridge Automation
| Field | Value |
|---|---|
| Scheduler name | `finsight-daily-risk-job` |
| Schedule | `cron(30 21 ? * MON-FRI *)` = 17:30 ET Mon–Fri |
| Target | SSM SendCommand on `i-06df445415d082798` (finsight-flink EC2) |
| IAM role | `finsight-ec2-scheduler-role` (trust: `scheduler.amazonaws.com`) |
| Log file on EC2 | `/var/log/finsight_risk.log` |

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
| **AI Chat** | http://localhost:3000/chat | Agentic GPT-4o chat — calls 5 tools on demand |
| **AI Insights** | http://localhost:3000/ai-insights | 3-panel portfolio analysis |
| **Risk Analytics** | http://localhost:3000/portfolios/[id] → Risk tab | VaR, stress tests, factor exposure, inline alerts |
| **Alerts API** | http://localhost:8000/api/alerts | Alert list, unread count, mark read |
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
The chat now uses GPT-4o autonomous tool calling. It makes multiple OpenAI calls (one per tool
invocation) before streaming the final answer. Budget ~3–8 seconds before the first token arrives.

1. Confirm backend is running: `Invoke-RestMethod http://localhost:8000/health`
2. Confirm `OPENAI_API_KEY` is valid in `backend/.env` — chat now uses 2–4 API calls per question
3. ChromaDB is optional — if it's down, `search_market_context` returns `{"error": "ChromaDB unavailable"}` and GPT-4o answers from SQL data only. Other tools are unaffected.
4. Check browser console for SSE connection errors (should see `text/event-stream` response)
5. If the status bar shows `● CALLING: GET_PORTFOLIO_DATA` but never advances: the tool call returned an error — check the backend terminal for the Python traceback

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

### Flink job immediately FAILED / keeps crashing (heartbeat timeout)
Symptom: jobs fail within seconds or minutes with `TaskManager heartbeat timed out` in the Flink UI exception trace.

Cause 1 — Both jobs submitted simultaneously. The 4-slot TaskManager gets saturated.  
Fix: Submit only one job at a time. Cancel any running jobs first:
```powershell
$jid = (Invoke-RestMethod http://localhost:8082/jobs/overview).jobs | Where-Object state -eq "RUNNING" | Select-Object -ExpandProperty jid
Invoke-RestMethod -Method PATCH "http://localhost:8082/jobs/$jid?mode=cancel"
```
Then resubmit a single job.

Cause 2 — Cluster is in a zombie/split-brain state. Fix is a full streaming stack restart:
```powershell
cd C:\Agentic_AI\FinSight-AI
docker compose -f docker-compose-streaming.yml restart
```
Wait 20 seconds, verify all 5 containers are `Up`, then resubmit.

### TaskManager stuck in zombie loop (slot index climbing)
Symptom: `docker logs finsight-flink-taskmanager --tail 30` shows the same lines repeating:
```
Could not resolve JobManager address pekko.tcp://flink@flink-jobmanager:6123/user/rpc/jobmanager_N
Free slot TaskSlot(index:45 ...)
Allocated slot for ...
Free slot TaskSlot(index:46 ...)
```
The slot index keeps climbing (45 → 46 → 47 → ...). The TaskManager is cycling through slot
allocations every ~10 seconds and cannot reach the JobManager. No Python code is running.

Fix — restart the streaming stack:
```powershell
cd C:\Agentic_AI\FinSight-AI
docker compose -f docker-compose-streaming.yml restart
```

### ChromaDB `volatility_events` count not growing
Run Stage 3 and Stage 4 checks from Section 6d to isolate where the pipeline is broken:
- Stage 3 = 0 → Flink can't reach Kafka (restart streaming stack)
- Stage 4 = 0 → No trades flowing through (trade producer has exited, restart it)
- Stage 4 > 0 but Stage 5 = 0 → OpenAI or ChromaDB write is failing; check TaskManager logs:
```powershell
docker logs finsight-flink-taskmanager --tail 50
```
Look for `ERROR:` lines in the output — the exception message after `ERROR:` identifies the cause.

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

---

## Section 7: Vercel + ngrok (Remote Demo / Showcase Mode)

Use this when you want to share the app via a **public URL** for demos or portfolio showcasing,
without deploying the backend to cloud. The frontend runs on Vercel; the backend stays local
and is exposed temporarily through an ngrok tunnel.

**Architecture:**
```
Visitor browser → https://frontend-sandy-seven-21.vercel.app  (Vercel — always live)
                         ↓ API + WebSocket calls
              https://xxx.ngrok-free.app  (ngrok tunnel — active during your session)
                         ↓
              localhost:8000  (your local FastAPI backend)
```

---

### One-Time Setup

#### Install ngrok
```powershell
winget install Ngrok.Ngrok
```

#### Authenticate ngrok with your account token
Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken
```powershell
ngrok config add-authtoken YOUR_AUTH_TOKEN_HERE
```

#### Frontend is already deployed
Live URL: **https://frontend-sandy-seven-21.vercel.app**

To redeploy after any frontend code changes:
```powershell
cd C:\Agentic_AI\FinSight-AI\frontend
npx vercel --prod
```

---

### Every Demo Session — Steps

#### Step 1 — Start the local backend (follow Step 4 above as usual)
```powershell
C:\Agentic_AI\finsightaivenv\Scripts\Activate.ps1
cd C:\Agentic_AI\FinSight-AI\backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for `[OK] Database connected` and `Application startup complete`.

#### Step 2 — Start ngrok tunnel (new terminal)
```powershell
ngrok http 8000
```

ngrok will display:
```
Forwarding    https://a1b2c3d4xyz.ngrok-free.app → http://localhost:8000
```

Copy that `https://a1b2c3d4xyz.ngrok-free.app` URL.

#### Step 3 — Update Vercel Environment Variables

Go to: https://vercel.com → your project → Settings → Environment Variables

Update these two values using the ngrok URL from Step 2:

| Variable              | Value                                  |
|-----------------------|----------------------------------------|
| `NEXT_PUBLIC_API_URL` | `https://a1b2c3d4xyz.ngrok-free.app`  |
| `NEXT_PUBLIC_WS_URL`  | `wss://a1b2c3d4xyz.ngrok-free.app/ws` |

> `NEXT_PUBLIC_API_URL` → `https://` prefix, no trailing path
> `NEXT_PUBLIC_WS_URL` → `wss://` prefix (not `ws://`), must end with `/ws`

#### Step 4 — Redeploy frontend to pick up the new env vars
```powershell
cd C:\Agentic_AI\FinSight-AI\frontend
npx vercel --prod
```

#### Step 5 — Verify

Open: **https://frontend-sandy-seven-21.vercel.app**

In your ngrok terminal you should see all `200 OK`:
```
OPTIONS /api/portfolios     200 OK
GET     /api/portfolios/    200 OK
OPTIONS /api/market-events  200 OK
GET     /api/market-events/ 200 OK
```

> `307 Temporary Redirect` entries are normal FastAPI behaviour (trailing slash redirect) — ignore them.

---

### Important Notes

| Topic | Detail |
|---|---|
| ngrok URL changes | The URL is **different every time** you restart ngrok (free tier). Repeat Steps 3–4 each session. |
| Keep both terminals open | Closing the backend or ngrok terminal disconnects the Vercel frontend immediately. |
| WebSocket shows RECONNECTING | Expected when backend or ngrok is not running. Turns green once both are up. |
| Session limit | ngrok free tier sessions last up to 8 hours. |
| 307 Redirects in ngrok log | Normal — FastAPI redirects `/api/portfolios` → `/api/portfolios/`. Not an error. |

---

### Troubleshooting (Vercel + ngrok)

| Symptom | Cause | Fix |
|---|---|---|
| `400 Bad Request` on OPTIONS | CORS preflight rejected | Restart backend — `main.py` uses `allow_origins=["*"]` |
| `403 Forbidden` on GET requests | ngrok browser interstitial | `ngrok-skip-browser-warning: 1` header is set in `frontend/lib/api.ts` — restart backend and retry |
| `WebSocket /` 403 | `NEXT_PUBLIC_WS_URL` is missing `/ws` at the end | Update the env var to end with `/ws` and redeploy |
| Dashboard shows no data | ngrok URL changed after restart | Update both Vercel env vars with the new URL and redeploy |
| Frontend shows `RECONNECTING` | Backend or ngrok not running | Start both terminals and verify ngrok shows the forwarding URL |

---

## AWS — Running Flink + ChromaDB on EC2

Use this when you want the streaming pipeline running 24/7 on AWS instead of locally.
FastAPI backend and frontend stay local/Vercel — only Kafka/Flink and ChromaDB move to EC2.

### Instances

| Instance | Elastic IP | Purpose |
|---|---|---|
| `finsight-chromadb` (t3.micro) | `13.206.225.80` | ChromaDB vector store |
| `finsight-flink` (t3.medium) | `13.233.21.229` | Kafka + Flink + trade producer |

SSH key: `C:\Agentic_AI\aws\finsight-key.pem`

---

### Auto Start/Stop (Lambda Scheduler)

EC2 instances are managed automatically by the `finsight-ec2-scheduler` Lambda:
- **9:20 AM ET Mon–Fri** → Lambda starts both EC2 instances
- **4:25 PM ET Mon–Fri** → Lambda stops both EC2 instances
- **9:25 AM ET** → Cron on Flink EC2 runs `start_pipeline.sh` (5 min after EC2 starts)
- **4:15 PM ET** → Cron on Flink EC2 runs `stop_pipeline.sh`

**On normal market days you do not need to do anything.** Only follow the manual steps below if the Lambda fails or you need to recover mid-session.

To verify Lambda ran: AWS Console → Lambda → `finsight-ec2-scheduler` → Monitor → CloudWatch logs → look for the 9:20 AM ET invocation showing `[START]`.

---

### Manual Session Steps (recovery only)

#### Step 1 — Start both EC2 instances (if Lambda failed)
AWS Console → EC2 → Instances → select both → **Start instance**. Wait ~60 seconds.
Or test the Lambda directly: Lambda console → `finsight-ec2-scheduler` → Test → `{"action": "start"}`.

#### Step 2 — Verify ChromaDB is up
```powershell
Invoke-RestMethod "http://13.206.225.80:8001/api/v2/heartbeat"
```
Expected: `{"nanosecond heartbeat": <number>}`

If it times out, SSH in and restart the container:
```bash
ssh -i C:\Agentic_AI\aws\finsight-key.pem ec2-user@13.206.225.80
cd /home/ec2-user/chromadb && docker compose up -d
```

#### Step 3 — SSH into Flink EC2 and start the pipeline
```powershell
ssh -i C:\Agentic_AI\aws\finsight-key.pem ec2-user@13.233.21.229
```
```bash
bash /home/ec2-user/FinSight-AI/aws/ec2-flink/start_pipeline.sh
```
This starts Kafka + Flink containers, submits the volatility detector job, and launches the trade producer. Takes ~90 seconds total.

#### Step 4 — Verify trade producer connected correctly
```bash
tail -10 /home/ec2-user/logs/finsight-trade-producer.log
```
Must show `Connected to Kafka at 172.31.34.55:9092` (NOT localhost). If it shows `localhost:9092` or `401 Unauthorized`, the `.env` wasn't loaded — kill and restart manually:
```bash
kill $(cat /tmp/trade_producer.pid)
set -a; source /home/ec2-user/FinSight-AI/aws/ec2-flink/.env; set +a
source /home/ec2-user/FinSight-AI/flinkvenv/bin/activate
cd /home/ec2-user/FinSight-AI/backend/flink
PYTHONUNBUFFERED=1 nohup python -u finnhub_trade_producer.py >> /home/ec2-user/logs/finsight-trade-producer.log 2>&1 &
echo $! > /tmp/trade_producer.pid
```

#### Step 5 — Verify Flink job is running
```bash
curl -s http://localhost:8082/jobs/overview | python3 -c "import sys,json; [print(j['name'], j['state']) for j in json.load(sys.stdin)['jobs']]"
```
Expected: `FinSight Volatility Detector RUNNING`

#### Step 6 — After 5 minutes, verify ChromaDB is receiving data
```bash
curl -s 'http://13.206.225.80:8001/api/v2/tenants/default_tenant/databases/default_database/collections' | python3 -c "
import sys, json, urllib.request
cols = json.load(sys.stdin)
col_id = cols[0]['id']
count = json.loads(urllib.request.urlopen('http://13.206.225.80:8001/api/v2/tenants/default_tenant/databases/default_database/collections/' + col_id + '/count').read())
print(f'volatility_events: {count} documents')
"
```
Expected: a positive and growing number.

---

### Stop Steps (end of day)

```bash
# On Flink EC2
bash /home/ec2-user/FinSight-AI/aws/ec2-flink/stop_pipeline.sh
```
Then go to AWS Console → stop both EC2 instances to save credits.

---

### Cron (auto-starts pipeline after Lambda starts EC2)

Cron is already installed on the Flink EC2 and runs automatically:
- **9:25 AM ET Mon–Fri** → `start_pipeline.sh`
- **4:15 PM ET Mon–Fri** → `stop_pipeline.sh`

The cron window fires once at 9:25 AM ET. If the EC2 starts late (Lambda delay or manual start after 9:25 AM ET), the cron won't fire again — run `start_pipeline.sh` manually in that case.

---

### Key Log Files (on Flink EC2)

| File | What it shows |
|---|---|
| `/home/ec2-user/logs/finsight-pipeline.log` | Pipeline start/stop events |
| `/home/ec2-user/logs/finsight-trade-producer.log` | WebSocket connection status + trade count |
| `docker logs finsight-flink-taskmanager --tail 50` | Flink job output (NORMAL/ALERT/ERROR per symbol) |

---

### Troubleshooting (AWS)

| Symptom | Fix |
|---|---|
| EC2 instances not started at 9:20 AM ET | AWS Console → Lambda → `finsight-ec2-scheduler` → Monitor → check CloudWatch logs. If log group missing or access denied, the Lambda IAM role is broken. Verify trust policy includes `lambda.amazonaws.com` and permissions include `ec2:StartInstances` + CloudWatch Logs. |
| Lambda test fails: "role cannot be assumed by Lambda" | IAM → `finsight-ec2-scheduler-role` → Trust relationships → add `lambda.amazonaws.com` alongside `scheduler.amazonaws.com` |
| Kafka offset frozen despite producer showing "N trades published" | Kafka is advertising its public Elastic IP and the EC2 cannot hairpin-NAT to itself. Check `.env` on Flink EC2: `KAFKA_EXTERNAL_IP` must be `172.31.34.55` (private IP), not `13.233.21.229`. If wrong, fix and run `docker compose up -d --force-recreate kafka`. |
| Duplicate Flink jobs (two Volatility Detector entries) | `start_pipeline.sh` was run twice. Cancel the newer duplicate: `curl -X PATCH http://localhost:8082/jobs/<jid>?mode=cancel` |
| ChromaDB heartbeat times out | SSH into ChromaDB EC2, run `cd /home/ec2-user/chromadb && docker compose up -d` |
| `curl http://13.206.225.80:8001` hangs from Flink EC2 | Check security group `finsight-chromadb-sg` — port 8001 must be open to `0.0.0.0/0` |
| Trade producer shows `401 Unauthorized` | `.env` not sourced — follow Step 4 manual restart above |
| Flink job not RUNNING | Run `docker compose ps` on Flink EC2 — if containers are down, run `cd /home/ec2-user/FinSight-AI/aws/ec2-flink && docker compose up -d`, then resubmit: `docker exec finsight-flink-jobmanager flink run --detached -py /opt/flink/jobs/volatility_detector_job.py` |
| ChromaDB document count stuck at 0 | Check `docker logs finsight-flink-taskmanager --tail 30` for ERROR lines. No errors + NORMAL outputs = market is calm, no 1.5% moves yet — this is expected |
