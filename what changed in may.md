# Why AI Chat Only Mentioned META for "What Changed in May 2026?"

**Question asked**: "What changed in May 2026?"  
**Portfolio**: Portfolio 1  
**Date investigated**: 2026-06-21

---

## The Short Answer

GPT-4o only talked about META because META was the **only stock with concrete May 2026 price data** in the context it received. It had no data about NVDA, MSFT, GOOGL, or any other position for that specific month. The model answered correctly from what it was given — the problem is the data it received was incomplete.

---

## Where the META Data Came From

**Data lineage:**

1. `historical_loader.py` called `yf.download("META", ...)` → fetched **real Yahoo Finance data** including May 2026
2. Daily prices were aggregated into a monthly summary and stored in ChromaDB `ohlcv_data` collection:

```
Document ID:  ohlcv_META_20260531
Collection:   ohlcv_data
Text:         "META monthly OHLCV: Open $614.12, High $642.40,
               Low $592.05, Close $631.92, Volume 300,382,900 shares in May 2026"
```

3. When the question was asked, RAG retrieved this document as the top semantic match for "what changed in May 2026"
4. GPT-4o read the raw numbers and reproduced them as the answer

**What the numbers mean:**

| Number | Meaning |
|---|---|
| `$614.12` | META's opening price on the **first trading day** of May 2026 |
| `$642.40` | Highest price META reached on **any single day** in May 2026 |
| `$592.05` | Lowest price META fell to on **any single day** in May 2026 |
| `$631.92` | META's closing price on the **last trading day** of May 2026 |
| `300,382,900` | **Total shares traded** across all days in May 2026 (summed) |

These are **real market prices** from Yahoo Finance — not synthetic data.

---

## Why Only META — Three Root Causes

### 1. RAG returns only 5 documents total across all 10 collections

```python
# ai_chat_service.py line 72
rag_results = self.rag.retrieve_context(rag_query, n_results=5)
```

5 documents spread across 10 collections. A portfolio with 30 positions only gets 1–2 stocks' OHLCV data in the context window at best.

### 2. The RAG query has no awareness of which tickers are in the portfolio

```python
# ai_chat_service.py line 71
rag_query = f"{user_message} {portfolio_data.get('portfolio_name', '')} portfolio"
# Became: "what changed in May 2026 Portfolio 1 portfolio"
```

This is a generic text query. ChromaDB returns whichever document is most semantically similar — META's May 2026 document happened to win. Whether META moved more or less than other portfolio holdings was irrelevant to the ranking.

### 3. PortfolioAnalyzer provides no per-position price history

The system prompt GPT-4o received from `PortfolioAnalyzer` included:

```
Top Positions: META (8.2%), NVDA (6.1%), MSFT (5.8%)...  ← weights only, no price performance
Risk Metrics:  Volatility: 12.3%, Sharpe: 1.45           ← portfolio-level, not per-stock
Performance:   YTD: +7.2%, MTD: +1.1%                    ← portfolio-level only
```

There is no historical price movement data per position. Even if NVDA dropped 20% in May 2026, GPT-4o had zero data about it because nothing fetched that from ChromaDB or SQL Server.

---

## What a Complete Answer Would Need

To properly answer "what changed in May 2026?" the system needs:

1. **SQL query** on `Position_Changes_Log` for that portfolio + date range
2. **OHLCV data from ChromaDB** for each specific ticker in the portfolio (not whatever RAG randomly surfaces)
3. **Ranked by magnitude of change** — which positions moved most
4. Only then ask GPT-4o to synthesize

The current architecture cannot do steps 1 or 2 in a targeted, portfolio-aware way.

---

## The Fix — Task 3.4a (Agentic Tool Calling)

With GPT-4o function/tool calling enabled (planned in Task 3.4a), the same question would work like this:

```
User: "What changed in May 2026?"

GPT-4o decides it needs historical data and calls:
  → get_position_history(portfolio_id=1, start="2026-05-01", end="2026-05-31")
     → SQL Server: returns ALL position weight changes for that month

  → search_market_context("META NVDA MSFT GOOGL May 2026 price performance volatility")
     → ChromaDB: returns OHLCV for multiple portfolio tickers, not just META

GPT-4o synthesizes:
  "In May 2026, NVDA had the largest move (+18.3%), followed by META (+2.9%).
   MSFT declined (-4.1%). The portfolio's tech weighting shifted from 35% to 38%..."
```

The model drives the data retrieval and knows which tools to call — instead of receiving whatever RAG happens to surface.

---

## Files Involved

| File | Role |
|---|---|
| `backend/rag/historical_loader.py` | Fetched META OHLCV from yfinance, stored in ChromaDB |
| `backend/rag/query_engine.py` | Retrieved the META document via semantic similarity |
| `backend/services/ai_chat_service.py` | Built system prompt, ran RAG, streamed GPT-4o response |
| `backend/services/portfolio_analyzer.py` | Provided portfolio state (current weights only, no history) |

---

## Related Plan Item

See **Task 3.4a** in `plan.md` — Agentic AI Chat with OpenAI Function Calling.  
This is the planned fix for the limitation described here.
