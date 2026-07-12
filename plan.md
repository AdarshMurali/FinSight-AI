# Intelligent Financial Research Agent - Development Plan

## Application Name Suggestions
1. **FinSight AI** (Recommended) - Conveys financial intelligence and insight
2. **Prism Portfolio Intelligence** - Suggests multi-dimensional analysis
3. **Quantum Portfolio Advisor** - Modern, institutional feel
4. **Sentinel Financial Intelligence** - Guardian/monitoring aspect
5. **HedgeScope AI** - Direct appeal to hedge funds

---

## Project Overview
An AI-powered financial research agent for hedge funds and institutional clients that:
- Analyzes portfolio positions and performance
- Explains portfolio states and changes
- Detects and analyzes impact of sectoral, policy, and global events
- Provides actionable recommendations for portfolio optimization
- Delivers real-time monitoring and alerts

**Target Users**: Hedge funds, institutional investors, portfolio managers

---

## Tech Stack
- **Backend**: Python (FastAPI/Flask), Apache Flink (streaming)
- **Frontend**: Next.js (React)
- **Database**: SQL Server (structured data), ChromaDB (vector embeddings)
- **Cache**: Redis
- **AI/LLM**: OpenAI SDK (GPT-4/Claude 3.5/4)
- **Infrastructure**: Docker, MCP (Model Context Protocol)
- **Additional**: LangChain/LlamaIndex (orchestration), Celery (async tasks)

---

## Development Phases

### **PHASE 1: Data Modeling & Synthetic Data Generation** ⭐ START HERE
**Duration**: 1-2 weeks | **Status**: Planning

#### Task 1.1: Database Schema Design
**Goal**: Design comprehensive SQL Server schema for financial data

**Tables to Create**:
1. **Customers/Institutions**
   - customer_id (PK)
   - customer_name
   - institution_type (hedge_fund, asset_manager, family_office)
   - aum (assets under management)
   - risk_profile
   - created_at, updated_at

2. **Portfolios**
   - portfolio_id (PK)
   - customer_id (FK)
   - portfolio_name
   - total_value
   - cash_balance
   - currency
   - inception_date
   - strategy_type (long_short, market_neutral, event_driven, etc.)

3. **Positions**
   - position_id (PK)
   - portfolio_id (FK)
   - security_id (FK)
   - quantity
   - avg_cost_basis
   - current_price
   - market_value
   - weight (% of portfolio)
   - position_type (long, short)
   - opened_date
   - last_updated

4. **Securities**
   - security_id (PK)
   - ticker_symbol
   - security_name
   - security_type (stock, bond, option, future, etf)
   - sector
   - industry
   -country
   - exchange
   - currency

5. **Transactions**
   - transaction_id (PK)
   - portfolio_id (FK)
   - security_id (FK)
   - transaction_type (buy, sell, dividend, split)
   - quantity
   - price
   - transaction_date
   - fees
   - notes

6. **Portfolio_Performance**
   - performance_id (PK)
   - portfolio_id (FK)
   - as_of_date
   - total_value
   - daily_return
   - mtd_return
   - ytd_return
   - volatility
   - sharpe_ratio
   - max_drawdown

7. **Market_Events**
   - event_id (PK)
   - event_date
   - event_type (policy, geopolitical, sectoral, economic)
   - event_title
   - event_description
   - affected_sectors (JSON array)
   - affected_regions (JSON array)
   - impact_level (high, medium, low)
   - source_url

8. **Position_Changes_Log**
   - log_id (PK)
   - portfolio_id (FK)
   - security_id (FK)
   - change_date
   - change_type (rebalance, risk_adjustment, market_move)
   - old_weight
   - new_weight
   - reason
   - related_event_id (FK, nullable)

**Deliverables**:
- SQL schema scripts (CREATE TABLE statements)
- Entity-Relationship Diagram (ERD)
- Data dictionary documentation

---

#### Task 1.2: Synthetic Data Generation Scripts
**Goal**: Create realistic synthetic portfolio data for testing

**Data Generation Requirements**:
1. **10-20 institutional customers** with varying AUM ($100M - $10B)
2. **50-100 portfolios** with different strategies
3. **500-1000 securities** across:
   - US equities (S&P 500, NASDAQ)
   - International equities (FTSE, DAX, Nikkei)
   - Fixed income (Treasury, Corporate bonds)
   - Alternatives (commodities, currencies)
   - Sectors: Technology, Healthcare, Finance, Energy, Consumer, Industrials, etc.

4. **Position data**:
   - 20-50 positions per portfolio
   - Mix of long/short positions
   - Realistic sector allocations
   - Correlation patterns

5. **Historical transactions** (6-12 months of history)

6. **Market events** (20-30 events):
   - Fed rate decisions
   - Geopolitical events (Russia-Ukraine, Middle East tensions)
   - Sector-specific (tech regulation, oil price shocks)
   - Policy changes (tax reform, trade policies)

7. **Performance metrics** (daily snapshots for 1 year)

**Tools/Libraries**:
- `Faker` for realistic names and data
- `numpy`/`pandas` for numerical data
- `yfinance` for real market prices (reference)
- Custom algorithms for correlated returns

**Python Scripts to Create**:
- `generate_customers.py`
- `generate_securities.py`
- `generate_portfolios.py`
- `generate_positions.py`
- `generate_transactions.py`
- `generate_market_events.py`
- `generate_performance_metrics.py`
- `main_data_generator.py` (orchestrator)

**Deliverables**:
- Python scripts for data generation
- Populated SQL Server database
- Data validation reports (statistics, distributions)

---

#### Task 1.3: Database Setup & Migration Framework
**Goal**: Set up SQL Server connection and migration management

**Actions**:
1. Create database connection utilities (`db_config.py`)
2. Set up migration framework (Alembic or raw SQL scripts)
3. Create seed data loading scripts
4. Implement data validation queries
5. Set up database backup/restore procedures

**Deliverables**:
- Database connection module
- Migration scripts versioned (V1_initial_schema.sql, etc.)
- Seed data loader
- README for database setup

---

### **PHASE 2: Backend API Development**
**Duration**: 2-3 weeks

#### Task 2.1: Core API Framework
**Goal**: Build RESTful API with FastAPI

**Endpoints to Create**:

**Portfolio Management**:
- `GET /api/portfolios` - List all portfolios
- `GET /api/portfolios/{id}` - Get portfolio details
- `GET /api/portfolios/{id}/positions` - Get current positions
- `GET /api/portfolios/{id}/performance` - Get performance metrics
- `GET /api/portfolios/{id}/history` - Get historical transactions

**Analysis**:
- `POST /api/analysis/portfolio-state` - Analyze current portfolio state
- `POST /api/analysis/position-changes` - Detect significant position changes
- `POST /api/analysis/event-impact` - Analyze event impact on portfolio
- `POST /api/analysis/recommendations` - Get optimization suggestions

**Market Data**:
- `GET /api/securities` - List securities
- `GET /api/securities/{id}` - Security details
- `GET /api/market-events` - List market events
- `GET /api/market-events/{id}/affected-portfolios` - Get affected portfolios

**Deliverables**:
- FastAPI application structure
- CRUD operations for all entities
- Request/response models (Pydantic)
- API documentation (Swagger/OpenAPI)

---

#### Task 2.2: Business Logic Layer
**Goal**: Implement portfolio analytics and calculations

**Modules to Create**:

1. **Portfolio Analyzer** (`portfolio_analyzer.py`)
   - Calculate portfolio metrics (returns, volatility, Sharpe ratio)
   - Sector/region allocation analysis
   - Risk exposure calculations
   - Concentration risk detection

2. **Position Change Detector** (`position_detector.py`)
   - Detect significant weight changes (>5% threshold)
   - Identify rebalancing events
   - Track entry/exit positions
   - Compare against historical patterns

3. **Event Impact Analyzer** (`event_analyzer.py`)
   - Map events to affected securities/sectors
   - Calculate event-driven performance attribution
   - Measure portfolio beta to events
   - Generate impact reports

4. **Performance Attribution** (`performance_attribution.py`)
   - Security selection contribution
   - Sector allocation contribution
   - Market timing effects
   - Risk-adjusted returns

**Deliverables**:
- Business logic modules
- Unit tests (pytest)
- Performance benchmarks

---

#### Task 2.3: Data Pipeline with Apache Flink
**Goal**: Set up real-time streaming for market data and events

**Flink Jobs**:
1. **Market Data Ingestion**
   - Stream price updates
   - Calculate real-time position values
   - Update portfolio metrics

2. **Event Stream Processing**
   - Ingest news/events from external sources
   - Classify and tag events
   - Trigger impact analysis

3. **Anomaly Detection**
   - Detect unusual position changes
   - Alert on threshold breaches
   - Identify correlation breaks

**Deliverables**:
- Flink job definitions
- Stream processing pipeline
- Kafka/RabbitMQ integration (if needed)

---

### **PHASE 3: AI/LLM Integration**
**Duration**: 2-3 weeks

#### Task 3.1: LLM Integration Setup
**Goal**: Set up OpenAI SDK with multi-model support

**Implementation**:
1. Create LLM abstraction layer supporting:
   - OpenAI GPT-4/GPT-4-turbo
   - Anthropic Claude 3.5 Sonnet/Opus/Claude 4
   - Model selection based on cost/complexity

2. Implement token management and cost tracking

3. Set up prompt templates library

**Configuration**:
```python
LLM_CONFIG = {
    "quick_analysis": "gpt-4-turbo",  # Fast, lower cost
    "deep_research": "claude-opus-4",  # Deep reasoning
    "summarization": "gpt-4",          # Balance
    "recommendations": "claude-sonnet-4.5"  # Strategic thinking
}
```

**Deliverables**:
- LLM service abstraction (`llm_service.py`)
- Model router/selector
- Cost tracking module
- Prompt template manager

---

#### Task 3.2: AI Analysis Modules
**Goal**: Build AI-powered analysis capabilities

**Modules**:

1. **Portfolio State Explainer** (`ai_portfolio_explainer.py`)
   - Input: Portfolio data, market context
   - Output: Natural language explanation of portfolio state
   - Prompt: "Explain why this portfolio has [X% tech exposure, Y% returns, etc.]"

2. **Change Detector & Narrator** (`ai_change_narrator.py`)
   - Input: Position changes, market events
   - Output: Causality analysis and narrative
   - Example: "Technology sector weight decreased 8% following Fed rate hike announcement, likely due to risk-off sentiment..."

3. **Market Event Analyzer** (`ai_event_analyzer.py`)
   - Input: Event data, affected securities
   - Output: Impact assessment and exposure analysis
   - Considers: Direct holdings, sector correlations, geographic exposure
   - ⚠️ **Pending (found 2026-07-12)**: built and working end-to-end (`POST /api/analysis/ai/analyze-event`), but never wired to the frontend — `aiAnalyzeEvent()` exists in `frontend/lib/api.ts` and is called from nowhere. Revisit: add a "Deep AI Analysis" button on the market-events detail page.

4. **Recommendation Engine** (`ai_recommendation_engine.py`)
   - Input: Portfolio state, risk profile, market conditions
   - Output: Actionable rebalancing suggestions
   - Considers: Risk limits, transaction costs, tax implications

**Deliverables**:
- AI analysis modules
- Prompt engineering templates
- Response parsing and validation
- Integration tests

---

#### Task 3.3: RAG System with ChromaDB
**Goal**: Set up retrieval-augmented generation for enhanced analysis

**Implementation**:

1. **Document Ingestion Pipeline**
   - Ingest market reports, research papers, news articles
   - Chunk and embed documents
   - Store in ChromaDB with metadata

2. **Semantic Search**
   - Query relevant context for portfolio analysis
   - Find similar historical events
   - Retrieve sector-specific insights

3. **RAG Integration**
   - Combine retrieved context with LLM prompts
   - Enhance explanations with factual grounding
   - Cite sources in responses

**Document Types**:
- Fed meeting minutes
- Earnings reports
- Sector research reports
- Geopolitical analysis
- Historical event summaries

**Deliverables**:
- ChromaDB setup and configuration
- Document ingestion pipeline
- Embedding generation (OpenAI embeddings)
- RAG query module
- Document management API

---

#### Task 3.4: MCP Integration — Agentic AI + MCP Server
**Goal**: Two complementary MCP additions that genuinely upgrade the AI layer and showcase
the latest AI engineering patterns on the resume.

> **Background — three different "MCP" contexts in this project:**
> - RAG.md mentions *consuming* external MCP servers (Yahoo Finance, FRED MCP) — we are the client
> - Task 3.4a below is *building* an MCP server — we are the server exposing our tools
> - Task 3.4b upgrades AI Chat using OpenAI function calling — same agentic concept, no MCP transport needed
> All three are conceptually related but distinct in direction and implementation.

---

#### Task 3.4a: Agentic AI Chat (OpenAI Function Calling)
**Goal**: Upgrade `/chat` from static context injection to true agentic tool calling

**The Problem with Current AI Chat**:
The current `/chat` endpoint pre-loads a fixed portfolio snapshot + RAG context into every
prompt. The LLM answers from that static block. If the user's question needs data outside
that snapshot, quality degrades.

**The Agentic Upgrade**:
GPT-4o autonomously decides which tools to call based on the question.
The LLM drives data retrieval — it fetches exactly what it needs, nothing more.

```
Before: User question → [pre-loaded data block] → GPT-4o → answer
After:  User question → GPT-4o thinks → calls tool(s) → gets live data → answer
```

**Tools to expose to GPT-4o**:
| Tool | Calls | When LLM invokes it |
|---|---|---|
| `get_portfolio_data` | PortfolioAnalyzer | "What is my sector allocation?" |
| `get_position_history` | PositionChangeDetector | "What changed in October?" |
| `search_market_context` | MarketRAGEngine (ChromaDB) | "Why did tech drop?" |
| `get_market_events` | SQL MarketEvents table | "What events affected energy?" |
| `run_risk_analysis` | RecommendationEngine | "What are my biggest risks?" |

**Implementation**:
- Modify `backend/services/ai_chat_service.py`
- Pass `tools=[...]` to OpenAI API call
- Handle `tool_calls` in response, execute the right service, feed results back
- Continue streaming after tool results are injected
- No new pip dependencies — function calling is built into `openai` SDK

**Deliverables**:
- Updated `ai_chat_service.py` with tool definitions and tool execution loop
- `backend/services/ai_tools.py` — thin wrapper mapping tool names to service calls
- Updated frontend chat UI to show "Calling tool: get_portfolio_data..." during tool execution

---

#### ⚠️ Task 3.4a — Pending Fix: RAG gives stale price/market answers (found 2026-07-06)

**Problem**: Asking chat "how has MSFT performed in the last few months" returned 2023 OHLCV data presented as current, even though today is 2026-07-06.

**Why**: (1) No live stock quote tool exists among the 5 tools — `search_market_context` is the only price-adjacent tool and it's pure ChromaDB semantic search. (2) `MarketRAGEngine.retrieve_context()` (`backend/rag/query_engine.py`) ranks purely by cosine similarity with no recency filter/boost, so "recent months" phrasing can match old documents just as well as new ones. (3) Static collections (`ohlcv_data`, `market_news`, etc.) were bulk-loaded once on 2025-06-18 and never refreshed since. (4) `volatility_events` IS refreshed live daily by `volatility_detector_job` (confirmed growing on AWS ChromaDB) but has no ranking edge over the stale bulk docs, so it can lose the similarity contest and never surface.

**Status (2026-07-07): ✅ FIXED AND VERIFIED**:
- [x] Inject today's date into `ai_chat_service.py`'s system prompt (line ~78)
- [x] New tool `get_current_quote(ticker)` in `ai_tools.py` via yfinance `fast_info`, with ~30s in-process TTL cache
- [x] Recency-aware ranking in `retrieve_context()` — blends `relevance_score` with a recency-decay term; also fixed date-key lookup to cover `event_date`/`filed_date`/`detected_at` (found `volatility_events` and `earnings_filings` weren't matching the original `date`/`published_at`/`period` keys)

Verified via a real end-to-end `/chat` call: correct live AAPL price + genuinely recent 2026 volatility events cited by date, not stale 2023 data. See `status.md` for full test output and root-cause writeup.

**Deferred**: scheduled periodic refresh of `historical_loader.py` static collections — bigger lift, separate task later.

---

#### ⚠️ New Pending Item: Daily Securities Price Update Job (found 2026-07-06)

**Problem**: `Securities.current_price` and `Positions.market_value` were set once at synthetic data generation and are never refreshed — there's no daily job for this (`backend/scripts/` only has `risk_job.py`, which writes `Risk_Metrics` and doesn't touch `Securities`/`Positions`). This means `get_portfolio_data` (the chat's main portfolio tool) always returns frozen prices/values, a second, independent staleness bug alongside the RAG one above.

**Status (2026-07-07): ✅ SCRIPT BUILT AND VERIFIED, scheduling not yet wired**:
- [x] `backend/scripts/price_update_job.py` — pulls latest price per ticker (yfinance `fast_info`), updates `Securities.current_price`, recomputes `Positions.market_value` + `weight`, rolls up `Portfolios.total_value`
- [x] Fixed along the way: `Security.current_price` was missing from the ORM entirely (added to `models.py`); `Positions.weight` is `DECIMAL(5,4)` storing a fraction, not a 0–100 percentage (was overflowing on every portfolio until fixed)
- [x] Verified against production Azure SQL: 135/135 securities, 50/50 portfolios updated correctly (AAPL $195.50 → $313.81)
- [x] Deployed to EC2 and scheduled (2026-07-08) — `finsight-daily-price-update` EventBridge schedule, 16:00 ET Mon-Fri via SSM, verified end-to-end via manual trigger before trusting the schedule
- [x] Considered AWS Lambda first, rejected — Azure SQL's IP-allowlist firewall has no good fit with Lambda's non-static egress IP without a NAT Gateway/instance, which would defeat the goal of avoiding an always-on EC2. See `CLOUD_MIGRATION.md` for full writeup.
- [ ] Optional: also insert a daily `Portfolio_Performance` row from this job to keep daily/MTD/YTD return fields alive

See `status.md` for full bug/verification writeup.

---

#### Task 3.4b: FastMCP Server (Custom MCP Server)
**Goal**: Expose FinSight's portfolio analysis tools as a standards-compliant MCP server
so any MCP-compatible AI client can connect and query portfolio data directly

**What this enables**:
- Connect Claude Desktop → FinSight MCP Server → SQL Server / ChromaDB
- Portfolio managers can query their data from Claude Desktop, Cursor, GitHub Copilot Chat
- Demonstrates MCP server development on resume

**Architecture**:
```
[Claude Desktop / Cursor / any MCP client]
            ↓  stdio / SSE transport
[FinSight FastMCP Server  :8002]
            ↓
[SQL Server]  [ChromaDB]  [PortfolioAnalyzer]
```

**Tools to expose**:
- `get_portfolio_summary(portfolio_id)` — full portfolio state from SQL Server
- `get_portfolio_positions(portfolio_id, sector?)` — positions with weights
- `search_market_context(query, n_results?)` — semantic search across ChromaDB
- `analyze_portfolio_risk(portfolio_id)` — risk metrics, concentration, recommendations
- `get_market_events(impact_level?, limit?)` — recent market events from SQL Server

**Resources to expose**:
- `portfolio://{portfolio_id}` — portfolio data as an MCP resource
- `market-event://{event_id}` — event detail as an MCP resource

**Technology**:
- `pip install fastmcp` (Anthropic's high-level MCP server library)
- Single file: `backend/mcp_server.py` using `@mcp.tool()` decorators
- Start: `python backend/mcp_server.py` (runs on stdio for Claude Desktop, or SSE on :8002)

**Claude Desktop config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "finsight": {
      "command": "python",
      "args": ["C:/Agentic_AI/FinSight-AI/backend/mcp_server.py"]
    }
  }
}
```

**New package required**:
```
fastmcp>=0.1.0
```

**Deliverables**:
- `backend/mcp_server.py` — FastMCP server with 5 tools and 2 resources
- Claude Desktop configuration for local testing
- Updated `requirements.txt`
- Demo: Claude Desktop querying live portfolio data and running risk analysis

---

**Resume showcase value**:
- "Built a Model Context Protocol (MCP) server exposing hedge fund portfolio analytics to any MCP-compatible AI client"
- "Implemented agentic AI assistant with GPT-4o autonomous tool calling for dynamic, context-aware financial analysis"
- "Designed multi-tool AI agent that selects and executes the right data retrieval strategy per query"

---

### **PHASE 4: Frontend Development**
**Duration**: 2-3 weeks

#### Task 4.1: Next.js Application Setup
**Goal**: Create modern, responsive frontend

**Pages/Routes**:
1. **Dashboard** (`/dashboard`)
   - Portfolio overview
   - Performance charts
   - Recent alerts/events

2. **Portfolio View** (`/portfolios/{id}`)
   - Position table
   - Allocation charts (sector, geography, asset class)
   - Performance metrics
   - Transaction history

3. **AI Insights** (`/portfolios/{id}/insights`)
   - Portfolio state explanation
   - Recent change analysis
   - Event impact summaries
   - Recommendations panel

4. **Market Events** (`/events`)
   - Event timeline
   - Impact analysis
   - Affected portfolios

5. **Comparison** (`/compare`)
   - Compare multiple portfolios
   - Benchmark analysis
   - Peer performance

**UI Components**:
- Portfolio cards
- Position tables with sorting/filtering
- Interactive charts (Recharts/Chart.js)
- AI chat interface for Q&A
- Alert notifications

**Deliverables**:
- Next.js app structure
- Page components
- Reusable UI components
- Responsive design (Tailwind CSS)
- API integration layer

---

#### Task 4.2: Real-time Updates
**Goal**: Implement WebSocket for live data

**Features**:
- Real-time portfolio value updates
- Live position changes
- Event notifications
- AI analysis streaming

**Technology**:
- WebSocket server (FastAPI WebSocket)
- Next.js client integration
- Redis pub/sub for message broker

**Deliverables**:
- WebSocket server
- Client-side WebSocket integration
- Real-time UI updates

---

#### Task 4.3: AI Chat Interface
**Goal**: Conversational interface for portfolio Q&A

**Features**:
- Natural language queries: "Why did my tech exposure decrease?"
- Contextual AI responses using portfolio data
- Follow-up questions
- Export insights as reports

**Implementation**:
- Chat UI component
- Streaming LLM responses
- Context management
- Chat history

**Deliverables**:
- Chat interface
- LLM streaming integration
- Context-aware query handling

---

### **PHASE 5: Advanced Features**
**Duration**: 2-3 weeks

#### Task 5.1: Advanced Risk Analytics ✅ COMPLETE
**Goal**: Implement daily VaR, stress testing, and factor exposure per portfolio

**What was built**:
1. **Risk Computation** (`backend/services/risk_analytics.py`)
   - Historical VaR (95%, 99%, 1-day, 10-day) — rolling 252-day returns via yfinance
   - Parametric VaR (normal distribution)
   - Return distribution stats: volatility, skewness, kurtosis
   - 6 stress test scenarios: 2008 Crisis, COVID Crash, Rate Hike, Tech Crash, Oil Shock, Stagflation
   - Factor exposure: Market beta, Tech beta, Value beta, Momentum beta vs. benchmark ETFs

2. **Daily Job** (`backend/scripts/risk_job.py`)
   - Loops all portfolios, runs `compute_all()`, saves to `Risk_Metrics` table
   - AWS EventBridge Scheduler (`finsight-daily-risk-job`) triggers at 17:30 ET Mon-Fri
   - SSM SendCommand → EC2 `i-06df445415d082798` (finsight-flink) → `risk_job.py`
   - Logs to `/var/log/finsight_risk.log` on EC2
   - Local run: `python scripts/risk_job.py` from `backend/`

3. **REST API** (`backend/routers/risk.py`)
   - `GET /api/risk/{portfolio_id}` — latest stored metrics (fast, no recompute)
   - `POST /api/risk/{portfolio_id}/refresh` — on-demand recompute (~10-30s)

4. **Frontend** (`frontend/app/portfolios/[id]/page.tsx` — Risk Analytics tab)
   - VaR grid (historical 95%/99%, parametric, 10-day)
   - 6 stress test cards with impact bars
   - Factor exposure table with beta values and R²

5. **Data Storage** (`Risk_Metrics` table, SQL Server)
   - One row per portfolio per day — historical record accumulates
   - Fields: `var_data`, `stress_data`, `factor_data`, `parametric_data` (JSON), `computed_at`, `price_date`

**Note (2026-07-12)**: the original "6 stress test scenarios" list above (Rate Hike, Tech Crash, Oil Shock, Stagflation) never matched what was actually built — this section predates implementation and was never updated. Actual current state: **5 historical-replay scenarios** (2008 Financial Crisis, COVID Crash, 2022 Rate Shock, 2023 Regional Banking Crisis, 2026 Iran War) plus **4 parametric shock scenarios** (Rates +100bps/-100bps via a duration proxy, Equities -20% via computed market beta, No Stress baseline) — a deliberately separate sensitivity-based methodology, not historical replay. Full writeup, including the duration-proxy simplification and known gaps, is in `status.md`.

**Run command (local)**:
```powershell
cd "C:\Agentic_AI\FinSight-AI\backend"
& "C:\Agentic_AI\FinSight-AI\finsightaivenv\Scripts\python.exe" scripts/risk_job.py
```

---

#### Task 5.2: Alert System ✅ COMPLETE
**Goal**: Proactive threshold monitoring and in-app notifications

**What was built**:

1. **Alert Model** (`backend/models.py` — `Alert` class)
   - Fields: `alert_id`, `portfolio_id`, `alert_type`, `severity`, `title`, `message`, `is_read`, `triggered_at`
   - `alert_type`: threshold | event | ai  |  `severity`: critical | warning | info

2. **Alert Engine** (`backend/services/alert_engine.py`)
   - VaR 95% > 2% (warning), VaR 99% > 3.5% (critical), Stress < -25% (warning), Stress < -40% (critical), Market beta > 1.5 (warning)
   - Deduplication: one alert per title per portfolio per day
   - Runs automatically after each portfolio in `risk_job.py`

3. **Alerts REST API** (`backend/routers/alerts.py`)
   - `GET /api/alerts` — filters: `portfolio_id`, `unread_only`, `limit`
   - `GET /api/alerts/unread-count` — returns `{"count": N}`
   - `PATCH /api/alerts/{alert_id}/read` — mark single alert read
   - `PATCH /api/alerts/read-all` — mark all read, optional `portfolio_id` filter

4. **Frontend — Sidebar Bell** (`frontend/components/Sidebar.tsx`)
   - Bell icon with red unread badge, polls every 60 seconds
   - Slide-out panel (320px) — severity-colored per alert, mark individual / mark all

5. **Frontend — Risk Tab Inline Alerts** (`frontend/app/portfolios/[id]/page.tsx`)
   - Alert panel at top of Risk Analytics tab, portfolio-specific (`portfolio_id` filter)
   - Loaded alongside risk metrics when Risk tab opens

**Currently implemented**: threshold alerts only. Event alerts and AI-generated alerts are stubbed (column exists, no engine yet).

**Pending (Task 5.2 sub-items)**:
- **Event alerts** — when a `Market_Events` row fires (e.g. Fed rate hike), scan portfolios for exposure to affected sectors/securities and raise an `alert_type='event'` alert. Needs: event→sector mapping logic + trigger hook in `alert_engine.py`.
- **AI-generated alerts** — GPT-4o proactively reviews a portfolio (news sentiment + positions + recent price moves) and raises a natural-language `alert_type='ai'` alert, e.g. "Heavy NVDA exposure is elevated risk given GPU export news." Needs: new function in `alert_engine.py` that calls OpenAI with portfolio + RAG context and parses the response into an Alert row.

---

#### Task 5.2b: ChromaDB Data Retention (Optional — Review Before Implementing)
**Goal**: Prevent ChromaDB from growing unbounded due to continuous Flink news ingestion

**Background**:
The Flink `news_sentiment_job` writes one document per unique news article into the
`market_news` collection. With Finnhub polling every 2 minutes, this grows steadily over
time. ChromaDB has no native TTL — retention must be implemented as a scheduled cleanup job.

**Recommended Retention Policy**:
| Collection | Keep | Reason |
|---|---|---|
| `market_news` | Last 90 days | Older news has little RAG value for current portfolio analysis |
| `volatility_events` | Last 2 years | Historical volatility patterns remain useful for context |
| `macro_indicators` | Permanent | FRED monthly series — compact and always relevant |
| `ohlcv_data` | Permanent | Historical prices — compact and always relevant |
| `sec_filings` / `earnings` | Last 3 years | Financial filings retain value for longer periods |
| `analyst_research` | Last 1 year | Analyst ratings go stale relatively quickly |

**Implementation Approach**:
- Scheduled cleanup function (weekly) that queries each collection via metadata filter
- ChromaDB supports `where={"published_at": {"$lt": cutoff_date}}` for filtering
- Delete matched IDs using `collection.delete(ids=[...])`
- Can be wired into the Phase 5.2 alert/monitoring infrastructure as a maintenance task

```python
# Sketch — backend/rag/retention.py
def purge_old_news(days_to_keep=90):
    from datetime import datetime, timedelta, timezone
    import chromadb
    chroma     = chromadb.HttpClient(host="localhost", port=8001)
    collection = chroma.get_collection("market_news")
    cutoff     = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).isoformat()
    results    = collection.get(where={"published_at": {"$lt": cutoff}}, include=[])
    if results["ids"]:
        collection.delete(ids=results["ids"])
        print(f"Purged {len(results['ids'])} articles older than {days_to_keep} days")
```

**When to implement**: Only needed once ChromaDB `market_news` document count
exceeds ~50,000 docs or disk usage on `chroma_data` volume approaches 2GB.
Check with: `collection.count()` or `docker system df -v`.

**Note on MCP servers (Yahoo Finance / AlphaVantage / FRED)**:
These are a separate concept from Flink. MCP servers are called ON DEMAND by the LLM
during a conversation to fetch live data (e.g. current stock price, today's Fed rate).
Flink is a BACKGROUND pipeline that pre-loads data into ChromaDB for semantic RAG search.
They are complementary — MCP is relevant only if we add Claude API tool-use or
agentic capabilities in a future phase.

**Deliverables** (if implemented):
- `backend/rag/retention.py` — collection-aware purge function with configurable TTL per collection
- Scheduled task wired into FastAPI lifespan or a Celery beat job
- Monitoring log showing doc counts before/after each purge run

---

#### Task 5.3: Risk Trend Visualization ✅ COMPLETE
**Goal**: Exploit the historical `Risk_Metrics` rows that accumulate daily to show how portfolio risk evolves over time

**Why this matters**:
`risk_job.py` inserts one row per portfolio per day. Currently only the latest row is read.
The history is being silently built up and not yet used. This task surfaces that data.

**Features**:
1. **VaR Trend Chart** (Risk Analytics tab)
   - Line chart: last 30 days of `var_95_1d_pct` and `var_99_1d_pct`
   - Highlight the day VaR first crossed warning/critical threshold
   - Powered by the existing `Risk_Metrics` historical rows — no new computation

2. **Stress Test Trend** (optional)
   - Show how `2008 Crisis` scenario impact % changed over the past month
   - Indicates whether portfolio is becoming more or less resilient over time

3. **Alert Correlation** (optional)
   - Overlay threshold-breach alert dates on the VaR trend chart
   - Makes it obvious that alerts fired when VaR was elevated

**Backend changes needed**:
- New endpoint: `GET /api/risk/{portfolio_id}/history?days=30`
  - Returns array of `{computed_at, var_95_1d_pct, var_99_1d_pct, stress_worst_pct}` rows
  - Query: `ORDER BY computed_at DESC LIMIT N` on `Risk_Metrics` table

**Frontend changes needed**:
- Add a Recharts `LineChart` in the Risk Analytics tab (below VaR grid)
- Fetch history when Risk tab opens (alongside existing `getRiskMetrics()` call)
- Show "No history yet — run the risk job daily to build trend data" if < 2 rows exist

**No new pip dependencies** — Recharts is already in the frontend; SQL query is trivial.

**Deliverables**:
- `GET /api/risk/{portfolio_id}/history` endpoint
- VaR trend chart component on Risk tab
- (Optional) stress test trend + alert overlay

---

### **PHASE 6: Infrastructure & Deployment**
**Duration**: 1-2 weeks

#### Task 6.1: Dockerization
**Goal**: Containerize all services

**Containers**:
1. **Backend API** (FastAPI)
2. **Frontend** (Next.js)
3. **SQL Server** (or use managed service)
4. **ChromaDB**
5. **Redis**
6. **Flink** (job manager + task manager)

**Deliverables**:
- Dockerfiles for each service
- Docker Compose for local development
- Multi-stage builds for optimization

---

#### Task 6.2: Redis Caching Strategy ✅ COMPLETE (2026-07-11)
**Goal**: Implement caching for performance

**What's cached (three shipped, two deferred)**:
| What | TTL | Status |
|---|---|---|
| Unread alert count | 60s | ✅ Done — precise invalidation on mark-read/mark-all-read |
| Risk metrics (`/api/risk/{id}`) | 30 min (not 24h as originally planned) | ✅ Done — `risk_job.py` runs on a different EC2 than Redis, no safe cross-box invalidation without exposing an unauthenticated Redis to the network, so a shorter TTL bounds staleness naturally instead |
| Portfolio summary + positions | 5 min | ✅ Done |
| AI chat responses | 1h (keyed by query hash) | Not yet — lower priority, revisit if OpenAI cost becomes worth optimizing |
| yfinance price fetches | 30s | Not yet — the in-process TTL cache already added to `get_current_quote` (Task 3.4a) covers the main case |

**What's NOT cached**: WebSocket price ticks (streaming by nature), Flink/Kafka data.

**Deployed as Valkey** (Redis-compatible fork), not Redis itself — AL2023's default repos have no `redis` package, only `valkey` (actively maintained, AWS's current recommendation) and the older `redis6`. Fully wire-compatible with the Python `redis` client. Self-hosted on the ChromaDB EC2 (Option A from the original plan below), binds `127.0.0.1` only — no security group change needed.

**Deliverables**:
- ✅ `backend/services/cache.py` — reusable `get_or_set()`/`invalidate()` wrapper, graceful fallback if Redis/Valkey is unreachable (same posture as ChromaDB elsewhere in this app)
- ✅ Applied to alerts, risk metrics, portfolio summary/positions
- ✅ Cache invalidation logic (same-process writes only — see risk metrics TTL note above for the cross-EC2 case)
- Not built: AI chat response caching, yfinance fetch caching (deferred, lower value)

<details>
<summary>Original planning notes (kept for reference)</summary>

**AWS deployment options** (decide when implementing):
- **Option A — Install on existing EC2**: `apt install redis` on the ChromaDB t3.micro. Free, uses spare capacity, good enough for demo.
- **Option B — AWS ElastiCache**: Managed Redis, ~$15-20/month for `cache.t3.micro`. Overkill for this project but resume-worthy if budget allows.

</details>

---

#### Task 6.3: Deployment & CI/CD — PARTIALLY COMPLETE (backend cloud deploy done 2026-07-09)
**Goal**: Production-ready deployment

**What's done**:
1. ✅ Cloud infrastructure — FastAPI backend deployed to the existing ChromaDB EC2 (`13.206.225.80`), reused rather than a new box ($0 extra cost). Domain `fin-sightai.space` (GoDaddy) — `api.fin-sightai.space` (backend), `www.fin-sightai.space` (frontend, Vercel). `nginx` + Certbot for HTTPS, `systemd` for process management/auto-restart. Full writeup: `CLOUD_MIGRATION.md`.
2. ✅ Managed SQL Server — already on Azure SQL since Phase 1.
3. ⏳ CI/CD pipeline (GitHub Actions) — still manual (`git pull` + `systemctl restart` over SSH/SSM). Not started.
4. ⏳ Health checks and monitoring — `/health` endpoint exists, no external monitoring/alerting wired up yet.
5. ⏳ Logging — plain file logs (`journalctl`/log files on EC2), no ELK/CloudWatch aggregation.
6. ⏳ Secrets management — `.env` files on disk, not AWS Secrets Manager (see Phase 7 Task 7.2 below).

**Remaining Deliverables**:
- CI/CD pipeline (GitHub Actions)
- Monitoring dashboards
- Secrets management

---

#### Task 6.4: Authentication & Multi-Tenant Portfolio Access ✅ COMPLETE (scoped 2026-07-07, built 2026-07-11)
**Goal**: When JWT auth is added, don't just gate the API — make each fund manager see only the portfolios (and their customers) they actually manage, instead of all 50. This is a real-world multi-tenant access control pattern, not just a login screen.

**What was built** (all 4 phases, each verified live against production Azure SQL / a real browser, not just imported):
1. **Data model** — `Users` table + `Portfolios.manager_id` FK, migrated via a new additive `db_migration_auth.sql` (NOT by re-running `db_migration_fix.sql`, which deletes/recreates `Portfolios` and would have violated the FK from `Alerts`/`Risk_Metrics`, destroying the accumulated alert/risk history). 5 demo fund managers (~10 portfolios each) + 1 admin, documented in `AUTH.md`.
2. **Backend core** — `backend/auth.py` (`hash_password`/`verify_password` via `bcrypt`, JWT access+refresh via `PyJWT`, `get_current_user`, `require_portfolio_access`, `check_portfolio_access`, `scope_portfolio_query`), `routers/auth.py` (login/refresh/logout/me), all 6 routers retrofitted. CORS switched from `allow_origins=["*"]` to the explicit origin list + `allow_credentials=True` (required for the httpOnly cookie).
3. **Frontend** — `/login` page, `AuthContext`, `apiFetch` sends `credentials: 'include'`, Sidebar shows the logged-in manager + logout. Existing pages needed zero changes — the portfolio list narrows automatically once the backend scopes it.
4. **The AI tool dispatcher + MCP server + WebSocket** — the part flagged below as easy to get wrong, closed: `ai_tools.py`'s `execute_tool()` now takes `current_user` and checks ownership before every portfolio-scoped tool call; `mcp_server.py` resolves one identity per process from a long-lived `FINSIGHT_MCP_TOKEN` (minted via `scripts/mint_mcp_token.py`) and fails closed if missing; `/ws` authenticates at the handshake (rejects with no valid cookie) and filters each price tick to the connection's accessible portfolios.

**Bugs found and fixed along the way** (not hypothetical — each one reproduced against real data before being fixed):
- `EventImpactAnalyzer` treats an empty portfolio list as "no filter → show everything" — a manager whose requested IDs didn't intersect their own access would've seen every portfolio's data. Guarded in both `/analysis/event-impact` and `/analysis/ai/analyze-event`.
- Hardcoded `secure=True` on the auth cookies silently blocked all local HTTP testing (`Secure` cookies are never sent over plain HTTP, by curl or any real browser — `COOKIE_SECURE` is now a setting, off in dev `.env`, on in production).
- Next.js 16's new `allowedDevOrigins` protection blocked the HMR websocket between `127.0.0.1` and `localhost`, silently preventing the whole client bundle from hydrating — no console error, just a permanently blank screen. Not a code bug; just means local dev must be accessed via `localhost:3000`.

**Deployment note**: ✅ fully deployed to production 2026-07-11 (backend, frontend, and MCP server — see `CLOUD_MIGRATION.md` for the full writeup, including the MCP server's relocation from the Flink EC2 to the ChromaDB EC2 and that EC2's resize to t3.small).

**Why this matters**: Today there is no concept of "who is logged in" anywhere in the schema — `Customers` are the institutions being managed, not the people managing them. Bolting JWT on without also scoping data access would just add a login page in front of the same unrestricted 50-portfolio view.

**1. Data model**
- New `Users` (fund managers) table: credentials, `role` (`fund_manager` | `admin`)
- `Portfolios.manager_id` FK → `Users` — one owner per portfolio (simplest model; upgrade to a `Portfolio_Managers(portfolio_id, user_id, role)` junction table later if a portfolio ever needs multiple managers/analysts)
- `admin` role bypasses scoping entirely (needed for ops/compliance-style oversight, and for demoing the full dataset)
- One-time backfill: the existing 50 seeded portfolios have no owner — assign them across a few demo manager accounts + one admin account

**2. Enforcement layer (the part that's easy to get wrong)**
- Every one of the 18+ REST endpoints currently trusts whatever `portfolio_id` is in the URL (`GET /api/portfolios/{id}`, `/api/risk/{id}`, etc.) — without scoping, Manager A could request Manager B's portfolio ID directly (classic IDOR).
- Fix once, centrally: a reusable FastAPI dependency, e.g. `require_portfolio_access(portfolio_id) -> Portfolio`, used by every portfolio-scoped route instead of ad-hoc `db.query(Portfolio).get(id)` calls.
- List endpoints (`GET /api/portfolios`) become `WHERE manager_id = current_user.id` (unfiltered for `admin`).

**3. Non-obvious gotcha: AI chat + MCP server**
- `backend/services/ai_tools.py`'s `execute_tool()` dispatcher and `backend/mcp_server.py`'s tool functions both accept `portfolio_id` as a plain argument chosen by the LLM/tool caller — not a REST path a dependency can gate.
- If only the REST routers are scoped, a logged-in manager could ask the chat "show me portfolio 37's risk" and get another manager's data straight through tool-calling, completely bypassing auth.
- The same identity/scoping check needs to be threaded into the AI tool dispatcher and the MCP tool handlers, not just the FastAPI routers.

**4. Frontend**
- Login page, JWT stored in an httpOnly cookie (safer than localStorage against XSS)
- Portfolio list/dropdown naturally narrows to "my portfolios" once the list endpoint is scoped
- Admin view/toggle to see the full portfolio set

**Deliverables**:
- `Users` table + password hashing (bcrypt/argon2) + `/auth/login`, `/auth/refresh` endpoints
- `Portfolios.manager_id` FK + backfill script for existing 50 portfolios across demo accounts
- `require_portfolio_access()` FastAPI dependency, retrofitted into all portfolio-scoped routers
- Scoping check added to `ai_tools.py` tool dispatcher and `mcp_server.py` tool handlers
- Frontend login flow + scoped portfolio list/dropdown + admin view

**Resume value**: "Implemented JWT-based multi-tenant access control ensuring fund managers can only access their own authorized portfolios — enforced consistently across REST API, agentic AI chat tool-calling, and MCP server layers."

---

## Success Metrics

**Technical**:
- API response time < 200ms (90th percentile)
- AI analysis generation < 5 seconds
- Support 100+ concurrent users
- 99.5% uptime

**Business**:
- Portfolio analysis accuracy (validated by domain experts)
- Event detection latency < 1 minute
- Recommendation relevance score > 80%
- User engagement (time spent, queries per session)

---

## Resume Showcase Strategy

**Portfolio Presentation**:
1. **Live Demo** (deployed instance with sample data)
2. **GitHub Repository** (well-documented, clean code)
3. **Architecture Diagram** (system design)
4. **Demo Video** (2-3 minutes showing key features)
5. **Case Study** (write-up explaining problem, solution, impact)

**Key Highlights for Resume**:
- "Built AI-powered portfolio analysis system for institutional investors"
- "Designed scalable architecture handling real-time market data streaming (Apache Flink)"
- "Implemented RAG system with ChromaDB for enhanced financial insights"
- "Developed multi-LLM orchestration (Claude/GPT-4) optimized for cost/performance"
- "Created full-stack solution (Python, Next.js, SQL Server) with real-time capabilities"

---

## Estimated Timeline
- **Phase 1**: 1-2 weeks ⭐ START HERE
- **Phase 2**: 2-3 weeks
- **Phase 3**: 2-3 weeks
- **Phase 4**: 2-3 weeks
- **Phase 5**: 2-3 weeks
- **Phase 6**: 1-2 weeks

**Total**: 9-16 weeks (2.5-4 months) for full system

**MVP** (Phases 1-3 + basic Phase 4): ~6-8 weeks

---

## Next Immediate Steps

1. ✅ **Review and approve this plan**
2. **Create project structure** (folders, virtual environment)
3. **Start Task 1.1**: Design SQL schema
4. **Create ER diagram** for database
5. **Write SQL CREATE TABLE scripts**

---

## Questions & Assumptions

**Assumptions**:
- You have SQL Server running locally with appropriate permissions
- You have Python 3.9+ installed
- You have Node.js 18+ for Next.js
- OpenAI/Anthropic API keys available
- Sufficient compute for local Flink (or will use cloud)

**Questions for Clarification**:
1. What level of historical data depth? (1 year, 5 years?)
2. Frequency of portfolio updates? (daily, intraday, real-time?)
3. Do you need multi-currency support initially?
4. Target deployment environment? (local, AWS, GCP, Azure?)
5. Authentication/multi-tenancy required for MVP?

---

---

## Technologies / Features Worth Adding (Review Before Each Phase)

These were identified as gaps that add resume value or practical robustness. Revisit when working on the relevant phase — don't implement blindly, options may need re-evaluation.

| Item | Priority | Notes |
|---|---|---|
| **JWT Auth + Multi-Tenant Access** | ✅ Done (local) | See Task 6.4 — built and verified locally 2026-07-11. Not yet deployed to production (`api.fin-sightai.space` still runs the old unauthenticated build). |
| **Langfuse (LLM tracing)** | High | Free tier. Tracks every GPT-4o call — tokens, latency, tool calls, cost. 20-minute add. Strong resume signal for LLM engineering maturity. |
| **Rate limiting** (`slowapi`) | Medium | One-liner FastAPI middleware. Prevents API abuse on public demo. |
| **Prometheus + Grafana** | Medium | Observability story for resume. Both free/open-source, can run on EC2. Shows production-readiness mindset. |
| **ChromaDB static collections on AWS** | ✅ Done | All 8 static collections loaded to AWS ChromaDB (2026-07-06): ohlcv_data (7,991), dividends_data (2,226), earnings_data (400), analyst_recs (100), macro_indicators (3,498), fed_communications (729), earnings_filings (17,200), splits_data (24). Total ~36K docs. |
| **ChromaDB data retention job** | Low | See Task 5.2b. Only needed once `market_news` exceeds ~50K docs or disk > 2GB. |
| **Reddit Sentiment Pipeline** | Good to Have | Live Flink stream from r/wallstreetbets, r/investing, r/stocks via PRAW. Adds retail sentiment signal distinct from institutional data. No viable 5-year historical — live stream only (similar to market_news pipeline). Implement only if a live sentiment signal adds demo value. |
| **BigQuery Analytics Layer** | Medium | Free forever (1 TB queries/month, 10 GB storage). See Task 7.1 below for full integration plan. Strong resume signal — classic OLTP (Azure SQL) + OLAP (BigQuery) architecture. |

---

### **PHASE 7: BigQuery Analytics Integration** (Future — Review When Time Allows)

#### Task 7.1: Google BigQuery as Analytics Layer
**Goal**: Add BigQuery as a read-side analytics store alongside Azure SQL, enabling complex
historical queries (correlation matrices, rolling volatility, multi-year trends) that would
be slow or expensive to run directly on the operational SQL Server database.

**Free tier**: Always Free — 10 GB storage + 1 TB queries/month. No expiry.

**Architecture**:
```
Azure SQL Server (operational)          Google BigQuery (analytics)
  ├── Portfolios / Users                  ├── Historical OHLCV (5+ years)
  ├── Positions / Transactions            ├── Pre-aggregated risk metrics
  ├── Real-time alerts                    ├── Correlation matrices
  └── Market Events                       └── Sector performance aggregates
              │                                       │
              └───────────── FastAPI ─────────────────┘
                                 │
                             Next.js UI
```

**Rule**: Azure SQL handles transactional/operational reads. BigQuery handles analytical/historical queries.

---

**Data Sync Strategy (choose one when implementing)**:

- **Option A — Daily Python script** (simplest to start):
  Dump OHLCV + risk metrics from Azure SQL → BigQuery via `google-cloud-bigquery` client.
  ```python
  df = pd.read_sql("SELECT * FROM OHLCV_Data WHERE date = CAST(GETDATE() AS DATE)", conn)
  bq_client.load_table_from_dataframe(df, "dataset.ohlcv_data")
  ```

- **Option B — ChromaDB loader feeds both** (cleanest):
  The existing `chromadb_setup.py` already fetches yfinance data. Add a parallel write
  path to BigQuery in the same pipeline.

- **Option C — Flink → BigQuery sink** (most impressive for showcase):
  Use Google's Flink BigQuery connector. Makes the full pipeline end-to-end visible.
  Real-time streaming data lands directly in BigQuery.

---

**Showcase Features to Build**:

1. **Portfolio Correlation Heatmap** (`/analytics` page)
   - "How correlated are my holdings over the last 2 years?"
   - BigQuery window functions handle this across millions of rows in seconds
   - Frontend: color-coded matrix (Recharts or D3)

2. **Historical Volatility Chart**
   - Rolling N-day volatility using BigQuery `STDDEV()` window function
   - User can select 30/60/90-day window
   - Much faster than computing in Python/Pandas

3. **Sector Performance Dashboard**
   - Group portfolio/watchlist by sector
   - Show 1M / 3M / 1Y / 5Y performance per sector
   - Aggregates across thousands of tickers in seconds

4. **Backtesting** ("What if I bought X stock 3 years ago?")
   - BigQuery stores full historical OHLCV
   - FastAPI calculates returns and benchmark comparison
   - Very demo-friendly, visually striking

5. **AI Chat Tool: `query_historical_analytics`**
   - Add BigQuery as a 6th tool in the agentic chat (Task 3.4a)
   - User: "How volatile was NVDA in 2023 vs 2024?"
   - LLM queries BigQuery, returns data-backed answer

6. **Anomaly History** (ties into Flink volatility detection)
   - Flink detects real-time volatility → writes flags to BigQuery
   - BigQuery stores the history of anomalies
   - Show: "This stock had unusual volatility 12 times in the last year"

---

**FastAPI Integration**:
```python
# pip install google-cloud-bigquery pandas-gbq
from google.cloud import bigquery

bq_client = bigquery.Client(project="your-gcp-project")

@router.get("/analytics/historical-volatility/{symbol}")
async def get_historical_volatility(symbol: str, window_days: int = 30):
    query = f"""
    SELECT date, symbol,
        STDDEV(daily_return) OVER (
            ORDER BY date ROWS BETWEEN {window_days} PRECEDING AND CURRENT ROW
        ) AS rolling_volatility
    FROM `your_dataset.ohlcv_data`
    WHERE symbol = @symbol
    ORDER BY date DESC LIMIT 365
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("symbol", "STRING", symbol)]
    )
    df = bq_client.query(query, job_config=job_config).to_dataframe()
    return df.to_dict("records")
```

**New dependency**: `google-cloud-bigquery`, `pandas-gbq`

**Resume value**:
- "Designed OLTP + OLAP architecture: Azure SQL for operational data, BigQuery for analytics"
- "Integrated Google BigQuery for historical financial analytics — correlation matrices, rolling volatility, sector heatmaps"
- "Extended agentic AI chat with BigQuery tool for multi-year data-backed question answering"

**Prerequisites before starting**:
- Log into existing GCP account at `console.cloud.google.com`
- Create a project and enable BigQuery API
- Create a service account + download JSON key
- Set `GOOGLE_APPLICATION_CREDENTIALS` env variable

**Deliverables** (when implementing):
- `backend/services/bigquery_service.py` — BQ client + query helpers
- `backend/routers/analytics.py` — new `/api/analytics/` endpoints
- Daily sync script or Flink BQ sink (Option A/B/C above)
- `frontend/app/analytics/page.tsx` — Portfolio Analytics page with charts
- Updated `requirements.txt`

---

---

## PHASE 7: Security Hardening (Good to Have — Do Later)

### Task 7.1: HTTPS / TLS Encryption (Data in Transit)

All data between the browser and backend travels over the internet — currently unencrypted if served over plain HTTP. Financial data (portfolio values, positions, AI responses) must be encrypted in transit.

**What to do:**
- **Vercel frontend** — already HTTPS by default. Nothing to do.
- **FastAPI backend (ngrok demo mode)** — ngrok tunnels are already HTTPS. Nothing to do for demos.
- **FastAPI backend (production deployment)** — if/when backend moves to cloud (EC2, ECS, etc.), put it behind an **Application Load Balancer (ALB)** with an ACM certificate, or use **nginx + Let's Encrypt (Certbot)** as a reverse proxy.
- **AWS EC2 services (ChromaDB, Kafka)** — currently only accessed server-to-server (private IP). If ever exposed publicly, add TLS. For now, security groups limiting access to known IPs is sufficient.
- **WebSocket (`ws://`)** — must become `wss://` (already done for Vercel + ngrok setup).

**Checklist when going production:**
- [ ] ALB + ACM cert OR nginx + Certbot on backend EC2
- [ ] All `NEXT_PUBLIC_API_URL` uses `https://`, `NEXT_PUBLIC_WS_URL` uses `wss://`
- [ ] HSTS header on API responses
- [ ] Verify no mixed-content warnings in browser console

---

### Task 7.2: AWS Secrets Manager + SSM Parameter Store — ✅ COMPLETE, deployed to production (2026-07-11)

All real credentials moved out of plaintext `.env` on the backend EC2. Split across two AWS services rather than Secrets Manager alone, since only some of the original `.env` contents are genuinely secret:

**Secrets Manager** (`finsight/prod`, one bundled JSON secret, ap-south-1) — the 11 real credentials: `DB_SERVER`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `FRED_API_KEY`, `AlphaVantage_API_KEY`, `FINNHUB_API_KEY`, `FINNHUB_WEB_HOOK_SECRET`. One secret rather than one-per-key — a single EC2 role has no reason for split IAM grants, and it's one `boto3` call instead of several.

**SSM Parameter Store** (Standard tier, free) — 3 non-secret infra values that still shouldn't sit in a public-facing repo/plaintext file: `/finsight/chroma_host`, `/finsight/chroma_port`, `/finsight/kafka_bootstrap_servers` (internal EC2 IPs/ports).

**Deliberately not migrated**: `NGROK_API_KEY` — grepped the backend, zero references, retired instead (leftover from pre-domain-deployment dev). `CORS_ORIGINS`, `API_HOST/PORT/RELOAD`, `DB_ODBC_DRIVER`, `COOKIE_SECURE` — plain config, no confidentiality need, left in the EC2's (now much smaller) `.env`.

**Implementation** (`backend/services/secrets_loader.py`):
```python
import json, os

def load_aws_secrets() -> None:
    if os.environ.get("USE_AWS_SECRETS", "").lower() != "true":
        return
    import boto3
    region = os.environ.get("AWS_REGION", "ap-south-1")

    sm = boto3.client("secretsmanager", region_name=region)
    secret = json.loads(sm.get_secret_value(SecretId="finsight/prod")["SecretString"])
    for k, v in secret.items():
        os.environ[k] = str(v)

    ssm = boto3.client("ssm", region_name=region)
    for param_name, env_key in SSM_PARAM_TO_ENV.items():
        os.environ[env_key] = ssm.get_parameter(Name=param_name)["Parameter"]["Value"]
```
Called from the top of `config.py`, before `Settings()` is instantiated — pydantic-settings' priority order is env vars > `.env` file > defaults, so this is safe to enable without first stripping the EC2 `.env` (real env vars win regardless). Opt-in via `USE_AWS_SECRETS=true`; `boto3` is only imported when the flag is on, so it's not a hard dependency for local dev. No try/except swallowing — if AWS is unreachable with the flag on, the app fails to start with a clear traceback rather than silently booting with missing credentials.

**Bug found during first deploy**: the IAM policy grants `ssm:GetParameter` (singular), but the first version of the code called the batch `ssm.get_parameters()` API — a *different* IAM action (`ssm:GetParameters`, plural) than what was granted, so it 403'd on the real EC2 role despite working locally under the broader `lavanya` CLI profile. Fixed by looping `get_parameter()` once per param instead of one batch call.

**Deployed and verified** (2026-07-11): `boto3` installed in the EC2's `backendvenv`, systemd unit (`finsight-backend.service`) updated with `Environment=USE_AWS_SECRETS=true` + `Environment=AWS_REGION=ap-south-1`, service restarted. Confirmed via log (`[OK] Loaded 11 secrets from Secrets Manager (finsight/prod) + 3 params from SSM Parameter Store` → `[OK] Database connected`) and a live `/health` check. Real secrets then stripped from the EC2's `.env` (backed up to `.env.bak.20260711` first) and the service restarted again with zero `.env` fallback — proving the app runs purely on AWS-sourced credentials via the EC2's IAM instance role, not just "env vars happened to win over stale file values." Production login re-verified in a real browser afterward (JWT signing now uses the AWS-sourced key too).

---

**Created**: 2026-06-14
**Last Updated**: 2026-07-12
**Status**: All of Phase 5 (5.1, 5.2 incl. event + AI alerts, 5.3, 5.4 PDF reports) complete. 3.4b (FastMCP), 6.2 (Redis/Valkey caching), 6.4 (JWT + multi-tenant access), 7.2 (AWS Secrets Manager + SSM Parameter Store) also complete and live in production. AWS ChromaDB 36K+ docs. Docker Desktop retired. Both daily EC2 batch jobs (`risk_job.py`, `price_update_job.py`) live and verified on AWS (2026-07-08). FastAPI backend pushed to the cloud 2026-07-09 (Task 6.3 partial — see `CLOUD_MIGRATION.md`): reused ChromaDB EC2, `fin-sightai.space` domain, nginx+HTTPS, Vercel frontend live at `https://www.fin-sightai.space`. MCP server relocated from the Flink EC2 to the ChromaDB EC2 2026-07-11 (that box resized t3.micro → t3.small to fit it, now also running Redis/Valkey). Overview tab volatility display bug fixed 2026-07-11. Stress testing overhauled 2026-07-12: swapped Dot-com Bust for 2023 Regional Banking Crisis + 2026 Iran War, added 4 parametric shock scenarios (Rates ±100bps, Equities -20%, No Stress) as a separate sensitivity-based methodology — see status.md for full writeup. Pending: real CI/CD, Dockerization, Excel report format (deferred), orphaned analyze-event AI endpoint (found 2026-07-12).

---

## Appendix: Ideas Not Part of the Initial Design (found 2026-07-10, review later)

These surfaced from a pending-work review on 2026-07-10 — none were part of the original phase plan above. Not scoped or scheduled yet; revisit and decide before implementing any of them.

1. **LLM cost dashboard** — `llm_service.py` already tracks every call via `UsageRecord`/`get_usage_stats()`, but nothing surfaces it in the UI. Likely low effort since the data collection already exists.
2. **Portfolio comparison page** (`/compare`) — was in the original Task 4.1 page list but never built. Multi-portfolio + benchmark comparison.
3. **Custom what-if stress scenarios** — let a user define their own shock (e.g. "oil -30% + rates +100bps") instead of only the 6 fixed scenarios in `risk_analytics.py`.
4. **Alert delivery beyond in-app** — Slack webhook or email for `severity='critical'` alerts, using existing trigger points in `alert_engine.py`.
5. **WebSocket auth gap** — `/ws` currently has zero auth; anyone connected sees live price ticks for all 50 portfolios. Should be bundled into Task 6.4 (JWT) rather than left as an afterthought.
6. **Compliance / audit trail** — access log (user, portfolio, endpoint, timestamp). Pairs naturally with the new `Users` table planned in Task 6.4; relevant differentiator for the hedge-fund domain.
