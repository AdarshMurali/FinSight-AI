# FinSight AI — Functional Overview

> **Status of this document.** This is the authoritative description of what FinSight AI does, for readers who care about the product rather than the infrastructure. For deployment, tech stack, and system design, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## 1. What FinSight AI is

FinSight AI is an AI-powered portfolio-intelligence platform for hedge funds and institutional investors. A fund manager signs in and can: browse their portfolios' positions and performance, ask a conversational AI assistant free-form questions about that portfolio and have it pull live data to answer, see risk analytics (VaR, stress tests, factor exposure), get proactive alerts when risk crosses a threshold or a market event plausibly touches a holding, and export a portfolio report. An admin sees every portfolio in the firm rather than just their own.

Unlike a traditional dashboard, the centerpiece feature — **AI chat** — doesn't run a fixed report. It's agentic: given a question, GPT-4o decides for itself which of six tools to call (portfolio data, position history, market-context search, market events, risk analysis, live quotes), executes them, and only then drafts a grounded answer. See [`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg) for that flow end to end, alongside the two further pipelines that run independently of anyone using the chat: live volatility detection and a pair of daily scheduled jobs (risk metrics, end-of-day data capture) — see §5.

## 2. Users and access

| Role | Scope | Example |
|---|---|---|
| `fund_manager` | Own portfolios only (~10 of 50, enforced at the database query layer) | Sarah Chen sees her book, not Marcus's |
| `admin` | All 50 portfolios, scoping bypassed | Marcus Webb sees the whole firm |

Demo accounts exist for both roles (see `AUTH.md`); the scoping is enforced identically across the REST API, the AI chat's tool layer, and the live WebSocket feed — a manager can't get another manager's data by asking the AI chat for it or by guessing a portfolio ID in a request.

## 3. Core user journeys

### 3.1 Sign in
Email + password (bcrypt-verified) → JWT access/refresh tokens issued as httpOnly cookies. Session persists across page loads via the frontend's `AuthContext`.

### 3.2 Dashboard
Landing page: total AUM and other KPIs, a portfolios table, a market-events feed, strategy distribution, and a live clock. Portfolio rows flash green/red on every live price tick (via WebSocket); Kafka-sourced market events surface as toast alerts when the streaming pipeline is running. The dashboard still works with live price simulation even when the Kafka/Flink pipeline is off outside market hours.

### 3.3 Portfolio list & detail
Positions, sector/geography/asset allocation, performance (returns, Sharpe, volatility), and transaction history, with the total value flashing live as prices tick. The **Risk Analytics** tab shows a VaR grid, five historical stress-test scenarios (2008 Crisis, COVID Crash, 2022 Rate Shock, 2023 Regional Banking Crisis, 2026 Iran War) plus four parametric shocks (rates ±100bps, equities −20% via beta, no-stress baseline), a factor-exposure table, a 30-day VaR trend chart, and an inline alert panel. An **Export Report** button generates a PDF bundling the overview, latest risk metrics, top 15 positions, recent alerts, and a fresh AI-written commentary paragraph. (Excel export was considered and explicitly deferred — PDF only ships today.)

### 3.4 AI Insights
Three GPT-4o-driven panels for a selected portfolio: a plain-language explanation of its current state, a narrative of what changed and why, and a set of recommendations — each grounded with RAG context from ChromaDB, with collapsible source citations and a per-call cost tag.

### 3.5 AI Chat — the centerpiece
A streaming conversational assistant. The user asks a question about a selected portfolio; GPT-4o autonomously decides which tools it needs (it can chain several in one turn — e.g. pull portfolio data, then position history, then market context), the UI shows an orange "calling: X" chip while each tool runs, and the final answer streams in as rendered markdown with collapsible RAG citations. There is **no human approval step anywhere in this loop** — once a question is submitted, it runs fully autonomously from tool selection through the final answer. See the diagram for the full loop, including the code-enforced cap on how many tool-call iterations a single question can trigger.

### 3.6 Market Events
A timeline of Fed/geopolitical/sector/earnings/M&A events with impact levels, sourced from yfinance (earnings), FRED (macro), and Finnhub-derived news (M&A/guidance, keyword-matched). Each event's detail page lists affected portfolios and offers a manual "Analyze impact" AI button per portfolio.

### 3.7 Alerts
Three kinds, all delivered automatically (no chat interaction required):

- **Threshold alerts** — VaR/stress/beta breaches computed by a daily risk job, deduplicated by "family," with a 30-day mute cooldown (bypassed for critical severity) and automatic resolution once the condition clears.
- **Event alerts** — a sector×region exposure scan against tracked market events, deduplicated to once per event per portfolio.
- **AI-generated alerts** — GPT-4o-mini reviews a portfolio's top holdings plus RAG context once a day and flags only specific, dated catalysts, capped at one alert per portfolio per day.

A sidebar bell shows an unread count (polled every 60s); alerts also surface inline on the Risk Analytics tab.

Threshold and AI-generated alerts both depend on the daily risk job described in §5, which runs on the streaming EC2 alongside live volatility detection (see `ARCHITECTURE.md` §4 for the market-hours schedule both run on).

### 3.8 Keeping the data current — daily end-of-day capture
A separate scheduled job (`price_update_job.py`) pulls each day's OHLCV prices, dividends, splits, and macro indicators (yfinance + FRED) and writes them into Azure SQL and ChromaDB, so the next trading day's dashboards, risk numbers, and AI answers are working from current data rather than a stale snapshot.

### 3.9 MCP server — using FinSight AI from outside the app
FinSight AI exposes eight tools (list/summarize portfolios, positions, risk, alerts, market events, RAG search, refresh risk) over an MCP SSE endpoint, so a portfolio manager can query their live data directly from Claude Desktop, Cursor, or VS Code without opening the web app. **Caveat:** the public endpoint authenticates once at startup as a single admin identity, so any MCP client that connects to it currently sees all 50 portfolios, not just one manager's — see `ARCHITECTURE.md` §6 for the full explanation and the workaround (running the server locally in stdio mode with a manager's own token).

## 4. What's deliberately not there

Being explicit about scope avoids over-promising:

- **No human-in-the-loop gate on any product feature.** Every pipeline in the diagram — chat, alerts, risk monitoring — runs fully autonomously. The only human approval anywhere in the system is operational: the two-environment CI/CD deploy gate (see `ARCHITECTURE.md` §7), not something a portfolio manager ever sees.
- **No Excel export** — PDF only, by explicit deferral.
- **No Reddit sentiment, no BigQuery analytics layer** — both were designed (see `RAG.md`, `plan.md`) but never built.
- **Curated, not open-world.** Market-event mapping covers the securities and event types the system actually ingests, not arbitrary open-world news.

## 5. The three dominant runtime flows

All three are diagrammed in [`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg):

1. **Agentic AI chat** (§3.5) — triggered by a user question; GPT-4o alone decides what happens next at each step; terminates in a streamed, cited answer. Runs on the backend EC2, which is always on.
2. **Live volatility detection** (§3.7) — runs continuously during market hours: live trade ticks feed a Flink windowed aggregation; a breach either gets logged silently (no catalyst worth surfacing) or triggers an AI catalyst check and lands as a delivered alert.
3. **Daily scheduled jobs** (§3.7, §3.8) — two independent cron-triggered pipelines: `risk_job.py` recomputes VaR/stress/factor exposure and feeds the same threshold-alert engine as flow 2; `price_update_job.py` refreshes the day's OHLCV/dividends/macro data into Azure SQL and ChromaDB.

Flows 2 and 3 both run on the second, streaming EC2 — see [`ARCHITECTURE.md`](ARCHITECTURE.md) §4 for exactly how its market-hours schedule works.

Color-coding on the diagram: **blue** = deterministic code (math, routing, auth), **purple** = LLM (reasoning/RAG/drafting), **teal** = hybrid (code + LLM together). None of FinSight AI's product pipelines carry a fourth category — a human-approval gate — see §4.

## 6. Where to look

- [`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg) — the three flows above, diagrammed
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — tech stack, deployment, and system design
- `AUTH.md` — demo account credentials and login detail
- `backend/rag/USAGE_EXAMPLES.md` — concrete RAG query examples
