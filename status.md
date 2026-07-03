## Project Status — FinSight AI
**Last Updated**: 2026-07-03 (Phase 5 tasks 5.1, 5.2, 5.3 complete)

---

### Phase 1: Data Modeling & Synthetic Data Generation ✅ COMPLETED

- ✅ Task 1.1: Database Schema Design — 8 tables designed and created in SQL Server
- ✅ Task 1.2: Synthetic Data Generation — 1,500+ portfolio records, 500+ securities, full position/transaction/performance history loaded
- ⚠️ Task 1.3: Database Setup & Migration Framework — Partially done (manual SQL scripts used, no formal Alembic migration framework)

**Database:**
- Engine: SQL Server 2022 (Docker container `sqlserver1`)
- Host: localhost:1433 | DB: FinSight_AI | User: sa
- Tables: Customers, Securities, Portfolios, Positions, Transactions, Market_Events, Portfolio_Performance, Position_Changes_Log
- Data volume: ~1,500 portfolio records across 500+ customers, 500+ securities

---

### Phase 2: Backend API Development ✅ COMPLETED

- ✅ Task 2.1: Core API Framework — FastAPI with 18+ REST endpoints, Swagger at /docs, health check, SQLAlchemy ORM
  - Portfolio CRUD: GET /api/portfolios, /api/portfolios/{id}, positions, performance, history
  - Securities: GET /api/securities, /api/securities/{id}
  - Market Events: GET /api/market-events, /api/market-events/{id}/affected-portfolios
  - Analysis: POST /api/analysis/portfolio-state, position-changes, event-impact, recommendations

- ✅ Task 2.2: Business Logic Layer — 5 analytics modules
  - `portfolio_analyzer.py` — sector/region allocation, risk metrics, concentration risk
  - `position_detector.py` — significant weight change detection, rebalancing identification
  - `event_analyzer.py` — event-to-portfolio impact mapping
  - `recommendation_engine.py` — rule-based optimisation suggestions (priority-ranked)
  - `performance_attribution.py` — security/sector contribution to returns

- ⏸️ Task 2.3: Flink Data Pipeline — Partially done (see Phase 3 RAG notes)

**Backend:**
- Framework: FastAPI 0.115.0 | Python 3.10
- Virtual env: `finsightaivenv/` (excluded from git)
- Running at: http://localhost:8000 | Swagger: http://localhost:8000/docs

---

### Phase 3: AI/LLM Integration ✅ COMPLETED

- ✅ Task 3.1: LLM Integration Setup — OpenAI GPT-4o abstraction layer
  - `backend/services/llm_service.py` — model routing, token/cost tracking, PromptLibrary
  - Model routing: `gpt-4o-mini` (quick tasks) / `gpt-4o` (analysis, recommendations, deep)
  - Streaming support added: `generate_stream()` yields tokens for real-time chat (Task 4.3)
  - Cost tracking: UsageRecord per call, get_usage_stats() for session totals
  - API key: OpenAI (OPENAI_API_KEY in backend/.env)

- ✅ Task 3.2: AI Analysis Modules — 4 AI-powered endpoints
  - `ai_portfolio_explainer.py` → POST /api/analysis/ai/explain-portfolio
  - `ai_change_narrator.py` → POST /api/analysis/ai/narrate-changes
  - `ai_event_analyzer.py` → POST /api/analysis/ai/analyze-event
  - `ai_recommendation_engine.py` → POST /api/analysis/ai/recommendations
  - All combine: PortfolioAnalyzer data + ChromaDB RAG context + GPT-4o

- ✅ Task 3.3: RAG System with ChromaDB — 24,072+ documents across 10 collections
  - ChromaDB running at localhost:8001 (Docker container `FinSight_AI_chromadb`)
  - Collections: ohlcv_data, macro_indicators, sec_filings, market_news, earnings_data,
    analyst_research, technical_indicators, dividend_data, splits_data, volatility_events
  - Batch loaders: `historical_loader.py` (yfinance, FRED), `analyst_research_loader.py`
  - Live pipeline: `finnhub_news_producer.py` → Kafka → Flink → ChromaDB (polls every 2 min)
  - RAG query engine: `backend/rag/query_engine.py` (searches all 10 collections, returns ranked results)
  - Additional APIs: FRED (macroeconomic data), AlphaVantage, Finnhub

- ✅ Task 3.4a: Agentic AI Chat (OpenAI Function Calling) — COMPLETED (2026-06-25)
  - Upgraded `/chat` from static context injection to GPT-4o autonomous tool calling
  - **Before**: every question pre-loaded a fixed portfolio snapshot + 5 RAG docs → GPT-4o answered from that static block
  - **After**: GPT-4o decides which tools it needs, calls them, gets live data, then answers
  - **5 tools exposed to GPT-4o:**
    - `get_portfolio_data` → PortfolioAnalyzer (sector allocation, risk metrics, performance)
    - `get_position_history` → PositionChangeDetector (significant changes in a date range)
    - `search_market_context` → MarketRAGEngine (semantic search across all ChromaDB collections)
    - `get_market_events` → SQL MarketEvents table (Fed decisions, geopolitical events, etc.)
    - `run_risk_analysis` → RecommendationEngine (concentration risk, rebalancing suggestions)
  - **Files changed (5):**
    - `backend/services/ai_tools.py` — NEW: tool schemas + execute_tool() dispatcher
    - `backend/services/ai_chat_service.py` — REWRITTEN: non-streaming tool loop + streaming final answer
    - `backend/routers/analysis.py` — 2-line change: now passes event dicts directly to SSE
    - `frontend/lib/api.ts` — added `onToolCall?` callback + `parsed.tool_call` handler
    - `frontend/app/chat/page.tsx` — ToolChips component, streamingToolCalls state, status indicator
  - **UX**: during tool execution, status bar shows `● CALLING: GET_PORTFOLIO_DATA`; completed tools appear as orange chips inside the assistant bubble
  - RAG pipeline unchanged — `search_market_context` tool calls same MarketRAGEngine
  - **Validated (2026-06-26)**: all 5 tools confirmed firing; multi-tool chaining tested (3 tools in one response); ChromaDB graceful degradation confirmed

- ✅ Task 3.4a Bug Fix: Markdown rendering in chat (2026-06-26)
  - **Problem**: GPT-4o responses containing `**bold**` and `### headers` rendered as raw text
  - **Fix**: replaced plain `{msg.content}` text node in `Bubble` component with `<ReactMarkdown>` + `remark-gfm`
  - **Styling**: headings → orange (`#F5821F`), bold → white, code → dark bg with orange text; matches terminal aesthetic
  - **Files changed**: `frontend/app/chat/page.tsx` (import + Bubble component), `frontend/package.json` (+`react-markdown`, `remark-gfm`)

- ⏸️ Task 3.4b: FastMCP Server — PENDING (expose FinSight as standards-compliant MCP server for Claude Desktop / Cursor)

---

### Phase 4: Frontend Development — IN PROGRESS

- ✅ Task 4.1: Next.js Application Setup — COMPLETED
  - Framework: Next.js 15 + Tailwind CSS v4, TypeScript, monospace Bloomberg-style UI
  - Pages built:
    - `/` — Dashboard: KPI strip, portfolios table, market events, strategy distribution, live clock
    - `/portfolios` — Portfolio list with filtering
    - `/portfolios/[id]` — Portfolio detail: positions, performance, transaction history
    - `/ai-insights` — 3-panel AI analysis (Explanation · Narrative · Recommendations)
    - `/market-events` — Event list with impact levels
    - `/market-events/[id]` — Event detail with affected portfolios
    - `/chat` — AI Chat Interface (Task 4.3, see below)
  - Shared components: Sidebar, StatCard, LoadingSpinner, SectionHeader
  - API layer: `frontend/lib/api.ts` — typed fetch wrappers for all endpoints
  - Running at: http://localhost:3000

- ✅ Task 4.1 (UI): Bloomberg Terminal redesign — applied across all pages
  - Color system: Pure black `#000000` bg · Bloomberg orange `#F5821F` accent · `#E0E0E0` text
  - Monospace font throughout (Consolas/Monaco)
  - Square panel headers (solid orange bar, black text) · no rounded corners
  - High-contrast readable text hierarchy (`#E0E0E0` → `#CCC` → `#AAA` → `#888` → borders only below)
  - Portfolio dropdown fix: shows `#ID — Name · strategy (Customer #N)` for uniqueness

- ✅ Task 4.1 (UI): AI Insights page redesign
  - 3 visually distinct panels: Blue (Explanation) · Amber (Narrative) · Violet (Recommendations)
  - SmartText renderer: parses `**bold**`, `-` bullets, section headers from AI plain text
  - RAG sources collapsible, cost tag per panel, signal badge on recommendations

- ✅ Task 4.2: Real-time WebSocket Updates — COMPLETED (2026-06-21)
  - **Architecture decision**: No Redis needed for single-process dev setup. Used in-memory
    asyncio `ConnectionManager` instead — Redis stays in Phase 6 Task 6.2 where it belongs
    (caching, not pub/sub). WebSocket scales to Redis pub/sub in one swap if needed later.

  - **Backend — 3 files created/modified:**
    - `backend/services/connection_manager.py` — singleton tracks all open WebSocket connections,
      asyncio-safe lock, auto-removes dead connections on failed broadcast
    - `backend/routers/ws.py` — two background tasks auto-started on FastAPI lifespan:
      - **Price simulator**: Gaussian ±0.5% tick on 8 random portfolios every 4s (simulates
        live market data; swap to real Flink output in one line when needed)
      - **Kafka bridge**: daemon thread consumes `market.news` topic → asyncio queue →
        broadcast to all clients; falls back silently if Kafka is unavailable
    - `backend/main.py` — registers `/ws` router, launches both background tasks at startup,
      cancels them cleanly on shutdown via lifespan context manager
  - **New endpoints:**
    - `ws://localhost:8000/ws` — WebSocket connection (all real-time updates)
    - `GET /ws/stats` — returns active connection count (for debugging)

  - **Frontend — 3 files created/modified:**
    - `frontend/hooks/useWebSocket.ts` — reconnecting WebSocket hook: exponential backoff
      (1s → 30s cap), 20s heartbeat ping, stable `onMessage` ref (no re-subscribe on render)
    - `frontend/app/page.tsx` (Dashboard) — subscribes to WS; portfolio rows flash
      **green▲/red▼** on every price tick; Total AUM recalculates live from ticked values;
      Kafka `market_event` messages surface as **amber slide-in toast alerts** (auto-dismiss 8s);
      LIVE/RECONNECTING indicator in top bar reflects actual WS state
    - `frontend/app/portfolios/[id]/page.tsx` — filters WS updates by `portfolio_id`; Total
      Value stat flashes with live Δ% below it; Wifi/WifiOff icon in header shows connection;
      charts and positions table restyled to Bloomberg theme
  - **CSS:** `flash-up`, `flash-down`, `alert-in` keyframe animations added to `globals.css`

- ✅ Task 4.3: AI Chat Interface — COMPLETED (2026-06-21), upgraded to agentic (2026-06-25)
  - New page `/chat` — conversational Q&A with agentic GPT-4o tool calling
  - Backend: `ai_chat_service.py` — non-streaming tool loop + streaming final answer
  - Endpoints: POST /api/analysis/ai/chat (SSE: emits tool_call events + token chunks) · GET /api/analysis/ai/chat/suggested-questions
  - Frontend: streaming chat bubbles, orange tool-call chips show which tools were invoked, status bar shows active tool name during execution
  - Features: portfolio selector, 6 suggested questions, multi-turn history, Enter to send, CLEAR button

---

### Phase 5: Advanced Features — IN PROGRESS

- ✅ Task 5.1: Advanced Risk Analytics — COMPLETED
  - `backend/services/risk_analytics.py` — Historical VaR (95%/99%, 1-day/10-day), parametric VaR, 6 stress tests (2008 Crisis, COVID, Rate Shock, Dot-com Bust, Oil Shock, Stagflation), factor exposure (OLS regression vs SPY/IWD/IWF/MTUM/USMV)
  - `backend/scripts/risk_job.py` — loops all portfolios, saves to `Risk_Metrics` table; runs daily 17:30 ET via AWS EventBridge → SSM → Flink EC2
  - `backend/routers/risk.py` — `GET /api/risk/{id}` (latest), `POST /api/risk/{id}/refresh` (on-demand, ~10-30s), `GET /api/risk/{id}/history?days=30` (trend data)
  - Frontend Risk Analytics tab: VaR grid, 6 stress test cards, factor exposure bar chart + table, VaR trend chart

- ✅ Task 5.2: Alert System — COMPLETED (threshold alerts only; event + AI alerts pending)
  - `backend/services/alert_engine.py` — fires on VaR 95% > 2% (warning), VaR 99% > 3.5% (critical), stress < -25% (warning), stress < -40% (critical), market beta > 1.5 (warning); deduplication: one alert per title per portfolio per day
  - `backend/routers/alerts.py` — `GET /api/alerts`, `GET /api/alerts/unread-count`, `PATCH /api/alerts/{id}/read`, `PATCH /api/alerts/read-all`
  - Frontend: Sidebar bell with red unread badge (polls 60s), slide-out panel; inline alert panel on Risk tab
  - **Pending (5.2 sub-items)**: Event alerts (Market_Events → sector exposure scan) and AI-generated alerts (GPT-4o proactive analysis) — column exists in model, no engine yet

- ✅ Task 5.3: Risk Trend Visualization — COMPLETED (2026-07-03)
  - `GET /api/risk/{id}/history?days=30` — returns chronological array of `{computed_at, price_date, var_95_1d_pct, var_99_1d_pct, stress_worst_pct}` from `Risk_Metrics` table
  - `frontend/lib/api.ts` — `RiskHistoryPoint` type + `getRiskHistory()` function
  - Frontend: VAR TREND · 30-DAY HISTORY LineChart at bottom of Risk tab — two lines (95%/99% VaR as absolute loss %), dashed reference lines at 2% (warning) and 3.5% (critical) thresholds, legend; shows "No trend data yet" placeholder if < 2 data points
  - Verified in browser: chart renders, WARN reference line visible, both VaR lines plotted correctly

- ⏳ Task 5.2b: ChromaDB Data Retention — OPTIONAL (only needed when market_news > ~50K docs)
- ⏳ Task 5.4 (was 5.3 in original plan): Report Generation (PDF/Excel, AI commentary) — PENDING

---

### Phase 6: Infrastructure & Deployment — PENDING
- ⏳ Task 6.1: Dockerization (full docker-compose for all services)
- ⏳ Task 6.2: Redis Caching (portfolio cache, AI response cache)
  - Note: Task 4.2 was implemented without Redis using in-process asyncio.
    Redis in Phase 6 is for HTTP response caching + enabling multi-worker WebSocket scaling.
- ⏳ Task 6.3: CI/CD + Cloud Deployment

---

### DevOps / Repository Hygiene ✅ COMPLETED (2026-06-21)

- ✅ Root `.gitignore` created — excludes `finsightaivenv/`, `__pycache__/`, `.env*`, ChromaDB data dirs,
  `*.jar`, `node_modules/`, `.next/`, large data files (`*.csv`, `*.parquet`), OS/IDE artifacts
- ✅ `backend/.gitignore` updated — explicit `finsightaivenv/` exclusion + ChromaDB dirs
- ✅ `finsightaivenv/` untracked from git — 9,559 venv files removed from tracking via `git rm -r --cached`

---

### API Keys Configured (backend/.env)

| Key | Provider | Used for |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI | GPT-4o analysis, chat streaming, embeddings |
| `FINNHUB_API_KEY` | Finnhub | Live news/trades Kafka producer |
| `FRED_API_KEY` | FRED (St. Louis Fed) | Macroeconomic indicator data |
| `AlphaVantage_API_KEY` | Alpha Vantage | Additional market data |

---

### Overall Progress

| Phase | Status | Notes |
|---|---|---|
| 1 — Data Modeling | ✅ Complete | Manual SQL scripts, no Alembic |
| 2 — Backend API | ✅ Complete | 18+ endpoints, full analytics |
| 3 — AI/LLM | ✅ Complete | GPT-4o, RAG, 4 AI endpoints, agentic chat (3.4a done, 3.4b pending) |
| 4 — Frontend | ✅ Complete | All 3 tasks done (4.1, 4.2, 4.3) |
| 5 — Advanced | 🔄 In Progress | 5.1 ✅ 5.2 ✅ (threshold) 5.3 ✅ · pending: 5.2 event/AI alerts, report gen |
| 6 — Infrastructure | ⏳ Pending | Redis (6.2) for caching + multi-worker WS scaling |

**Current Focus**: Phase 5 in progress. Tasks 5.1 (VaR/stress/factor), 5.2 (threshold alerts), 5.3 (VaR trend chart) complete. Pending: 5.2 event alerts + AI-generated alerts, Task 3.4b (FastMCP Server), Phase 6.

**Known Runtime Issues**:
- ChromaDB container not running → `search_market_context` tool returns "unavailable" (graceful degradation works; start `FinSight_AI_chromadb` docker container to restore RAG)

---

### AWS Infrastructure Fixes (2026-06-29)

Three production bugs found and fixed after EC2 instances failed to auto-start:

**1. Lambda IAM trust policy broken** — When the EventBridge risk job was set up (2026-06-27), the `finsight-ec2-scheduler-role` trust policy was overwritten to `scheduler.amazonaws.com` only, removing `lambda.amazonaws.com`. Lambda could not assume its own execution role → EC2s never started.
- Fix: trust policy now includes both `lambda.amazonaws.com` and `scheduler.amazonaws.com`
- Fix: added `ec2:StartInstances`, `ec2:StopInstances`, `ec2:DescribeInstances`, and CloudWatch Logs permissions to the role

**2. Kafka advertised listener used public Elastic IP** — `KAFKA_EXTERNAL_IP=13.233.21.229` caused Kafka to advertise its public IP to producers. Producers running on the same EC2 cannot reach the instance's own Elastic IP via hairpin NAT reliably (AWS VPC does not guarantee this). Messages silently buffered in the producer but never delivered; Kafka offset stayed frozen despite logs showing "N trades published".
- Fix: `KAFKA_EXTERNAL_IP=172.31.34.55` (private IP) in `/home/ec2-user/FinSight-AI/aws/ec2-flink/.env`
- Flink containers unaffected — they use the internal Docker listener `kafka:29092`

**3. `start_pipeline.sh` used bare `python`** — Script activates the venv but `nohup` launches a subprocess where the venv PATH is not inherited. `python` command not found → both producers silently exited with code 127.
- Fix: changed to `$VENV/bin/python` (explicit venv path) for both producer launch lines
