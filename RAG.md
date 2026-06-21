# Task 3.3: RAG System with ChromaDB — Market Sentiment Data Pipeline

## Overview

This document covers the complete architecture and implementation guide for populating ChromaDB with market sentiment data, historical financial data, and near-real-time streams — enabling the FinSight AI agent to reason about current market conditions, volatility drivers, and historical event patterns.

---

## What the AI Agent Needs from ChromaDB

When a user asks "Why did my tech portfolio drop 12% this week?", the agent needs:

| Context Type | Example |
|---|---|
| Recent news & sentiment | "Fed raised rates 50bps, tech selloff followed" |
| Historical event patterns | "Similar selloff in 2022 Q1 after Volcker pivot" |
| Earnings context | "NVDA/MSFT missed estimates by 3%" |
| Macro indicators | "CPI came in at 4.2%, above 3.8% forecast" |
| Analyst sentiment | "Sector consensus shifted from Buy to Hold" |
| Geopolitical context | "US-China tensions escalated over Taiwan Strait" |

All of this lives in ChromaDB as vector-embedded documents with rich metadata.

---

## Free Data Sources (No Payment Required)

### Tier 1 — Completely Free (No Limits / Very Generous)

#### 1. Yahoo Finance (`yfinance` Python Library)
- **What it provides**: 5+ years of OHLCV price data, dividends, splits, earnings, analyst recommendations, company news
- **Cost**: Free, no API key needed
- **Rate limits**: Unofficial API — no hard limit, but throttle to ~2000 req/day
- **Best for**: Historical price data (5 years), sector ETF data, earnings history
- **Python**: `pip install yfinance`

```python
import yfinance as yf

# 5 years of price history
ticker = yf.Ticker("AAPL")
hist = ticker.history(period="5y")

# Company news (last 30 days)
news = ticker.news

# Options chain for volatility signals
opts = ticker.option_chain("2024-03-15")

# Analyst recommendations
recs = ticker.recommendations
```

#### 2. FRED (Federal Reserve Economic Data)
- **What it provides**: 800,000+ economic time series — CPI, Fed Funds Rate, unemployment, GDP, yield curves, money supply
- **Cost**: Free, requires free API key from https://fred.stlouisfed.org/docs/api/api_key.html
- **Rate limits**: 120 requests per 60 seconds
- **Best for**: Macro economic context, Fed policy history, recession indicators
- **Python**: `pip install fredapi`

```python
from fredapi import Fred
fred = Fred(api_key='your_free_key')

# Fed Funds Rate history (decades back)
fed_rate = fred.get_series('FEDFUNDS', observation_start='2019-01-01')

# CPI inflation
cpi = fred.get_series('CPIAUCSL', observation_start='2019-01-01')

# Yield curve (10Y - 2Y spread) — key recession signal
yield_spread = fred.get_series('T10Y2Y', observation_start='2019-01-01')

# VIX volatility index
vix = fred.get_series('VIXCLS', observation_start='2019-01-01')
```

#### 3. SEC EDGAR (US Securities & Exchange Commission)
- **What it provides**: All US company filings — 10-K, 10-Q, 8-K (material events), proxy statements, earnings
- **Cost**: Completely free, no API key
- **Base URL**: `https://data.sec.gov/`
- **Best for**: Earnings text, risk factor disclosures, material event filings (8-K)
- **Python**: `pip install sec-edgar-downloader`

```python
from sec_edgar_downloader import Downloader

dl = Downloader("FinSightAI", "your@email.com", "/data/sec_filings")

# Download last 10 quarterly reports for Apple
dl.get("10-Q", "AAPL", limit=10)

# Download material event filings (8-K = major corporate events)
dl.get("8-K", "AAPL", limit=20)
```

#### 4. Reddit API (PRAW)
- **What it provides**: Real-time & historical posts from r/wallstreetbets, r/investing, r/stocks, r/economics
- **Cost**: Free — register at https://www.reddit.com/prefs/apps
- **Rate limits**: 60 requests/minute
- **Best for**: Retail sentiment, meme stock detection, contrarian signals
- **Python**: `pip install praw`

```python
import praw

reddit = praw.Reddit(client_id="xxx", client_secret="xxx", user_agent="FinSightAI/1.0")

# Top posts in r/investing this week
subreddit = reddit.subreddit("investing")
for post in subreddit.top(time_filter="week", limit=100):
    # process post.title, post.selftext, post.score
    pass
```

---

### Tier 2 — Free Tier (Limited Requests)

#### 5. Alpha Vantage
- **What it provides**: Stock prices, forex, crypto, economic indicators, **news sentiment API** (crucial!), earnings calendar
- **Cost**: Free API key — https://www.alphavantage.co/support/#api-key
- **Rate limits (free tier)**: 25 requests/day, 500 requests/month
- **Best for**: News sentiment scoring (built-in NLP sentiment), earning surprises
- **Python**: `pip install alpha-vantage`

```python
import requests

# NEWS SENTIMENT API — key for RAG
url = "https://www.alphavantage.co/query"
params = {
    "function": "NEWS_SENTIMENT",
    "tickers": "AAPL,MSFT,NVDA",
    "topics": "technology,earnings",
    "time_from": "20240101T0000",
    "limit": 200,
    "apikey": "YOUR_FREE_KEY"
}
response = requests.get(url, params=params).json()

# Each article has: title, summary, source, sentiment_score, ticker_sentiment
for article in response["feed"]:
    sentiment = article["overall_sentiment_score"]  # -1 to +1
    label = article["overall_sentiment_label"]  # Bullish/Bearish/Neutral
```

#### 6. Finnhub
- **What it provides**: Company news, earnings surprises, IPO calendar, insider transactions, analyst price targets, economic calendar
- **Cost**: Free API key — https://finnhub.io/register
- **Rate limits (free tier)**: 60 API calls/minute
- **Best for**: Real-time company news feed, earnings surprises, insider trading signals
- **Python**: `pip install finnhub-python`

```python
import finnhub

client = finnhub.Client(api_key="your_free_key")

# Company news (last 30 days)
news = client.company_news("AAPL", _from="2024-01-01", to="2024-03-01")

# Earnings surprises history
surprises = client.company_eps_estimates("AAPL", freq="quarterly")

# Market news by category
market_news = client.general_news("general", min_id=0)

# Economic calendar (Fed meetings, CPI releases)
economic_calendar = client.economic_calendar()
```

#### 7. Polygon.io (Free Tier)
- **What it provides**: US stock data, options, news articles, market status
- **Cost**: Free API key — https://polygon.io/
- **Rate limits (free tier)**: 5 calls/minute, end-of-day data only (no real-time)
- **Best for**: Historical news articles, ticker details, market events

#### 8. Massive API (User Mentioned)
- **What it provides**: Financial data aggregator
- **Website**: https://massiveapi.com
- **Free tier**: Check current limits at registration
- **Best for**: Aggregated financial datasets, alternative data

---

### Tier 3 — Supplementary Free Sources

#### 9. NewsAPI
- **What it provides**: News articles from 150,000+ sources worldwide
- **Cost**: Free developer plan — https://newsapi.org/register
- **Rate limits (free)**: 100 requests/day, 30-day history only
- **Best for**: General financial/economic news headlines

#### 10. Wikipedia (Via `wikipedia-api`)
- **What it provides**: Historical event context, company background, economic crisis summaries
- **Cost**: Completely free
- **Best for**: Enrichment context — "2022 inflation crisis", "2020 COVID market crash"

#### 11. BLS (Bureau of Labor Statistics)
- **What it provides**: Employment data, PPI, CPI, productivity indexes
- **Cost**: Free — no API key required for basic access
- **URL**: `https://api.bls.gov/publicAPI/v2/timeseries/data/`

---

## Five-Year Historical Data Strategy

Since some free APIs have limited lookback, here is the recommended approach to build 5 years of ChromaDB content without paying:

| Data Type | Source | Lookback | Volume |
|---|---|---|---|
| Price history (OHLCV) | yfinance | 5+ years | S&P 500 tickers |
| Macro indicators | FRED | 10+ years | 50+ series |
| Earnings filings | SEC EDGAR | 10+ years | 10-K/10-Q/8-K |
| Market events | Wikipedia + manual | 5 years | Crisis summaries |
| Fed communications | FRED / Fed website | 10+ years | FOMC minutes |
| News sentiment | Alpha Vantage | 1-2 years | Via key rotation |
| Reddit sentiment | PRAW Pushshift | 5 years | Historical dump |

**Key strategy**: Batch-load historical data first (one-time pipeline), then set up near-real-time streaming for ongoing updates.

---

## Apache Flink Integration for Near-Real-Time Ingestion

### Why Flink for ChromaDB Ingestion?

Flink processes event streams with exactly-once semantics, windowing, and backpressure — ideal for:
- Consuming API responses from a Kafka topic
- Applying NLP sentiment enrichment as a stream operator
- Batching embeddings (to avoid per-document OpenAI API calls)
- Writing enriched documents to ChromaDB in micro-batches

### Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA SOURCE LAYER                             │
│                                                                  │
│  yfinance ──────┐                                                │
│  Alpha Vantage ─┤                                                │
│  Finnhub ───────┼──► Python Ingestion Workers ──► Kafka Topics  │
│  FRED API ──────┤         (scheduled via Celery)                 │
│  SEC EDGAR ─────┘                                                │
│  Reddit PRAW ───┘                                                │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
                                    Kafka Topics:
                                    - market.news
                                    - market.prices
                                    - market.earnings
                                    - market.macro
                                    - market.sentiment
                                           │
┌──────────────────────────────────────────▼──────────────────────┐
│                   APACHE FLINK LAYER (PyFlink)                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Job 1: Market News Sentiment Stream                     │    │
│  │  - Consume: market.news topic                            │    │
│  │  - Enrich: VADER sentiment scoring                       │    │
│  │  - Window: Tumbling 5-minute windows                     │    │
│  │  - Output: Enriched news documents                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Job 2: Price Volatility Event Detector                  │    │
│  │  - Consume: market.prices topic                          │    │
│  │  - Detect: >2% moves, volume spikes, sector correlations │    │
│  │  - Emit: "Volatility Event" documents                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Job 3: Document Embedding Batcher                       │    │
│  │  - Collect all enriched documents                        │    │
│  │  - Batch: 50 docs per OpenAI embedding call              │    │
│  │  - Write: ChromaDB via HTTP sink                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
┌──────────────────────────────────────────▼──────────────────────┐
│                     CHROMADB VECTOR STORE                        │
│                                                                  │
│  Collections:                                                    │
│  - market_news          (news + sentiment)                       │
│  - macro_indicators     (FRED data)                              │
│  - earnings_filings     (SEC 10-K/10-Q/8-K)                     │
│  - volatility_events    (price spike events)                     │
│  - fed_communications   (FOMC minutes, speeches)                 │
│  - analyst_research     (recommendation changes)                 │
│  - reddit_sentiment     (retail trader sentiment)                │
└──────────────────────────────────────────┬──────────────────────┘
                                           │
┌──────────────────────────────────────────▼──────────────────────┐
│                    AI AGENT LAYER                                │
│                                                                  │
│  RAG Query: "What caused tech volatility in Jan 2025?"          │
│                                                                  │
│  1. Embed query → semantic search ChromaDB                       │
│  2. Retrieve top-K relevant documents                            │
│  3. Inject as context into LLM prompt                            │
│  4. LLM generates grounded analysis with citations               │
└─────────────────────────────────────────────────────────────────┘
```

---

## ChromaDB Collections Design

### Collection 1: `market_news`
```python
{
  "id": "news_alphavantage_20240115_aapl_001",
  "document": "Apple reported Q1 earnings beating estimates by 4.2%. iPhone sales grew 12% YoY driven by China recovery. Services revenue hit record $23.1B.",
  "metadata": {
    "source": "alpha_vantage",
    "published_at": "2024-01-15T18:30:00Z",
    "tickers": ["AAPL"],
    "sectors": ["technology"],
    "sentiment_score": 0.72,          # -1 (bearish) to +1 (bullish)
    "sentiment_label": "Bullish",
    "event_type": "earnings",
    "url": "https://...",
    "relevance_score": 0.95
  }
}
```

### Collection 2: `macro_indicators`
```python
{
  "id": "fred_fedfunds_20240131",
  "document": "Federal Reserve maintained Fed Funds Rate at 5.25-5.50% at January 2024 FOMC meeting, citing persistent inflation above 2% target. Markets interpreted as hawkish, leading to yield curve steepening.",
  "metadata": {
    "source": "fred",
    "series_id": "FEDFUNDS",
    "date": "2024-01-31",
    "value": 5.33,
    "event_type": "monetary_policy",
    "macro_category": "interest_rates",
    "market_impact": "hawkish"
  }
}
```

### Collection 3: `earnings_filings`
```python
{
  "id": "sec_8k_nvda_20240221",
  "document": "NVIDIA Corporation (NVDA) filed 8-K on Feb 21 2024 reporting Q4 FY2024 revenue of $22.1B, up 265% YoY. Data center segment grew 409% driven by AI GPU demand. EPS of $5.16 beat consensus of $4.60 by 12%.",
  "metadata": {
    "source": "sec_edgar",
    "filing_type": "8-K",
    "ticker": "NVDA",
    "filed_date": "2024-02-21",
    "fiscal_quarter": "Q4FY2024",
    "revenue_surprise_pct": 8.5,
    "eps_surprise_pct": 12.0,
    "sector": "technology"
  }
}
```

### Collection 4: `volatility_events`
```python
{
  "id": "volatility_tech_20240815",
  "document": "Technology sector experienced 3.8% single-day decline on Aug 15 2024. VIX spiked to 28.4 from 16.2 (75% increase). Primary driver: Yen carry trade unwinding triggered margin calls across leveraged positions. ETF QQQ volume 4.2x average.",
  "metadata": {
    "source": "flink_detector",
    "event_date": "2024-08-15",
    "affected_sectors": ["technology", "semiconductors"],
    "vix_level": 28.4,
    "sector_drawdown_pct": -3.8,
    "trigger_category": "macro_shock",
    "volume_ratio": 4.2,
    "duration_days": 3
  }
}
```

### Collection 5: `fed_communications`
```python
{
  "id": "fomc_minutes_20240320",
  "document": "FOMC March 2024 minutes revealed divided committee on rate cut timing. Several members expressed concern about progress toward 2% inflation target. Dot plot showed median of 3 cuts in 2024 vs 6 priced by markets. Powell emphasized data dependency.",
  "metadata": {
    "source": "federal_reserve",
    "document_type": "fomc_minutes",
    "meeting_date": "2024-03-20",
    "rate_decision": "hold",
    "rate_level": 5.33,
    "hawkish_dovish_score": 0.3,   # 0=neutral, 1=hawkish, -1=dovish
    "projected_cuts_2024": 3
  }
}
```

---

## Implementation Code

### Step 1: ChromaDB Setup

```python
# backend/rag/chromadb_setup.py
import chromadb
from chromadb.config import Settings

def get_chroma_client():
    return chromadb.HttpClient(
        host="localhost",
        port=8001,
        settings=Settings(anonymized_telemetry=False)
    )

def initialize_collections(client):
    collections = [
        "market_news",
        "macro_indicators", 
        "earnings_filings",
        "volatility_events",
        "fed_communications",
        "analyst_research",
        "reddit_sentiment"
    ]
    for name in collections:
        client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    return {name: client.get_collection(name) for name in collections}
```

### Step 2: Historical Data Loader (One-Time Batch)

```python
# backend/rag/historical_loader.py
import yfinance as yf
from fredapi import Fred
import chromadb
from openai import OpenAI
from datetime import datetime, timedelta

openai_client = OpenAI()

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch embed texts using OpenAI text-embedding-3-small."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]

def load_yfinance_news(tickers: list[str], collection):
    """Load Yahoo Finance news for ticker list."""
    docs, metadatas, ids = [], [], []
    
    for ticker in tickers:
        t = yf.Ticker(ticker)
        for i, article in enumerate(t.news[:20]):  # 20 articles per ticker
            content = f"{article.get('title', '')}. {article.get('summary', '')}"
            docs.append(content)
            metadatas.append({
                "source": "yahoo_finance",
                "ticker": ticker,
                "published_at": str(article.get("providerPublishTime", "")),
                "url": article.get("link", ""),
                "event_type": "news"
            })
            ids.append(f"yf_{ticker}_{i}_{article.get('providerPublishTime','')}")
    
    embeddings = embed_texts(docs)
    collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
    print(f"Loaded {len(docs)} Yahoo Finance articles")

def load_fred_macro(fred_client: Fred, collection):
    """Load FRED macro indicator summaries."""
    series_map = {
        "FEDFUNDS": ("Fed Funds Rate", "interest_rates"),
        "CPIAUCSL": ("CPI Inflation", "inflation"),
        "UNRATE": ("Unemployment Rate", "employment"),
        "T10Y2Y": ("Yield Curve (10Y-2Y)", "yield_curve"),
        "VIXCLS": ("VIX Volatility Index", "volatility"),
        "GDP": ("US GDP Growth", "gdp"),
        "DGS10": ("10-Year Treasury Yield", "interest_rates"),
    }
    
    docs, metadatas, ids = [], [], []
    
    for series_id, (name, category) in series_map.items():
        data = fred_client.get_series(series_id, observation_start="2019-01-01")
        
        # Create monthly summary documents
        monthly = data.resample("M").last()
        for date, value in monthly.items():
            if pd.isna(value):
                continue
            doc = f"{name} was {value:.2f} as of {date.strftime('%B %Y')}."
            docs.append(doc)
            metadatas.append({
                "source": "fred",
                "series_id": series_id,
                "series_name": name,
                "date": date.strftime("%Y-%m-%d"),
                "value": float(value),
                "macro_category": category
            })
            ids.append(f"fred_{series_id}_{date.strftime('%Y%m')}")
    
    embeddings = embed_texts(docs)
    collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
    print(f"Loaded {len(docs)} FRED macro data points")
```

### Step 3: PyFlink Near-Real-Time Job

```python
# backend/flink/market_news_job.py
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
import json
import chromadb
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def process_news_stream():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    
    # Kafka source — consuming market.news topic
    kafka_source = KafkaSource.builder() \
        .set_bootstrap_servers("localhost:9092") \
        .set_topics("market.news") \
        .set_group_id("finsight-rag-consumer") \
        .set_starting_offsets(KafkaOffsetsInitializer.latest()) \
        .set_value_only_deserializer(SimpleStringSchema()) \
        .build()
    
    stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),
        "Kafka Market News Source"
    )
    
    # Enrich with sentiment + write to ChromaDB
    def enrich_and_store(raw_json: str):
        analyzer = SentimentIntensityAnalyzer()
        chroma = chromadb.HttpClient(host="localhost", port=8001)
        collection = chroma.get_collection("market_news")
        
        article = json.loads(raw_json)
        text = f"{article['title']}. {article.get('summary', '')}"
        
        sentiment = analyzer.polarity_scores(text)
        
        # Embed and store (batch in production)
        from openai import OpenAI
        client = OpenAI()
        embedding = client.embeddings.create(
            model="text-embedding-3-small", input=text
        ).data[0].embedding
        
        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "source": article.get("source", "unknown"),
                "tickers": ",".join(article.get("tickers", [])),
                "sentiment_compound": sentiment["compound"],
                "sentiment_label": "Bullish" if sentiment["compound"] > 0.05 else
                                   "Bearish" if sentiment["compound"] < -0.05 else "Neutral",
                "published_at": article.get("published_at", ""),
                "event_type": article.get("event_type", "news")
            }],
            ids=[f"news_{article.get('id', hash(text))}"]
        )
    
    stream.map(enrich_and_store)
    env.execute("Market News Sentiment Stream")

if __name__ == "__main__":
    process_news_stream()
```

### Step 4: RAG Query Module

```python
# backend/rag/query_engine.py
import chromadb
from openai import OpenAI

class MarketRAGEngine:
    def __init__(self, chroma_host="localhost", chroma_port=8001):
        self.chroma = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        self.openai = OpenAI()
        self.collections = [
            "market_news", "macro_indicators", "earnings_filings",
            "volatility_events", "fed_communications"
        ]
    
    def retrieve_context(self, query: str, n_results: int = 5) -> list[dict]:
        """Semantic search across all collections."""
        query_embedding = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=query
        ).data[0].embedding
        
        all_results = []
        for coll_name in self.collections:
            try:
                coll = self.chroma.get_collection(coll_name)
                results = coll.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, 3),
                    include=["documents", "metadatas", "distances"]
                )
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                ):
                    all_results.append({
                        "collection": coll_name,
                        "document": doc,
                        "metadata": meta,
                        "relevance_score": 1 - dist  # cosine similarity
                    })
            except Exception:
                continue
        
        # Sort by relevance, return top-K
        return sorted(all_results, key=lambda x: x["relevance_score"], reverse=True)[:n_results * 2]
    
    def build_context_prompt(self, query: str) -> str:
        """Build RAG-enhanced prompt for LLM."""
        docs = self.retrieve_context(query, n_results=10)
        
        context_blocks = []
        for i, doc in enumerate(docs, 1):
            meta = doc["metadata"]
            context_blocks.append(
                f"[Source {i} — {doc['collection']} | {meta.get('date', meta.get('published_at', 'N/A'))}]\n"
                f"{doc['document']}"
            )
        
        return f"""You are a financial analyst AI. Use the following retrieved market context to answer the query.

RETRIEVED MARKET CONTEXT:
{chr(10).join(context_blocks)}

USER QUERY: {query}

Provide a detailed, grounded analysis citing the sources above. Identify causal relationships between events and market movements."""
```

---

## Free MCP Servers for Financial Data

MCP (Model Context Protocol) servers allow AI agents to directly call tools. These are available for free:

### 1. `mcp-server-fetch` (Official Anthropic)
- **Repo**: `github.com/modelcontextprotocol/servers/tree/main/src/fetch`
- **Use**: Fetch any financial news URL, SEC filing URL in real-time
- **Config**: Add to MCP config, no API key needed

### 2. Yahoo Finance MCP (Community)
- **Repo**: Search `yahoo-finance-mcp` on GitHub/npm
- **Tools**: `get_stock_price`, `get_stock_history`, `get_stock_news`
- **Cost**: Free, uses yfinance under the hood

### 3. Alpha Vantage MCP
- **Search**: `alpha-vantage-mcp` on GitHub
- **Tools**: `get_market_news_sentiment`, `get_earnings`, `get_economic_indicator`
- **Requires**: Free Alpha Vantage API key

### 4. FRED MCP (Community)
- **Search**: `fred-mcp-server` on GitHub
- **Tools**: `get_economic_series`, `search_fred`, `get_releases`
- **Requires**: Free FRED API key

### 5. Brave Search MCP (Official Anthropic)
- **Repo**: `github.com/modelcontextprotocol/servers/tree/main/src/brave-search`
- **Use**: Real-time web search for market news
- **Requires**: Free Brave Search API key (1000 queries/month free)

### MCP Config Example (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-brave-search"],
      "env": { "BRAVE_API_KEY": "your_free_key" }
    },
    "yahoo-finance": {
      "command": "npx",
      "args": ["-y", "mcp-yahoo-finance"]
    }
  }
}
```

---

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FINSIGHT AI — RAG ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────────┘

FREE DATA SOURCES                  INGESTION LAYER
──────────────────                 ────────────────
yfinance (prices/news) ──────────► Python workers (Celery)
FRED API (macro) ────────────────► Scheduled every 15 min
Alpha Vantage (sentiment) ───────► API rate-limit aware
Finnhub (company news) ──────────► Dedup by URL hash
SEC EDGAR (filings) ─────────────► One-time + incremental
Reddit PRAW (retail mood) ───────► Streaming via Kafka
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │  Apache Kafka   │
                                   │  Topics:        │
                                   │  market.news    │
                                   │  market.prices  │
                                   │  market.macro   │
                                   │  market.filings │
                                   └────────┬────────┘
                                            │
FLINK PROCESSING LAYER                      ▼
──────────────────────         ┌────────────────────────┐
                               │   Apache Flink Cluster  │
                               │   ┌──────────────────┐  │
                               │   │ Job 1: News NLP  │  │
                               │   │ (VADER sentiment)│  │
                               │   └──────────────────┘  │
                               │   ┌──────────────────┐  │
                               │   │ Job 2: Volatility │  │
                               │   │ Event Detector   │  │
                               │   └──────────────────┘  │
                               │   ┌──────────────────┐  │
                               │   │ Job 3: Embedding │  │
                               │   │ Batcher (batch   │  │
                               │   │ 50 docs → OpenAI)│  │
                               │   └──────────────────┘  │
                               └────────────┬────────────┘
                                            │
VECTOR STORE                                ▼
────────────         ┌────────────────────────────────────┐
                     │           ChromaDB                  │
                     │  ┌─────────────────────────────┐   │
                     │  │ market_news collection       │   │
                     │  │ macro_indicators collection  │   │
                     │  │ earnings_filings collection  │   │
                     │  │ volatility_events collection │   │
                     │  │ fed_communications collection│   │
                     │  └─────────────────────────────┘   │
                     └──────────────┬─────────────────────┘
                                    │
AI AGENT LAYER                      ▼
──────────────   ┌────────────────────────────────────────┐
                 │      FinSight AI Agent (FastAPI)        │
                 │                                        │
                 │  User: "Why did tech drop this week?"  │
                 │          │                             │
                 │          ▼                             │
                 │  1. Embed query                        │
                 │  2. Semantic search ChromaDB           │
                 │  3. Retrieve top-10 context docs       │
                 │  4. Build RAG prompt                   │
                 │  5. LLM (Claude/GPT-4) generates       │
                 │     grounded analysis with citations   │
                 └────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase A: One-Time Historical Load (Week 1)

```bash
# 1. Install dependencies
pip install yfinance fredapi chromadb openai vaderSentiment sec-edgar-downloader praw

# 2. Start ChromaDB
docker run -d -p 8001:8000 chromadb/chroma

# 3. Run historical loader
python backend/rag/historical_loader.py --sources yfinance,fred,sec_edgar --years 5

# 4. Verify collection counts
python -c "
import chromadb
c = chromadb.HttpClient(host='localhost', port=8001)
for name in ['market_news','macro_indicators','earnings_filings']:
    coll = c.get_collection(name)
    print(f'{name}: {coll.count()} documents')
"
```

### Phase B: Near-Real-Time Pipeline (Week 2)

```bash
# 1. Start Kafka (via Docker Compose)
docker-compose up -d kafka zookeeper

# 2. Start Flink cluster
docker-compose up -d flink-jobmanager flink-taskmanager

# 3. Deploy Flink jobs
flink run -py backend/flink/market_news_job.py
flink run -py backend/flink/volatility_detector_job.py

# 4. Start data ingestion workers
celery -A backend.workers worker --loglevel=info
celery -A backend.workers beat --loglevel=info  # Scheduled tasks
```

### Phase C: RAG Integration with AI Agent (Week 3)

- Wire `MarketRAGEngine.build_context_prompt()` into the AI analysis endpoints
- Add `POST /api/rag/query` endpoint for direct semantic search
- Integrate retrieved context into Task 3.2 AI modules

---

## Docker Compose Addition

Add to your existing `docker-compose.yml`:

```yaml
services:
  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_HTTP_PORT=8000

  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on: [zookeeper]
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"

  flink-jobmanager:
    image: flink:1.18-python3
    command: jobmanager
    ports:
      - "8081:8081"
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager

  flink-taskmanager:
    image: flink:1.18-python3
    depends_on: [flink-jobmanager]
    command: taskmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=flink-jobmanager
      - TASK_MANAGER_NUMBER_OF_TASK_SLOTS=4

volumes:
  chroma_data:
```

---

## Dependencies to Add to `backend/requirements.txt`

```txt
# RAG / Vector Store
chromadb>=0.5.0
openai>=1.40.0

# Free Data Sources
yfinance>=0.2.40
fredapi>=0.5.1
finnhub-python>=2.4.19
praw>=7.7.1
sec-edgar-downloader>=5.0.0
newsapi-python>=0.2.7

# NLP / Sentiment
vaderSentiment>=3.3.2
nltk>=3.8.1

# Streaming
apache-flink>=1.18.0
kafka-python>=2.0.2
confluent-kafka>=2.4.0

# Scheduling
celery>=5.3.0
redis>=5.0.0

# Utilities
pandas>=2.0.0
```

---

## API Rate Limit Management

Since free tiers have limits, use a rate limiter:

```python
# backend/rag/rate_limiter.py
import time
from collections import defaultdict

class APIRateLimiter:
    """Token bucket rate limiter for free API tiers."""
    
    LIMITS = {
        "alpha_vantage": {"calls": 25, "period": 86400},    # 25/day
        "finnhub": {"calls": 60, "period": 60},             # 60/min
        "newsapi": {"calls": 100, "period": 86400},         # 100/day
        "fred": {"calls": 120, "period": 60},               # 120/min
        "yfinance": {"calls": 2000, "period": 86400},       # ~2000/day (unofficial)
    }
    
    def __init__(self):
        self._counts = defaultdict(int)
        self._windows = defaultdict(float)
    
    def can_call(self, api: str) -> bool:
        limit = self.LIMITS.get(api, {"calls": 100, "period": 60})
        now = time.time()
        
        if now - self._windows[api] > limit["period"]:
            self._counts[api] = 0
            self._windows[api] = now
        
        if self._counts[api] < limit["calls"]:
            self._counts[api] += 1
            return True
        return False
    
    def wait_if_needed(self, api: str):
        while not self.can_call(api):
            time.sleep(1)
```

---

## Expected ChromaDB Document Volumes (5-Year Historical Load)

| Collection | Estimated Documents | Source |
|---|---|---|
| market_news | 50,000 - 200,000 | Alpha Vantage + Finnhub + Yahoo |
| macro_indicators | 5,000 - 20,000 | FRED (50 series × 60 months) |
| earnings_filings | 10,000 - 50,000 | SEC EDGAR (S&P 500 × 20 quarters) |
| volatility_events | 1,000 - 5,000 | Flink detector |
| fed_communications | 500 - 2,000 | FOMC minutes + speeches |
| reddit_sentiment | 20,000 - 100,000 | r/investing + r/wallstreetbets |
| **Total** | **~90K - 400K docs** | |

Storage estimate: ~2-5 GB for embeddings + documents.

---

## Quick Start Checklist

- [ ] Register free API keys: Alpha Vantage, Finnhub, FRED, NewsAPI, Reddit
- [ ] Start ChromaDB via Docker
- [ ] Run `historical_loader.py` for 5-year batch load (takes 2-4 hours)
- [ ] Start Kafka + Flink via Docker Compose
- [ ] Deploy PyFlink jobs for near-real-time streaming
- [ ] Test RAG query: `engine.retrieve_context("Fed rate hike impact on tech")`
- [ ] Integrate `MarketRAGEngine` into AI analysis endpoints (Task 3.2)
- [ ] Add MCP servers (fetch, brave-search) to Claude config

---

**Document Version**: 1.0  
**Phase**: 3, Task 3.3  
**Created**: 2026-06-16  
**Status**: Architecture Design — Ready for Implementation
