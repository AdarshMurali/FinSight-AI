# FinSight AI — Technical Architecture

> **Status of this document.** This is the single authoritative, current-state architecture reference for FinSight AI. The repo also carries several earlier working documents — `RAG.md`, `CLOUD_MIGRATION.md`, `AUTH.md`, `STARTUP_GUIDE.md`, `plan.md`, `status.md` — written at different points as the system evolved. They're kept for their operational detail (setup commands, bug postmortems, day-by-day history) but several are now stale or describe designs that were never fully built. Where this document and an older one disagree, **this document wins**; the specific disagreements are logged in [§9](#9-documentation-notes--known-drift).

## 1. What FinSight AI is

FinSight AI is a full-stack, agentic portfolio-intelligence platform for hedge funds and institutional investors. A fund manager signs in to see their book of portfolios, ask an AI chat assistant free-form questions about performance, risk, and market context, and get automatically generated alerts when a position's risk crosses a threshold or a market event plausibly affects it. It's also a systems-engineering showcase: the emphasis on CI/CD, IAM scoping, and secrets management throughout reflects that this is a portfolio project built to production standards, not only a feature demo.

Two architecture diagrams accompany this document:

- **[`docs/architecture/tech-architecture.svg`](docs/architecture/tech-architecture.svg)** — the real, currently-deployed infrastructure: two AWS EC2 instances (backend + streaming), Vercel (frontend), Azure SQL, the CI/CD pipeline, and the third-party integrations (OpenAI, Finnhub/FRED/yfinance), with a clearly separated box for what's local-dev-only and not part of the live deployment.
- **[`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg)** — the two dominant runtime pipelines (agentic AI chat, and always-on risk/volatility monitoring), color-coded by deterministic-code vs. LLM vs. hybrid, the same convention used in the companion MarginMaestro project.

## 2. Design principles (as-built, not aspirational)

1. **LLM decides, code executes.** The AI chat assistant (GPT-4o) chooses *which* tool to call; every tool itself is a plain, auth-checked Python function against SQL/ChromaDB/yfinance. Risk math (VaR, stress tests, factor exposure) is closed-form/regression code — never computed by the LLM.
2. **One provider, honestly.** Despite `anthropic` being a pinned dependency and older docs describing a multi-model ("Claude/GPT") design, the shipped system calls **OpenAI only** — `gpt-4o`, `gpt-4o-mini`, and `text-embedding-3-small`, routed by a `MODEL_ROUTING` table in `backend/services/llm_service.py`. See [§9](#9-documentation-notes--known-drift).
3. **Data-layer auth, not UI-layer.** Portfolio access is scoped by `manager_id` at the query layer, enforced identically across REST routes, the AI chat's tool dispatcher, and the WebSocket handshake — not just hidden in the frontend.
4. **No IaC, but reproducible.** Infrastructure was hand-provisioned via the AWS Console/CLI rather than Terraform/CloudFormation; the IAM policy documents under `aws/iam/` are version-controlled so the access model is still reviewable and reproducible.
5. **Two independently-gated deploys.** Backend and the Kafka/Flink streaming stack live on separate EC2 instances with separate GitHub Environments (`production-backend`, `production-flink`), each requiring human reviewer approval — a backend-only change can ship without touching the streaming pipeline and vice versa.
6. **Two EC2s by design, not one.** The architecture has always called for a second EC2 — `finsight-flink` — dedicated to the Kafka/Flink streaming stack, kept separate from the backend/ChromaDB EC2 so a spike in streaming load can't starve the API. It was originally started and stopped daily by a scheduled Lambda around market hours; as of this writing it's been switched off entirely to save cost during a lower-usage period. **It has not been removed from the design** — the compose files, IAM role, and scheduler Lambda are all still in place, and bringing it back up is a few minutes' work, not a rebuild. See [§4](#4-system--deployment-architecture) and the technical diagram for what runs on it.

## 3. Full tech stack

| Layer | Choice | Status |
|---|---|---|
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4 | **Live** — Vercel, `www.fin-sightai.space`, auto-deploys on push to `adarsh` |
| Backend API | FastAPI, SQLAlchemy 2.0, Pydantic v2, uvicorn | **Live** — Docker container on EC2 `13.206.225.80` (t3.small), behind nginx + Certbot at `api.fin-sightai.space` |
| MCP server | FastMCP, same image as backend, different entrypoint | **Live** — SSE at `:8002/sse`, connectable from Claude Desktop/Cursor/VS Code |
| LLM | OpenAI `gpt-4o` (analysis, chat) + `gpt-4o-mini` (quick summaries, daily AI alerts) | **Live** — `anthropic` SDK is installed but never called; treat as unused |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim, cosine) | **Live** — same model for ingestion and query |
| Vector store | ChromaDB (HTTP client) | **Live** — same EC2 as backend, port 8001, ~36.6k docs / 10 collections |
| Relational store | Azure SQL Server (`mssql+pyodbc`, ODBC 18) | **Live** — free tier, auto-pauses after ~1h idle; schema is plain numbered `.sql` scripts, **not** Alembic despite it being a dependency |
| Auth | Self-rolled JWT (PyJWT) + bcrypt, httpOnly cookies | **Live** — no third-party IdP |
| Streaming | Kafka (Confluent images) + Apache Flink 1.18 (PyFlink) | **Built and deployable, currently paused** — separate EC2 `13.233.21.229` (t3.medium), stopped for cost savings; design is market-hours-only (09:20–16:25 ET) start/stop via a scheduler Lambda, restartable in minutes |
| Cache | Valkey (Redis-compatible fork) | **Live** — self-hosted on the backend EC2, `127.0.0.1:6379` only |
| CI | GitHub Actions (`ci.yml`) | **Live** — builds/pushes 3 Docker images to Docker Hub, path-filtered |
| CD | GitHub Actions (`cd.yml`) via AWS SSM `RunShellScript` | **Live** — gated behind 2 independently human-approved GitHub Environments |
| IaC | None — hand-provisioned; IAM policy JSON version-controlled | as-built, see [§2](#2-design-principles-as-built-not-aspirational).4 |
| Secrets | AWS Secrets Manager (`finsight/prod`, one JSON secret) | **Live** — opt-in via `USE_AWS_SECRETS=true` |
| Non-secret config | AWS SSM Parameter Store | **Live** — Chroma host/port, Kafka bootstrap servers, volatility-detector thresholds |
| Observability | `/health` endpoint + plain EC2 logs only | **Not built** — no CloudWatch/ELK log aggregation, no Prometheus/Grafana, no LLM tracing |
| Analytics layer (BigQuery) | — | **Planned, not started** |
| Reddit sentiment (PRAW) | — | **Planned, not started** |

## 4. System / deployment architecture

See `docs/architecture/tech-architecture.svg` for the full picture. In prose:

- The **browser** talks HTTPS/WSS to the **Vercel-hosted Next.js frontend**, which in turn calls the **FastAPI backend** at `api.fin-sightai.space` (nginx + Certbot terminates TLS) and opens a native FastAPI **WebSocket** for live price ticks and Kafka-sourced market-event toasts.
- The backend EC2 (t3.small) runs, via Docker Compose: the **FastAPI backend** (`:8000`), the **MCP server** (`:8002/sse`, same image/different entrypoint), **ChromaDB** (`:8001`), and **Valkey** (`127.0.0.1:6379`). It talks to **Azure SQL** over TDS/pyodbc and to **OpenAI** for every chat completion and embedding call.
- The second EC2, `finsight-flink` (t3.medium), is dedicated to everything that needs to run continuously or on a schedule independent of a user's request — three distinct jobs, all currently paused along with the instance itself:
  1. **Live volatility detection** — Zookeeper, Kafka, Kafka-UI, the Flink JobManager/TaskManager, and two Finnhub producer containers (trades + news) consume a live trade WebSocket, aggregate it in a 15-minute tumbling window, and flag abnormal price-move%/volume-ratio events.
  2. **Daily risk metrics** — `risk_job.py`, cron-triggered via EventBridge → SSM, recomputes VaR, stress-test, and factor-exposure numbers for every portfolio and writes `Risk_Metrics`, which the threshold-alert engine reads.
  3. **Daily end-of-day data capture** — `price_update_job.py`, also cron-triggered, pulls the day's OHLCV/dividends/splits/macro data (yfinance + FRED) so the next trading day starts with a current dataset in Azure SQL and ChromaDB.

  Flink jobs write embeddings back into ChromaDB on the *other* EC2 over a security-group-restricted cross-instance HTTP call. **As of this writing, `finsight-flink` is stopped** to save cost — none of the three jobs above are currently running — but the instance, its Docker Compose stack, and its IAM role are untouched; starting it is an EC2 console click (or a Lambda invocation) away, not a redeploy. The weekly `market_events_job.py` is the one scheduled job that runs on the *backend* EC2 instead, since it only needs REST/DB access, not the streaming stack.
- A scheduled **Lambda** (`finsight-ec2-scheduler`, EventBridge-triggered) is the mechanism designed to start and stop the streaming EC2 daily around market open/close; it's currently unused while the instance is manually kept off.
- **CI** (`ci.yml`) builds and path-filter-pushes three Docker images to Docker Hub on every push to `adarsh`/`main`. Its completion triggers **CD** (`cd.yml`), which — after independent human approval on each of the `production-backend` and `production-flink` GitHub Environments — uses AWS SSM `RunShellScript` (OIDC-federated, no stored AWS keys) to `git pull` + `docker compose pull/up` on the relevant EC2.
- **`docker-compose-streaming.yml`** at the repo root is a **local-development-only** copy of the Kafka/Flink stack (ports 2181/9092/8080/8082). Production uses a separate compose file under `aws/ec2-flink/` on the dedicated streaming EC2 — don't confuse the two.

## 5. RAG pipeline

The originally-designed pipeline (documented in `RAG.md`) targeted eleven data sources (yfinance, FRED, SEC EDGAR, Reddit, Alpha Vantage, Finnhub, Polygon, NewsAPI, Wikipedia, BLS, and more), Celery-scheduled ingestion, and five Kafka topics with a VADER-sentiment Flink job. **What's actually live is narrower:**

- **Batch-loaded once**, via `historical_loader.py`: OHLCV, dividends, splits, earnings, analyst recommendations, and an initial news batch — sourced from **yfinance + FRED only**. SEC EDGAR filings (17.2k docs, the largest single collection) *were* fully built, unlike most of the other originally-planned sources.
- **Streamed continuously**: `market_news` via a Finnhub-polling producer (every 2 min) → Kafka → a Flink sentiment job → ChromaDB; and `volatility_events` via a live Finnhub trade WebSocket → Kafka topic `market.trades` → a Flink 15-minute tumbling-window job (widened from 5 minutes on 2026-07-18) that flags abnormal price-move%/volume-ratio and embeds a templated description via OpenAI.
- Each ingested item becomes **one embedded natural-language document** (no separate chunking step) via `text-embedding-3-small`, stored in ChromaDB with rich metadata and queried by cosine similarity.
- **Retrieval** (`backend/rag/query_engine.py`) blends similarity with a 180-day recency-decay term (fixing an earlier bug where stale 2023 bulk data outranked live data) and supports an optional ticker hard-filter (fixing cross-ticker contamination, e.g. an AAPL query surfacing AXP results).
- **Grounding is on-demand, not pre-injected.** The AI Insights panels build a RAG context block directly into their prompt; the agentic chat instead exposes retrieval as a tool (`search_market_context`) the LLM chooses to call — a deliberate upgrade from an earlier "always pre-load 5 docs" design. Every RAG-grounded answer shows collapsible source citations in the UI.

Treat `RAG.md` as a historical design doc, not current behavior; `backend/rag/README.md` and `knowledgebase.md`'s pipeline diagram are closer to ground truth.

## 6. Auth & access model

Self-rolled JWT auth (PyJWT, bcrypt), access + refresh tokens as **httpOnly cookies** (not localStorage, to reduce XSS exposure). Two roles: `fund_manager` (scoped to their own ~10 of 50 portfolios via `Portfolios.manager_id`) and `admin` (unscoped, sees all 50).

The scoping is enforced at **every** surface, not just REST:

- A reusable `require_portfolio_access(portfolio_id)` FastAPI dependency guards every portfolio-scoped route.
- The AI chat's tool dispatcher (`ai_tools.py: execute_tool()`) checks ownership of the requested `portfolio_id` **before** running any tool, so natural-language chat can't be used to route around REST-level scoping.
- The `/ws` WebSocket authenticates at handshake and filters every price tick to that connection's accessible portfolios.
- The **MCP server is the one deliberate scope-cut**: it authenticates once at process startup with a single long-lived token bound to the **admin** identity, so anyone who can reach its public SSE endpoint (`http://13.206.225.80:8002/sse`, plain HTTP) gets all-50-portfolio access. True per-manager MCP access requires running the server locally in stdio mode with that manager's own token. This is documented, not accidental — but it's worth flagging in any security discussion of the system, along with the endpoint being HTTP rather than HTTPS.

## 7. CI/CD pipeline

- **`ci.yml`** — triggered on push to `adarsh`/`main`, on PRs (build-only), or manual dispatch. Builds and, on a real push, pushes three path-filtered Docker images (`finsight-backend`, `finsight-flink`, `finsight-producer`) to Docker Hub.
- **`cd.yml`** — triggered by `ci.yml`'s successful completion (`workflow_run`) or manual dispatch. Two independent jobs, each gated by a GitHub Environment requiring human reviewer approval (`production-backend`, `production-flink`), each running an AWS SSM `RunShellScript` command (OIDC-federated IAM role, no long-lived AWS keys) that does `git pull` + `docker compose pull/up -d` on the relevant EC2.
- This pipeline is real and battle-tested, not aspirational: building it surfaced (and fixed) around nine distinct production issues — IAM resource-scoping quirks, `root` vs. `ec2-user` git/SSH ownership mismatches, SSM command wait-timeout limits, Flink resource contention on redeploy, hash-based job staleness, and CI path-filter granularity, among others.
- The Lambda-based EC2 power scheduler is the one deliberate exception to this pipeline — it's deployed manually, not through CI/CD.

## 8. Cross-cutting concerns

**Secrets & config.** AWS Secrets Manager holds one bundled JSON secret per environment (`finsight/prod`: DB credentials, JWT signing key, OpenAI/FRED/Alpha Vantage/Finnhub API keys), opt-in via `USE_AWS_SECRETS=true`. Non-secret runtime config (Chroma host/port, Kafka bootstrap servers, volatility-detector thresholds) lives in SSM Parameter Store instead.

**Observability.** Minimal by design so far: a `/health` endpoint and plain file/journalctl logs on each EC2. There is no centralized log aggregation, no metrics dashboard, and no LLM call tracing — all explicitly on the "not yet done" list rather than overlooked.

**Cost control.** The streaming EC2 only runs during market hours (Lambda-scheduled start/stop); Azure SQL free tier auto-pauses when idle; the backend, ChromaDB, MCP server, and cache all share one EC2 instance rather than each getting their own.

**Known security-relevant gaps worth naming explicitly:** the MCP endpoint is plain HTTP and admin-scoped for every caller (§6); there's no WAF/rate limiting called out anywhere in the docs; and there's no automated dependency/vulnerability scanning in CI beyond the build itself.

## 9. Documentation notes & known drift

A few things earlier docs get wrong or leave stale, worth knowing before trusting any single file in isolation:

- **LLM stack**: README.md and `plan.md`'s original tech-stack section describe "Claude/GPT"; the shipped backend calls OpenAI exclusively. `status.md` itself confirms this and calls out a stale MCP-tool docstring that still claims Claude Opus.
- **`RAG.md`** is the original design doc (2026-06-16) and describes several sources/components (Reddit, Alpha Vantage sentiment, NewsAPI, Celery, a VADER Flink job, five Kafka topics) that were never built as specified. `backend/rag/README.md` and `knowledgebase.md` reflect what's actually live.
- **`status.md`** is internally stale relative to its own later entries — its "Where Everything Lives" summary table says the backend is "Local only," contradicted elsewhere in the same file and by `CLOUD_MIGRATION.md`. Prefer `CLOUD_MIGRATION.md` and `plan.md` (both last updated 2026-07-18) for current deployment state; use `status.md` for its detailed bug postmortems, not as a state summary.
- **`STARTUP_GUIDE.md`** predates Dockerization and CI/CD (2026-07-16/17) and its MCP-server section references an outdated EC2 IP. Useful for *what each step does conceptually*, not for literal current commands.
- The Flink volatility window is **15 minutes**, not the 5 minutes still shown in `knowledgebase.md`'s Task 5.1 write-up (changed 2026-07-18 for data-coverage reasons).

## 10. Where to look

- [`docs/architecture/tech-architecture.svg`](docs/architecture/tech-architecture.svg) — infrastructure diagram (this document, §4)
- [`docs/architecture/functional-flow.svg`](docs/architecture/functional-flow.svg) — runtime pipeline diagram (companion: `FUNCTIONAL_OVERVIEW.md`)
- [`FUNCTIONAL_OVERVIEW.md`](FUNCTIONAL_OVERVIEW.md) — what the product does, feature by feature
- `RAG.md` — original RAG design (historical; see §5 and §9 for what's actually live)
- `AUTH.md` — demo accounts and auth flow detail (see §6 for the current summary)
- `CLOUD_MIGRATION.md` — the authoritative live-vs-planned deployment tracker
- `STARTUP_GUIDE.md` — local dev setup (conceptually useful; verify commands against `CLOUD_MIGRATION.md`)
- `backend/rag/README.md`, `knowledgebase.md` — ground-truth RAG pipeline detail
