## Project Status — FinSight AI
**Last Updated**: 2026-07-11 (Fixed and deployed the Overview tab volatility/percentage display bug found while building Task 5.4)

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

- ✅ Task 3.3: RAG System with ChromaDB — fully loaded on both local and AWS
  - ChromaDB running at localhost:8001 (Docker container `FinSight_AI_chromadb`)
  - Live pipeline: `finnhub_news_producer.py` → Kafka → Flink → ChromaDB (polls every 2 min, ~50–150 unique articles/day)
  - RAG query engine: `backend/rag/query_engine.py` (searches all collections, returns ranked results)
  - **Local ChromaDB**: ~24K docs (one-time historical bulk load)
  - **AWS ChromaDB (13.206.225.80)**: ✅ Fully loaded as of 2026-07-06 — 36,595 docs total
    | Collection | Docs | Source |
    |---|---|---|
    | earnings_filings | 17,200 | SEC EDGAR (5yr) |
    | ohlcv_data | 7,991 | yfinance monthly (5yr, 131 tickers) |
    | market_news | ~3,800 | Flink live stream |
    | volatility_events | ~3,400 | Flink live stream |
    | macro_indicators | 3,498 | FRED (40+ series, 2019–present) |
    | dividends_data | 2,226 | yfinance (5yr) |
    | fed_communications | 729 | FRED Fed balance sheet + rates |
    | earnings_data | 400 | yfinance quarterly |
    | analyst_recommendations | 100 | yfinance consensus |
    | splits_data | 24 | yfinance (5yr) |
  - **Reddit sentiment**: good-to-have, live stream only via PRAW (no historical), not yet implemented
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

- ✅ Task 3.4b: FastMCP Server — COMPLETED (2026-07-06)
  - `backend/mcp_server.py` — FastMCP server with 8 tools wired to live SQL Server + ChromaDB
  - **8 tools**: `list_portfolios`, `get_portfolio_summary`, `get_portfolio_positions`, `get_portfolio_risk`, `get_portfolio_alerts`, `search_market_context`, `get_market_events`, `refresh_portfolio_risk`
  - Two transport modes: `stdio` (Claude Desktop), `--transport sse --port 8002` (HTTP/Cursor)
  - `backend/claude_desktop_config.json` — ready-to-use config; deployed to `%APPDATA%\Claude\claude_desktop_config.json`
  - Restart Claude Desktop to activate; FinSight tools appear in Claude's tool panel

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

- ✅ Task 5.2: Alert System — COMPLETED, all three alert types (2026-07-10/11)
  - `backend/services/alert_engine.py` — threshold alerts fire on VaR 95% > 2% (warning), VaR 99% > 3.5% (critical), stress < -25% (warning), stress < -40% (critical), market beta > 1.5 (warning); dedup: one alert per title per portfolio per day
  - **Event alerts** (`generate_event_alerts`) — bulk sector×region exposure scan across all `Market_Events`, AND semantics (not OR — an earlier version matched ~90% of every portfolio on any US-tagged event, since `event_analyzer.py`'s `_parse_json_field` has been silently broken since it shipped: `affected_sectors`/`affected_regions` are stored as comma-separated strings, not JSON, so it always returned `[]`). Dedup once-per-event-per-portfolio (not per-day) since events are static, not a live feed. 290 alerts live in production.
  - **AI-generated alerts** (`generate_ai_alert_for_portfolio`) — GPT-4o-mini reviews top holdings + RAG context daily, flags only a specific dated catalyst (never bare concentration — every portfolio here is concentrated by construction with only 4-5 positions, so an early version flagged 48/50 portfolios on generic commentary; tightened prompt brought it to a defensible ~4-8%). Dedup once per portfolio per day, checked before the LLM call. ~$0.0075/day for 50 portfolios.
  - Both wired into `risk_job.py`'s daily run alongside threshold alerts.
  - `backend/routers/alerts.py` — `GET /api/alerts`, `GET /api/alerts/unread-count`, `PATCH /api/alerts/{id}/read`, `PATCH /api/alerts/read-all`
  - Frontend: Sidebar bell with red unread badge (polls 60s), slide-out panel; inline alert panel on Risk tab — no frontend changes needed for the new alert types (`alert_type` was already scoped as `"threshold" | "event" | "ai"` in the TS type, styling keys off `severity` not `alert_type`)

- ✅ Task 5.3: Risk Trend Visualization — COMPLETED (2026-07-03)
  - `GET /api/risk/{id}/history?days=30` — returns chronological array of `{computed_at, price_date, var_95_1d_pct, var_99_1d_pct, stress_worst_pct}` from `Risk_Metrics` table
  - `frontend/lib/api.ts` — `RiskHistoryPoint` type + `getRiskHistory()` function
  - Frontend: VAR TREND · 30-DAY HISTORY LineChart at bottom of Risk tab — two lines (95%/99% VaR as absolute loss %), dashed reference lines at 2% (warning) and 3.5% (critical) thresholds, legend; shows "No trend data yet" placeholder if < 2 data points
  - Verified in browser: chart renders, WARN reference line visible, both VaR lines plotted correctly

- ⏳ Task 5.2b: ChromaDB Data Retention — OPTIONAL (only needed when market_news > ~50K docs)
- ✅ Task 5.4 (was 5.3 in original plan): Report Generation — COMPLETE (2026-07-11)
  - `backend/services/report_generator.py` — packages already-computed data (portfolio overview, latest `Risk_Metrics` row, top 15 positions, last 8 alerts) plus a fresh AI commentary paragraph (`AIPortfolioExplainer.quick_summary()`, gpt-4o-mini) into a PDF via `reportlab` (pure Python, no system deps — deliberate given the mcp/Starlette dependency conflict hit earlier this session)
  - `GET /api/portfolios/{id}/report` — same `require_portfolio_access` auth as every other portfolio route, not cached (deliberate, infrequent on-demand action)
  - Frontend: "EXPORT REPORT" button next to "AI INSIGHTS" on the portfolio detail page, downloads via blob
  - PDF format only — Excel deferred (lower priority, revisit if there's demand for raw-numbers-in-a-spreadsheet use case)
  - Found while building this, fixed separately 2026-07-11: the portfolio Overview tab's "VOLATILITY" stat showed a value ~100x too small — see the dedicated bug-fix entry below.

---

### Phase 6: Infrastructure & Deployment — IN PROGRESS
- ⏳ Task 6.1: Dockerization (full docker-compose for all services)
- ✅ Task 6.2: Redis Caching — COMPLETE (2026-07-11), deployed as Valkey
  - Self-hosted on the ChromaDB EC2 (Redis unavailable in AL2023's default repos; Valkey — the actively-maintained Redis-compatible fork — was), binds `127.0.0.1` only
  - `backend/services/cache.py` — reusable `get_or_set()`/`invalidate()`, graceful fallback if unreachable
  - Cached: unread alert count (60s, invalidated on mark-read), portfolio summary/positions (5min), risk metrics (30min — shorter than the originally planned 24h, since `risk_job.py` runs on a different EC2 with no safe way to invalidate across boxes)
  - Not yet cached: AI chat responses, yfinance fetches (lower priority, deferred)
  - Note: Task 4.2 was implemented without Redis using in-process asyncio — that's unrelated to this caching layer.
- ✅ Task 6.3 (partial — cloud deploy done, CI/CD still manual): FastAPI backend deployed 2026-07-09
  - Reused the always-on ChromaDB EC2 (`13.206.225.80`) — $0 extra EC2 cost
  - Domain: `fin-sightai.space` (GoDaddy), `api.fin-sightai.space` → backend, `www.fin-sightai.space` → Vercel frontend
  - `nginx` reverse proxy + Certbot (Let's Encrypt, auto-renewing via a hand-rolled systemd timer — AL2023's certbot package doesn't ship one despite claiming to)
  - `systemd` service (`finsight-backend.service`) — auto-restart on crash/reboot, unlike the `nohup` pattern used for the MCP server
  - Deploy method: `git sparse-checkout` (backend/ only) via a read-only GitHub Deploy Key, manual `git pull` + `systemctl restart` for updates — real CI/CD (GitHub Actions) still not built
  - Full writeup, all bugs found/fixed, and verification steps: see `CLOUD_MIGRATION.md`

- ✅ Task 6.4: JWT Auth + Multi-Tenant Portfolio Access — COMPLETE, deployed to production (2026-07-11)
  - **Data model**: `Users` table + `Portfolios.manager_id` FK, via a new additive `db_migration_auth.sql` (not by re-running `db_migration_fix.sql` — that deletes/recreates `Portfolios`, which would violate the FK from `Alerts`/`Risk_Metrics` and wipe the accumulated alert/risk history built up in Tasks 5.1/5.2). 5 demo managers (~10 portfolios each) + 1 admin — see `AUTH.md` for credentials.
  - **Backend**: `backend/auth.py` (bcrypt password hashing, PyJWT access+refresh tokens in httpOnly cookies, `get_current_user`/`require_portfolio_access`/`check_portfolio_access`/`scope_portfolio_query`), `routers/auth.py` (login/refresh/logout/me), all 6 routers retrofitted (`portfolios`, `risk`, `alerts`, `analysis`, `market_events`, `securities`). CORS switched from `allow_origins=["*"]` to an explicit list + `allow_credentials=True`.
  - **Frontend**: `/login` page, `AuthContext`, `apiFetch` sends `credentials: 'include'`, Sidebar shows logged-in manager + logout — no changes needed to the 4 pages that list portfolios, since the backend scoping does the work.
  - **The hard edge (closed)**: `ai_tools.py`'s `execute_tool()` now takes `current_user` and checks ownership before any portfolio-scoped tool call, so the AI chat can't be used to bypass REST-level scoping via tool-calling. `mcp_server.py` resolves one identity per process from a long-lived `FINSIGHT_MCP_TOKEN` (minted via `scripts/mint_mcp_token.py`) and refuses to start without one. `/ws` authenticates at the WebSocket handshake and filters every price tick to the connection's accessible portfolios.
  - **Real bugs found while building this**: `EventImpactAnalyzer` treats an empty portfolio list as "no filter → show everything" (guarded in the two analysis endpoints that call it); hardcoded `secure=True` on cookies silently broke local HTTP testing (now `COOKIE_SECURE`, a setting); Next.js 16's `allowedDevOrigins` protection blocked the HMR websocket between `127.0.0.1`/`localhost`, causing a silent, error-free blank screen (not a code bug — just means local dev must use `localhost:3000`).
  - **Deployed and verified**: `api.fin-sightai.space` now enforces auth (`curl` without a cookie returns `401 {"detail":"Not authenticated"}` on `/api/portfolios`); production login confirmed working end-to-end in browser.

- ✅ Bug fix: Overview tab volatility/percentage display — COMPLETE, deployed (2026-07-11)
  - Root cause: `Portfolio_Performance.volatility`/`ytd_return` and `Positions.weight` are stored as decimal fractions (e.g. `0.1240` = 12.40%), but several frontend display sites called `.toFixed()` directly on them without multiplying by 100 first — values rendered ~100x too small (e.g. "0.1%" instead of "12.4%"). Confirmed via direct DB query on portfolio 1 (`volatility=0.1240, ytd_return=0.1340`) and cross-checked against the PDF report, which computed the same fields correctly.
  - Fixed 5 spots in `frontend/app/portfolios/[id]/page.tsx` (YTD Return `pct()` helper, VOLATILITY stat, sector allocation legend, positions-tab weight column) and `frontend/app/market-events/[id]/page.tsx` (`total_weight_change` — defensive fix; its backing table `Position_Changes_Log` has 0 rows currently, so not yet visibly wrong, but same bug pattern).
  - Swept the rest of the frontend for the same pattern and confirmed all other `.toFixed()...%` sites (VaR panel, VaR trend chart, stress test table, factor exposure R², live WebSocket price-tick `changePct`) are already correctly scaled — those fields are pre-multiplied by 100 in the backend (`risk_analytics.py`) or generated in percentage scale by the WS price simulator, so they were deliberately left untouched.
  - Verified in a real browser session both locally and on production (`https://www.fin-sightai.space`, logged in as Sarah Chen, portfolio 1): YTD RETURN `+13.40%`, VOLATILITY `12.4%`, sector allocation `55.8%/13.8%/11.5%/11.2%`, position weights correct.
  - Frontend-only change — no backend/EC2 deploy needed; shipped via Vercel's git auto-deploy on push to `adarsh` (commit `477794c`).

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
| 3 — AI/LLM | ✅ Complete | GPT-4o, RAG, agentic chat (3.4a), FastMCP server (3.4b) |
| 4 — Frontend | ✅ Complete | All 3 tasks done (4.1, 4.2, 4.3) |
| 5 — Advanced | ✅ Complete | 5.1 ✅ 5.2 ✅ (all 3 alert types) 5.3 ✅ 5.4 ✅ (PDF only, Excel deferred) |
| 6 — Infrastructure | 🔄 In Progress | Backend cloud deploy ✅ (6.3 partial) · 6.2 Redis/Valkey caching ✅ · 6.4 JWT auth ✅ · Dockerization, real CI/CD still pending |

**Current Focus**: All of Phase 5 is now complete and deployed, including Task 5.4 (PDF report generation) as of 2026-07-11. The Overview tab volatility/percentage display bug found while building the report is now fixed and deployed (see dedicated entry above). The ChromaDB EC2 runs four services together (ChromaDB, backend, MCP server, Valkey) after being resized t3.micro → t3.small to fit them; the MCP server was also relocated there from the market-hours-only Flink EC2. Next: retire the stale pre-auth MCP server still sitting on the Flink EC2, real CI/CD, Dockerization.

**Known Runtime Issues**:
- ChromaDB container not running locally → `search_market_context` returns "unavailable" (graceful degradation works; start `FinSight_AI_chromadb` docker container to restore RAG)

**Confirmed (2026-07-06)**: Even when the FastAPI backend runs locally (`http://localhost:8000`), it points at the AWS ChromaDB instance — `CHROMA_HOST=13.206.225.80` in `backend/.env` — not a local container. `volatility_detector_job` on the Flink EC2 is confirmed running daily; its `volatility_events` collection is confirmed growing in real time.

---

### ⚠️ Important Pending Item: AI Chat gives stale/wrong answers for "recent" price questions

**Found**: 2026-07-06 — user asked "how has Microsoft stock performed in the last few months" and got June–September **2023** OHLCV data back, presented as if current, even though today's date is 2026-07-06.

**Root cause (confirmed by reading code, not guessed)**:
1. **No live quote tool exists.** The 5 tools in `backend/services/ai_tools.py` (`get_portfolio_data`, `get_position_history`, `search_market_context`, `get_market_events`, `run_risk_analysis`) do not include any live/current stock price lookup. The only price-adjacent tool is `search_market_context`, which is pure ChromaDB semantic search.
2. **`search_market_context` has zero recency awareness.** `backend/rag/query_engine.py:23-54` (`retrieve_context()`) ranks purely by cosine similarity (`relevance_score`) — no date filter, no recency boost. A query like "last few months" just matches whatever embeds closest, regardless of actual date.
3. **The static collections (`ohlcv_data`, `market_news`, etc.) were bulk-loaded once** via `historical_loader.py` on 2025-06-18 (5 years of history ending at that run's `datetime.now()`) and are never incrementally refreshed. Even the newest static documents cap out ~mid-2025 — already stale vs. today.
4. **`volatility_events` (written live daily by `volatility_detector_job`) is the one collection that IS fresh** — confirmed growing daily on the AWS ChromaDB instance — but it has no ranking advantage over the older bulk static docs in step 2's pure-cosine-similarity search, so fresher volatility data can easily lose to older, semantically-closer-sounding static docs and never surface in the answer.

**Status (2026-07-07): ✅ FIXED AND VERIFIED** (items 1–3 below). Implemented:
1. **Inject today's date into the system prompt** — `ai_chat_service.py:78` now sends `f"{_SYSTEM_PROMPT}\n\nToday's date is {date.today().isoformat()}. The user is asking about portfolio #{portfolio_id}."`
2. **Live quote tool** — `get_current_quote(ticker)` added to `ai_tools.py` using `yfinance.Ticker(ticker).fast_info` (sub-second, not the slower `.history()` pull). Added to `TOOL_DEFINITIONS` + `execute_tool()` + system prompt tool guide, with a short in-process cache (~30s TTL, placeholder for the Phase 6 Redis line) and a graceful `{"error": ...}` fallback.
3. **Recency-aware ranking in `retrieve_context()`** (`query_engine.py`) — blends `relevance_score` with a recency-decay term (180-day half-life, 30% weight) from each doc's date metadata. While implementing, found the date-key lookup only checked `date`/`published_at`/`period` — `volatility_events` actually uses `event_date`/`detected_at` and `earnings_filings` uses `filed_date`, so those collections were silently getting zero recency credit. Widened the key list to cover all of them.

**Verified end-to-end (2026-07-07)**: started the FastAPI backend locally, hit `POST /api/analysis/ai/chat` with *"What's the current price of AAPL right now, and how has the market been recently in terms of volatility?"* (portfolio_id=1). Tool calls fired in order: `get_current_quote` → `search_market_context`. Answer correctly returned a real live AAPL price ($313.86, +0.37%) and cited genuinely recent 2026 volatility events by date (Visa 2026-07-06, Visa 2026-07-01, Mastercard 2026-06-24) — not 2023 data misrepresented as current, which was the original bug.

Also caught one unrelated issue while restarting the backend for this test: `main.py`'s DB startup check has no cold-start retry (unlike `risk_job.py`'s `wait_for_db()`) — a paused Azure SQL instance makes the whole app fail to boot on the first attempt. Not fixed yet, noted here for later.

**Deferred (not in this round)**: scheduling periodic re-runs of `historical_loader.py` to refresh the static ChromaDB collections themselves — bigger lift (new EventBridge schedule, real data volume). Items 1–3 above fix the "presented as current" symptom without needing this yet; revisit as a separate task later.

**Files changed**: `backend/services/ai_chat_service.py`, `backend/services/ai_tools.py`, `backend/rag/query_engine.py`.

---

### ⚠️ Pending Item: Daily Securities Price Update Job (SQL Server)

**Found**: 2026-07-06, while investigating the stale-chat issue above.

**Problem**: `Securities.current_price` (`backend/models.py:64`) and `Positions.market_value` were populated once during the original synthetic data generation and are **never refreshed**. There is no daily job — `backend/scripts/` only contains `risk_job.py` (writes to `Risk_Metrics`, doesn't touch `Securities`/`Positions`). So portfolio values, position market values, and anything `get_portfolio_data` returns to the AI chat are all frozen at whatever they were when the DB was seeded — a separate staleness problem from the ChromaDB/RAG one above, but with the same root symptom (answers look current but aren't).

**Status (2026-07-07): ✅ SCRIPT BUILT AND VERIFIED** (EventBridge scheduling not yet wired — see below). Built `backend/scripts/price_update_job.py`, same shape as `risk_job.py` (logging bookends, `wait_for_db()`, per-item try/except).

**Two real bugs found and fixed while building it, both against live production data**:
1. **`Security.current_price` wasn't mapped in the ORM at all.** The real DB column exists (`DECIMAL(18,4)`, NOT NULL — memory already flagged this gap) but `models.py`'s `Security` class never declared it, so `db.query(Security)....update(...)` failed with `CompileError: Unconsumed column names`. Fixed by adding `current_price = Column(DECIMAL(18, 4))` to the model.
2. **`Positions.weight` overflowed on every single portfolio.** The real column is `DECIMAL(5,4)` (max 9.9999) storing a *fraction* (0.28 = 28%), not `DECIMAL(5,2)` as `models.py` claims, and not a 0–100 percentage. Computing `market_value / total_value * 100` overflowed immediately. Fixed by storing the raw fraction (`market_value / total_value`, no ×100) plus a defensive clamp to ±9.9999.

**Verified end-to-end against production Azure SQL (2026-07-07)**: ran the job for real. Results:
- `Securities.current_price`: 135/135 updated (e.g. AAPL $195.50 → $313.81, matching the real live price fetched earlier in this session)
- `Portfolios`: 50/50 rolled up successfully
- Portfolio 32's position weights sum to 0.9495 — reconciles almost exactly with its cash allocation (`$200M / $3.97B ≈ 5.04%`), confirming the math is internally consistent

**Status update (2026-07-08): scheduled and live.** Explored moving this to AWS Lambda first (built a full container-image pipeline — Dockerfile, ECR, Lambda, IAM role) but hit a real architectural blocker: Azure SQL's firewall is IP-allowlist based, and Lambda without VPC config has no static egress IP (`Client with IP address '13.200.222.100' is not allowed to access the server`). Fixing that needs a NAT Gateway (~$32+/mo) or NAT instance (~$3-4/mo), which defeats the point of avoiding an always-on EC2 — especially since `finsight-flink`'s IP is already allow-listed and already running at $0 marginal cost. Decided to deploy this the same way as `risk_job.py` instead: pushed to EC2, created `finsight-daily-price-update` EventBridge schedule (16:00 ET Mon-Fri, 10 min before `risk_job.py`), verified via a manual SSM trigger before trusting the schedule (learned this lesson from `risk_job.py`'s 8-day silent failure). Full writeup in `CLOUD_MIGRATION.md`.

**Sequencing note (confirmed)**: `risk_analytics.py` pulls its own historical yfinance series for VaR/stress math, so it doesn't strictly *depend* on fresh `Positions.market_value` — but `get_portfolio_data` (`portfolio_analyzer.py:48`, reads `portfolio.total_value` directly from the stored column) and the dashboard both do. Running price-update first just keeps everything consistent, it isn't load-bearing for risk math itself.

**Deferred/optional**: daily `Portfolio_Performance` snapshot row from this job — separate nice-to-have, not required for the staleness fix.

**Files changed**: `backend/scripts/price_update_job.py` (new), `backend/models.py` (`Security.current_price` added).

---

### Where Everything Lives (Deployment Map)

> Goal: everything eventually moves off local via CI/CD (Phase 6). Until then, this table shows current state.

| Component | Where | Status | Notes |
|---|---|---|---|
| **Azure SQL Server** | Azure cloud (free tier) | ✅ Live | FinSight_AI DB — 50 portfolios, 135 securities, full data. Auto-pauses after 1hr inactivity (~1min cold start) |
| **AWS ChromaDB EC2** | EC2 `13.206.225.80` (t3.micro) | ✅ Live | 36,595 docs across 10 collections. Flink writes to it live. |
| **AWS Flink EC2** | EC2 `13.233.21.229` (t3.medium) | ✅ Live | Kafka + Flink + Finnhub producer. EventBridge triggers daily risk job at 17:30 ET Mon–Fri. |
| **Vercel (Frontend)** | Vercel cloud | ✅ Live | `https://frontend-sandy-seven-21.vercel.app` — deployed from git |
| **FastAPI Backend** | Local only | ⚠️ Local | `http://localhost:8000` — needs EC2/cloud deployment via CI/CD |
| **MCP Server** | AWS ChromaDB EC2 (SSE), moved 2026-07-11 | ✅ Live | `http://13.206.225.80:8002/sse` — always-on now (was on the market-hours-only Flink EC2 before). Isolated `mcpvenv`, own systemd service (`finsight-mcp`), bound to the admin identity. |
| **Local ChromaDB** | Shut down | ✅ Retired | Docker container no longer needed — all RAG uses AWS ChromaDB |
| **Local SQL Server** | Shut down | ✅ Retired | Docker container no longer needed — all DB uses Azure SQL |
| **Local Next.js** | Local only | ⚠️ Local | `http://localhost:3000` — Vercel is the production frontend |

**What still needs to move off local (Phase 6 scope):**
- FastAPI backend → EC2 or ECS (behind ALB + HTTPS)
- CI/CD pipeline → GitHub Actions: push to `main` → deploy backend + restart services

**Docker Desktop: shut down — no local containers needed anymore**

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
