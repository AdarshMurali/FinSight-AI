# FinSight AI — Knowledge Base

Running log of operational findings, architecture decisions, and verified behaviors
discovered during development and live testing.

---

## Task 5.1 — Risk Analytics (2026-06-27) ✅ Complete

### Architecture

```
risk_job.py (daily)
    │
    ├── compute_all(db, portfolio_id)   ← backend/services/risk_analytics.py
    │       ├── historical_var()        — 252-day rolling returns via yfinance
    │       ├── parametric_var()        — assumes normal distribution
    │       ├── stress_tests()          — 6 historical scenarios
    │       └── factor_exposure()       — regression vs. SPY, QQQ, VTV, MTUM
    │
    ├── save_result(db, pid, result)    ← writes to Risk_Metrics table (one row/day/portfolio)
    │
    └── run_alerts_for_portfolio()      ← Task 5.2 (see below)
```

### AWS Automation
- Scheduler: `finsight-daily-risk-job` (AWS EventBridge Scheduler)
- Schedule: `cron(30 21 ? * MON-FRI *)` = 17:30 ET Mon-Fri
- Target: SSM `AWS-RunShellScript` on EC2 `i-06df445415d082798` (finsight-flink)
- Command: activates `/home/ec2-user/finsight/venv`, runs `risk_job.py`, logs to `/var/log/finsight_risk.log`
- IAM role: `finsight-ec2-scheduler-role` — trust: `scheduler.amazonaws.com`, permission: `ssm:SendCommand`

### Why Historical Rows Matter
`Risk_Metrics` keeps one row per portfolio per day. Currently only the latest row is read by the API. The history silently accumulates — Task 5.3 will surface it via a VaR trend chart.

### Local Run Command
```powershell
cd "C:\Agentic_AI\FinSight-AI\backend"
& "C:\Agentic_AI\FinSight-AI\finsightaivenv\Scripts\python.exe" scripts/risk_job.py
```

### Risk_Metrics Table Schema
| Column | Type | Notes |
|---|---|---|
| `metric_id` | INT PK | Auto-increment |
| `portfolio_id` | INT FK | → Portfolios |
| `computed_at` | DATETIME | UTC timestamp of computation |
| `price_date` | DATE | Market data date (today) |
| `var_data` | TEXT | JSON: historical VaR, parametric VaR, distribution stats |
| `stress_data` | TEXT | JSON array of 6 stress test results |
| `factor_data` | TEXT | JSON: factor betas and R² |
| `status` | VARCHAR | Always "completed" for successful rows |

### Stress Test Scenarios (6)
| Key | Scenario | Approx shocks |
|---|---|---|
| `crisis_2008` | 2008 Financial Crisis | Equities -50%, credit spreads +400bps |
| `covid_2020` | COVID Crash | Equities -35% over 5 weeks |
| `rate_hike` | Fed Rate Hike | Rates +200bps, growth equities -20% |
| `tech_crash` | Tech Bubble | Tech -70%, value stocks flat |
| `oil_shock` | Oil Price Shock | Oil +80%, energy +25%, consumer -10% |
| `stagflation` | Stagflation | Rates +300bps, equities -20%, commodities +30% |

### Factor Exposure Benchmarks
| Factor | ETF used | Interpretation |
|---|---|---|
| Market | SPY | Overall market beta |
| Tech | QQQ | Growth/tech tilt |
| Value | VTV | Value tilt |
| Momentum | MTUM | Trend-following exposure |

---

## Task 5.2 — Alert System (2026-06-27) ✅ Complete

### Alert Generation Flow

```
risk_job.py (per portfolio, after save_result)
    │
    └── run_alerts_for_portfolio(db, pid, pname)
            │
            ├── reads latest Risk_Metrics row for pid
            ├── generate_threshold_alerts()
            │       ├── VaR 95% > 2.0%  → severity=warning
            │       ├── VaR 99% > 3.5%  → severity=critical
            │       ├── any stress test < -25%  → severity=warning
            │       ├── any stress test < -40%  → severity=critical
            │       └── market beta > 1.5  → severity=warning
            │
            ├── dedup: _already_alerted_today() — one alert per title per portfolio per day
            └── commits Alert rows to SQL Server
```

### Alert Table Schema
| Column | Type | Notes |
|---|---|---|
| `alert_id` | INT PK | Auto-increment |
| `portfolio_id` | INT FK nullable | → Portfolios (null for system-wide alerts) |
| `alert_type` | VARCHAR(50) | threshold \| event \| ai |
| `severity` | VARCHAR(20) | critical \| warning \| info |
| `title` | VARCHAR(255) | Short label, used for dedup |
| `message` | TEXT | Full explanation string |
| `is_read` | INT | 0=unread, 1=read |
| `triggered_at` | DATETIME | UTC, auto-set on insert |

### REST API
| Endpoint | Method | Description |
|---|---|---|
| `/api/alerts` | GET | Optional: `portfolio_id`, `unread_only`, `limit` |
| `/api/alerts/unread-count` | GET | `{"count": N}` — for badge |
| `/api/alerts/{id}/read` | PATCH | Mark single alert read |
| `/api/alerts/read-all` | PATCH | Mark all read, optional `portfolio_id` |

### Frontend — Two UI Placements

**1. Sidebar Bell Icon** (`Sidebar.tsx`)
- Polls `unread-count` every 60s; red badge when > 0
- Click → slide-out panel (320px wide, right of sidebar)
- Shows all alerts across all portfolios
- Severity dot + colored left border per alert (critical=#FF4040, warning=#FFB300, info=#00CC44)

**2. Risk Analytics Tab Inline Panel** (`portfolios/[id]/page.tsx`)
- Loads portfolio-specific alerts when Risk tab opens
- Orange gradient header "Risk Alerts" with unread count badge
- Individual dismiss (X) or "Mark All Read" (CheckCheck icon)

Both placements share the same API — only the `portfolio_id` filter differs.

### Currently Implemented Alert Types
- **Threshold** alerts: fully implemented (5 check types)
- **Event** alerts: column exists, no engine yet
- **AI-generated** alerts: column exists, no engine yet

---

## Task 3.4a — Agentic AI Chat (2026-06-25)

### What Changed

The `/chat` endpoint was upgraded from static context injection to GPT-4o autonomous tool calling.

**Before (static pre-load):**
Every question — regardless of what was asked — triggered two fixed operations upfront:
1. `PortfolioAnalyzer.analyze_portfolio_state()` → current snapshot only (total value, top sectors, top 5 positions)
2. `MarketRAGEngine.retrieve_context(query, n_results=5)` → 5 docs from ChromaDB

Both results were stuffed into a giant system prompt string and sent to GPT-4o. The LLM
answered from that frozen block. If the question needed data outside the snapshot (historical
changes, a different portfolio, specific event details), quality degraded.

**After (agentic tool calling):**
GPT-4o receives a system prompt and a menu of 5 tools. It decides which tools to call based on
the question, executes them via a non-streaming loop, then streams the final answer.

```
User question → GPT-4o thinks → calls tools → gets live results → streams final answer
```

### Tool Loop Architecture

```python
# Non-streaming loop (handles tool calls cleanly)
while iterations < MAX_TOOL_ITERATIONS:
    response = openai.chat.completions.create(model="gpt-4o", messages=..., tools=TOOL_DEFINITIONS)
    if finish_reason != "tool_calls":
        break  # ready to stream final answer
    # yield {"tool_call": name} → frontend shows "● CALLING: ..."
    # execute tool → append {"role": "tool", ...} to messages

# Streaming final answer
stream = openai.chat.completions.create(model="gpt-4o", messages=..., stream=True)
for chunk in stream:
    yield {"token": delta.content}
```

**Key design decision**: non-streaming for tool calls (clean arg accumulation), streaming for
final answer (good UX). If GPT-4o answers directly without tools (rare), the non-streaming
answer is yielded as a single token chunk.

### The 5 Tools

| Tool | Service | When GPT-4o calls it |
|---|---|---|
| `get_portfolio_data` | `PortfolioAnalyzer.analyze_portfolio_state()` | "What's my sector allocation?", "How is the portfolio performing?" |
| `get_position_history` | `PositionChangeDetector.detect_significant_changes()` | "What changed in October?", "What did I buy/sell?" |
| `search_market_context` | `MarketRAGEngine.retrieve_context()` | "Why did tech drop?", "What's the macro outlook?" |
| `get_market_events` | SQL `MarketEvent` query | "What Fed events affected energy?", "Show recent high-impact events" |
| `run_risk_analysis` | `RecommendationEngine.generate_recommendations()` | "What are my biggest risks?", "How should I rebalance?" |

### SSE Event Format (new)

The chat endpoint previously emitted only `{"token": str}`. It now also emits:
```
data: {"tool_call": "get_portfolio_data"}\n\n   ← during tool execution phase
data: {"token": "The portfolio..."}\n\n          ← during final answer streaming
data: [DONE]\n\n
```

The `api.ts` `aiChatStream()` function accepts an optional `onToolCall?` callback for the new event type.

### RAG Is Unchanged

The `search_market_context` tool calls the same `MarketRAGEngine.retrieve_context()` that the old
system used, just on-demand instead of always. Flink → ChromaDB pipeline is unaffected. The
agentic upgrade is purely a change in how and when data is fetched.

### Files Changed

| File | Change |
|---|---|
| `backend/services/ai_tools.py` | NEW — tool schemas + execute_tool() dispatcher |
| `backend/services/ai_chat_service.py` | REWRITTEN — agentic loop, yields dicts not strings |
| `backend/routers/analysis.py` | 2-line — `for token` → `for event`, pass dict to SSE |
| `frontend/lib/api.ts` | +2 lines — `onToolCall?` param + `parsed.tool_call` branch |
| `frontend/app/chat/page.tsx` | ToolChips component, streamingToolCalls state, status indicator |

---

## Task 3.4a — Live Validation Results (2026-06-26)

End-to-end browser test using Chrome DevTools MCP against the running stack.

### Tools Confirmed Working

| Tool | Trigger question | Result |
|---|---|---|
| `run_risk_analysis` | "Run a full risk analysis..." | Fired solo; returned Sharpe -4.54, rebalancing suggestion |
| `get_portfolio_data` | "What is my portfolio allocation..." | Fired; returned $60M total, $3M cash, 5% Technology |
| `get_position_history` | same multi-tool question | Fired; returned no significant changes (3% threshold not crossed) |
| `search_market_context` | same multi-tool question | Fired; ChromaDB unavailable — graceful degradation confirmed |

### Multi-Tool Chaining Confirmed

Asking a compound question triggered 3 tools in one turn: `PORTFOLIO DATA` → `POSITION HISTORY` → `MARKET CONTEXT`. All three orange chips appeared above the response bubble. The SSE status bar cycled through each tool name (`● CALLING: SEARCH_MARKET_CONTEXT`) while the tool loop ran.

### ChromaDB Graceful Degradation — Confirmed

When ChromaDB container is not running, `search_market_context` returns `{"error": "ChromaDB unavailable"}`. GPT-4o receives this, reports "Market Context (Unavailable)" in its answer, and continues with data from the other tools. No crash, no 500, input re-enables normally.

### UX Observations

- Tool chips (orange pills) render above the text block inside the assistant bubble
- `● CALLING: <TOOL_NAME>` appears in the hint strip below the header during tool execution
- `● GENERATING...` replaces it once the streaming answer begins
- Input textarea re-enables and placeholder reverts to "Type your question..." on `[DONE]`
- CLEAR button appears in header as soon as a message exists

---

## Bug Fix: Markdown Not Rendering in Chat Bubbles (2026-06-26)

### Symptom

GPT-4o responses containing markdown (`**bold**`, `### Header`, bullet lists) were rendered as
plain text — raw asterisks and hashes visible in the chat bubble.

### Root Cause

`frontend/app/chat/page.tsx` `Bubble` component rendered assistant content as:
```tsx
<div className="... whitespace-pre-wrap">
  {msg.content}   {/* plain React text node — no markdown processing */}
</div>
```

### Fix

Installed `react-markdown` + `remark-gfm` and replaced the text node with `<ReactMarkdown>`:

```tsx
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  components={{
    h1/h2/h3: orange text, font-bold, tracking-wider
    strong:   white text, font-bold
    p:        mb-2 paragraphs
    ul/ol/li: list-disc/decimal with spacing
    code:     dark bg, orange text
    pre:      dark bg, scrollable
  }}
>
  {msg.content}
</ReactMarkdown>
```

### Files Changed

| File | Change |
|---|---|
| `frontend/app/chat/page.tsx` | Added `ReactMarkdown` import + replaced `{msg.content}` + removed `whitespace-pre-wrap` |
| `frontend/package.json` | Added `react-markdown`, `remark-gfm` dependencies |

### Styling Decisions

- Headers (`h1`/`h2`/`h3`) → `#F5821F` orange to match the terminal accent color
- Bold (`**text**`) → white (`text-white`) for high contrast against the dark bg
- Inline code → `bg-[#1A1A1A]` with orange text (same as terminal prompt color)
- Removed `whitespace-pre-wrap` from the container — ReactMarkdown handles its own whitespace

---

## AWS Deployment Session — 2026-06-23/24

### Infrastructure
- ChromaDB → EC2 t3.micro, Elastic IP `13.206.225.80`, key at `C:\Agentic_AI\aws\finsight-key.pem`
- Flink + Kafka → EC2 t3.medium, Elastic IP `13.233.21.229`, private IP `172.31.34.55`
- All deployment files in `aws/` folder in repo root
- Both instances STOPPED overnight (safe, EBS persists all data and setup)

### Bugs Found and Fixed During AWS Setup

**1. Kafka readiness check used wrong port**
`start_pipeline.sh` checked `kafka-topics --bootstrap-server localhost:9092`. On AWS, port 9092 is the external listener (advertised as Elastic IP) — unreachable from inside the container itself. Fixed to use `localhost:29092` (internal PLAINTEXT listener).

**2. Docker volume path hardcoded to `/home/ubuntu`**
`docker-compose.yml` in `aws/ec2-flink/` used Ubuntu paths. Amazon Linux 2023 uses `ec2-user`. Fixed with `sed` on EC2.

**3. Flink job submission blocks the shell**
`flink run -py` with PyFlink blocks until the streaming job completes (forever). Prevents trade producer from starting. Fixed by adding `--detached` flag: `flink run --detached -py`.

**4. Kafka topic doesn't exist on fresh cluster**
Flink fails immediately with `UnknownTopicOrPartitionException` if `market.trades` doesn't exist yet. Fixed by adding topic pre-creation step to `start_pipeline.sh` using `--if-not-exists`.

**5. kafka-python 3.0.4 removed NoBrokersAvailable**
EC2 venv installed latest kafka-python (3.x) which dropped `NoBrokersAvailable` from `kafka.errors`. Fixed by pinning `kafka-python==2.0.2`.

**6. Python 3.9 on EC2 doesn't support `X | Y` union type syntax**
`finnhub_trade_producer.py` line 34: `producer: KafkaProducer | None = None` — this is Python 3.10+ syntax. EC2 runs Python 3.9. Fixed on EC2 with `sed` (`producer = None`). Local file unchanged.

**7. EC2 can't reach its own Elastic IP (Kafka self-connection)**
Trade producer on Flink EC2 was configured to connect to Kafka at `13.233.21.229:9092` (Elastic IP). AWS blocks EC2 instances from reaching their own public IP. Fixed by setting `KAFKA_BOOTSTRAP_SERVERS=172.31.34.55:9092` (private IP) and updating `KAFKA_ADVERTISED_LISTENERS` to use the private IP.

**8. .env not loaded by trade producer (wrong directory)**
`load_dotenv()` in `config.py` looks for `.env` in the script directory (`backend/flink/`). The `.env` is in `aws/ec2-flink/`. Fixed `start_pipeline.sh` to use `set -a; source $REPO/aws/ec2-flink/.env; set +a` before starting the producer.

**9. `/var/log/` not writable by ec2-user**
`start_pipeline.sh` originally wrote logs to `/var/log/finsight-pipeline.log`. Amazon Linux non-root users can't write there. Fixed all log paths to `/home/ec2-user/logs/`.

### ONE Remaining Blocker (as of session end)
ChromaDB security group (`finsight-chromadb-sg`) doesn't allow port 8001 from Flink EC2 private IP `172.31.34.55`. Flink containers cannot reach ChromaDB. Fix before next run:
- AWS Console → Security Groups → `finsight-chromadb-sg` → Edit inbound rules
- Add: Custom TCP, Port 8001, Source `172.31.34.55/32`

### Verified Working
- Trade producer connects to Finnhub WebSocket and publishes to Kafka (1,479 messages confirmed)
- Kafka topic `market.trades` exists and receives live trades
- Flink Volatility Detector job submits and reaches RUNNING state
- Cron schedule installed (9:25 AM / 4:15 PM ET Mon-Fri)
- ChromaDB accessible from local laptop at `http://13.206.225.80:8001`
- ChromaDB accessible from within ChromaDB EC2 itself

---

## Flink Streaming Pipeline — Trade Producer + Volatility Detector

### What the Pipeline Does

The streaming pipeline is a real-time data enrichment layer that feeds the RAG system
with live market intelligence. It has three stages:

```
Finnhub WebSocket (live trades for 50 stocks)
        │
        ▼
Kafka  topic: market.trades
        │
        ▼
Flink  5-minute tumbling window per ticker
        │  → OHLCV aggregation
        │  → detect: price move > 1.5%  OR  volume > 2x rolling average
        │
        ├─ NORMAL → discard
        │
        └─ ALERT → OpenAI text-embedding-3-small → ChromaDB  volatility_events
```

**Trade Producer** (`backend/flink/finnhub_trade_producer.py`):
- Opens a Finnhub WebSocket connection
- Subscribes to live trade ticks for all 50 covered tickers
- Publishes each tick to Kafka topic `market.trades` as JSON
- Runs only during market hours (Mon–Fri 9:30 AM–4:00 PM ET)
- Reconnects automatically on WebSocket drop

**Volatility Detector** (`backend/flink/volatility_detector_job.py`):
- Reads from `market.trades` using Flink's Kafka source (reads from latest offset)
- Groups trades by ticker symbol using `key_by`
- Applies a 5-minute `TumblingProcessingTimeWindows`
- Aggregates: open/high/low/close price + total volume + trade count (`WindowAggregator`)
- Detects two triggers:
  - **Price spike**: `abs(close - open) / open * 100 >= 1.5%`
  - **Volume spike**: `window_volume / rolling_avg_volume >= 2.0x`
- On trigger: builds a natural-language event document, calls OpenAI to embed it,
  upserts into ChromaDB `volatility_events` collection
- Uses `parallelism=2` — consumes 2 of the 4 TaskManager slots

**Covered tickers (50)**:
AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, BRK.B, JPM, JNJ, V, WMT, PG, MA,
INTC, NFLX, MCD, DIS, KO, PEP, ABT, TMO, MRK, IBM, CSCO, CAT, F, GM, BA, HON,
UNP, AXP, SPG, XOM, CVX, COP, MPC, PSX, VLO, EQR, VZ, T, TMUS, DELL, ORCL, AMD,
PYPL, ADBE, AVGO, INTU

---

## ChromaDB — volatility_events Collection

**Collection ID**: `2149b560-44a8-42b5-97ab-ef8f6b140527`

Each document is a natural-language event description, e.g.:
```
NVDA experienced a volatility event on 2026-06-22. Price moved -0.05% (DOWN)
from $875.50 to $874.96 in a 5-minute window (high $875.60, low $874.96).
Volume: 12,400 shares (10.2x average). Triggers: volume was 10.2x the rolling average.
```

**Metadata fields per document**:

| Field | Type | Description |
|---|---|---|
| `ticker` | string | Stock symbol |
| `direction` | string | UP / DOWN |
| `price_move_pct` | float | % price change in window |
| `high_low_range_pct` | float | % range (high-low)/low |
| `total_volume` | int | Shares traded in window |
| `volume_ratio` | float | Volume vs rolling average |
| `price_spike` | bool | Whether price threshold triggered |
| `volume_spike` | bool | Whether volume threshold triggered |
| `open_price` / `close_price` | float | Window OHLCV prices |
| `window_start` / `window_end` | string | ISO timestamps of 5-min window |
| `detected_at` | string | UTC ISO timestamp of detection |
| `source` | string | Always `flink_volatility_detector` |
| `data_type` | string | Always `volatility_event` |
| `event_type` | string | Always `volatility` |
| `ingested_via` | string | Always `flink_stream` |

**Quick count check**:
```powershell
$volId = "2149b560-44a8-42b5-97ab-ef8f6b140527"
Invoke-RestMethod "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/$volId/count"
```

**Spot-check records**:
```powershell
$volId = "2149b560-44a8-42b5-97ab-ef8f6b140527"
$body = @{ limit = 5; include = @("documents","metadatas") } | ConvertTo-Json
$r = Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections/$volId/get" `
  -ContentType "application/json" -Body $body
for ($i = 0; $i -lt $r.documents.Count; $i++) {
    Write-Host "[$($r.metadatas[$i].ticker)] $($r.documents[$i])"
    Write-Host "  vol_ratio=$($r.metadatas[$i].volume_ratio)x  detected=$($r.metadatas[$i].detected_at)"
}
```

---

## AI / RAG Impact

The `volatility_events` collection sits alongside the 11 other batch-loaded ChromaDB
collections (`market_news`, `earnings_data`, `analyst_research`, `ohlcv_data`, etc.).

When a user asks a question in AI Chat or triggers AI Insights, the RAG retriever does a
semantic search across all collections and picks the most relevant chunks. Volatility event
documents are retrieved alongside historical data, giving the LLM grounded, time-aware
context for its answers.

**Without volatility_events**: AI answers rely on batch data — earnings last quarter,
analyst reports last month. No awareness of intraday activity.

**With volatility_events**: AI can reference events from minutes ago.

Example:
> User: "Was there anything unusual with Walmart yesterday?"
> AI (with RAG): "WMT showed a 56.8x volume spike at 18:55 UTC with minimal price
> movement (+0.06%), consistent with a large institutional block trade near close."

---

## First Live Run — 2026-06-22 (Verified Results)

### Trade Producer
- Published **9,963+ trade messages** to `market.trades` across the session
- Finnhub WebSocket connected and sustained throughout market hours

### Volatility Detector — ChromaDB Output
- **128 total documents** written to `volatility_events`
- **46 of 50 tickers** detected with at least one event
- **5 window batches** fired between 18:26–19:10 UTC (2:26–3:10 PM ET)

| Window fired (UTC) | ET | Stocks |
|---|---|---|
| 18:26 | 2:26 PM | 33 |
| 19:00 | 3:00 PM | 29 |
| 19:05 | 3:05 PM | 39 |
| 19:09 | 3:09 PM | 2 |
| 19:10 | 3:10 PM | 25 |

**Key observation**: All 128 events were triggered by **volume spikes only**. The 1.5% price
threshold was never crossed — market price action was low-volatility on this day, but
institutional volume activity was significant.

**Top volume spikes detected**:

| Ticker | Volume Spike | Price Move | Window (UTC) |
|---|---|---|---|
| WMT | 56.8x | +0.06% | 18:55 |
| GM | 47.4x | -0.14% | 18:20 |
| AVGO | 40.0x | -0.16% | 18:55 |
| T | 39.3x | -0.07% | 18:56 |
| V | 26.7x | -0.10% | 19:00 |
| INTU | 24.3x | -0.07% | 18:55 |
| AMD | 23.3x | -0.06% | 18:55 |
| PG | 23.0x | -0.01% | 18:20 |
| INTC | 22.4x | +0.004% | 18:20 |
| AMZN | 20.5x | +0.004% | 18:20 |

---

## Known Issues and Fixes Applied

### Bug: window_end always empty in ChromaDB records
**File**: `backend/flink/volatility_detector_job.py`, `WindowAggregator.reduce()` line 74

**Root cause**: `TradeToWindowEntry.map()` converts raw trades into aggregation-shaped dicts
that have `window_start` and `window_end` keys but drop the original `timestamp_iso` key.
The reducer was reading `b.get("timestamp_iso", "")` — since `b` is always a
`TradeToWindowEntry` output (not a raw trade), `timestamp_iso` was never present and always
fell back to `""`.

**Fix applied**:
```python
# Before (broken)
"window_end": b.get("timestamp_iso", ""),

# After (fixed)
"window_end": b.get("window_end", ""),
```

**Effect**: `window_end` and `event_date` in document text now populate correctly for all
new records. Existing 128 records from 2026-06-22 have empty `window_end` — this is
expected and harmless since the other metadata fields are correct.

---

## Operational Issues Discovered on First Run (2026-06-22)

### 1. TaskManager heartbeat timeout (recurring crash)
**Symptom**: Both Flink jobs (`FinSight Volatility Detector` and `FinSight News Sentiment
Stream`) fail repeatedly with:
```
java.util.concurrent.TimeoutException: Heartbeat of TaskManager timed out.
```
**Cause**: Both jobs submitted simultaneously consume all 4 TaskManager slots. Python
workers saturate the JVM, heartbeat gaps exceed Flink's default threshold.

**Fix**: Submit jobs one at a time. Volatility Detector first; add News Sentiment only
after confirming it is stable.

### 2. Flink cluster zombie/split-brain state
**Symptom**: `docker logs finsight-flink-taskmanager --tail 30` shows slot index climbing
(index:45 → 46 → 47 → ...) with the same line repeating every 10 seconds:
```
Could not resolve JobManager address pekko.tcp://flink@flink-jobmanager:6123/user/rpc/jobmanager_N
```
The TaskManager cycles through slot allocations indefinitely. No Python code runs.
ChromaDB count stays at 0 despite jobs appearing in the Flink UI.

**Fix**: Full streaming stack restart:
```powershell
cd C:\Agentic_AI\FinSight-AI
docker compose -f docker-compose-streaming.yml restart
```

### 3. Docker Desktop API returning 500
**Symptom**: All `docker` CLI commands fail with `500 Internal Server Error` from the
Docker Desktop Linux engine pipe. Affects `docker logs`, `docker exec`, `docker ps`.

**Workaround**: Flink REST API and ChromaDB HTTP API remain accessible even when the Docker
CLI is broken. Use `Invoke-RestMethod http://localhost:8082/...` to query Flink and
`Invoke-RestMethod http://localhost:8001/...` to query ChromaDB directly. Recover the CLI
by restarting Docker Desktop from the system tray.

---

## Flink Pipeline Verification Checklist

Run these in order whenever you need to confirm the pipeline is working end-to-end.
See `STARTUP_GUIDE.md` Section 6d for the full commands.

| Stage | Command target | Expected result |
|---|---|---|
| 1 — Trade producer alive | Kafka offset on `market.trades` | Growing number |
| 2 — Flink job healthy | Flink REST `/jobs/overview` | State = `RUNNING` |
| 3 — Trades being consumed | Flink vertex metrics (`records-consumed-total`) | Non-zero and growing |
| 4 — Windows firing | Flink sink metrics (`numRecordsIn`) | > 0 after first 5 min |
| 5 — ChromaDB receiving | `volatility_events` collection count | Growing every ~5 min |
| 6 — Data quality | Spot-check documents + metadata | Readable text, valid prices |
