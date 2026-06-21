# FinSight AI - RAG Data Loader

This module handles loading 5+ years of financial data into ChromaDB for semantic search and RAG (Retrieval Augmented Generation) capabilities.

## Overview

The RAG system ingests and embeds the following financial data:

- **OHLCV Data**: 5 years of daily Open-High-Low-Close-Volume price data
- **Dividends**: Historical dividend payments
- **Stock Splits**: Historical stock split events
- **Earnings**: Earnings release dates and quarterly financial data
- **Analyst Recommendations**: Current analyst ratings and price targets
- **Company News**: Recent news articles for each stock
- **Macro Indicators**: FRED economic data (Fed Funds Rate, CPI, Unemployment, etc.)

## Quick Start

### 1. Ensure ChromaDB is Running

Start ChromaDB on port 8001:

```bash
chromadb run --port 8001
```

### 2. Set Environment Variables

Create a `.env` file in the `backend/` directory with:

```env
OPENAI_API_KEY=sk-...                    # Required for embeddings
FRED_API_KEY=...                         # Optional, for macro indicators (get from FRED)
FINNHUB_API_KEY=...                      # Optional, for Finnhub data
```

### 3. Load Data

Run the loader:

```bash
python backend/rag/load_financial_data.py
```

This will load 5 years of data for the top 50 S&P 500 stocks into ChromaDB.

**To customize tickers:**

```bash
python backend/rag/historical_loader.py \
  --tickers AAPL MSFT GOOGL AMZN TSLA \
  --years 5 \
  --ohlcv --dividends --splits --earnings --analysts --news --macro
```

### 4. Validate Loaded Data

Check that data was loaded successfully:

```bash
python backend/rag/validate_data.py
```

This displays:
- Count of documents in each collection
- Sample documents with metadata
- Test semantic search across collections

## Architecture

### Collections

The system creates these ChromaDB collections:

| Collection | Purpose | Data Source |
|-----------|---------|-------------|
| `ohlcv_data` | Price movements, trends | yfinance |
| `dividends_data` | Shareholder returns | yfinance |
| `splits_data` | Stock split events | yfinance |
| `earnings_data` | Earnings releases, quarterly results | yfinance |
| `analyst_recommendations` | Ratings, price targets | yfinance |
| `market_news` | Recent company news | yfinance |
| `macro_indicators` | Economic indicators | FRED |

### Embedding Strategy

- **Model**: OpenAI's `text-embedding-3-small` (1536 dimensions)
- **Distance Metric**: Cosine similarity
- **Processing**: Batched (50 texts per API call to manage costs)

### Data Transformation

Raw financial data is transformed into natural language documents for embedding:

**OHLCV Example:**
```
AAPL monthly OHLCV: Open $150.23, High $155.67, Low $148.90, Close $153.44, Volume 1,234,567 shares in January 2024
```

**Dividend Example:**
```
AAPL paid dividend of $0.24 per share on February 15, 2024
```

**Earnings Example:**
```
AAPL earnings report released on January 30, 2024: EPS Estimate $2.10
```

**Analyst Example:**
```
AAPL: Analyst consensus is BUY with a target price of $200 based on 45 analyst opinions
```

## Usage in RAG

Use the `MarketRAGEngine` to retrieve relevant context:

```python
from query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Retrieve relevant documents for a query
context = engine.retrieve_context(
    query="What is Apple's recent performance and analyst outlook?",
    n_results=10
)

# Build RAG prompt for LLM
prompt = engine.build_context_prompt(
    query="Should I invest in Apple stock?"
)
```

## File Structure

```
backend/rag/
├── chromadb_setup.py           # Initialize ChromaDB client/collections
├── historical_loader.py         # Core data loading functions
├── load_financial_data.py       # Convenience runner script
├── validate_data.py            # Data validation & inspection
├── query_engine.py             # RAG query interface
├── test_rag.py                 # Tests
└── README.md                   # This file
```

## Data Loading Performance

Approximate loading times (first run):

- **OHLCV**: ~2-3 min for 50 stocks × 5 years
- **Dividends**: ~1 min
- **Splits**: <1 min
- **Earnings**: ~1 min
- **Analyst Recommendations**: ~1 min
- **News**: ~1 min per 50 articles
- **Macro Indicators**: ~1 min

**Total**: ~10-15 minutes for full 50-stock dataset

## API Costs

- **Embeddings**: ~$0.02-0.05 per full load (~100k documents)
  - Using `text-embedding-3-small` at $0.02 per 1M tokens
- **Data Sources**: Free (yfinance, FRED)

## Troubleshooting

### ChromaDB Connection Error
```
❌ Failed to connect to ChromaDB
```
**Solution**: Start ChromaDB: `chromadb run --port 8001`

### Rate Limit Errors
```
RateLimitError: Rate limit exceeded
```
**Solution**: 
- yfinance has implicit rate limits (~2000 requests/hour)
- Add delays between ticker loads: `time.sleep(0.5)`
- Use proxies if available

### Missing Embedding Dimensions
```
ValueError: dimension mismatch
```
**Solution**: Ensure all texts are embedded with the same model (`text-embedding-3-small`)

### No Data in Collections
```
⚠️ ohlcv_data: 0 documents
```
**Solution**: Check that yfinance can fetch data:
```python
import yfinance as yf
hist = yf.download('AAPL', start='2020-01-01', end='2025-01-01')
print(len(hist))  # Should be > 1000
```

## Updating Data

To refresh with new data (e.g., monthly):

```bash
# Option 1: Delete and recreate collections
python -c "
from chromadb_setup import get_chroma_client
client = get_chroma_client()
client.delete_collection('ohlcv_data')
client.delete_collection('market_news')
# ... delete others
"

# Option 2: Re-run loader (will upsert/update existing docs)
python backend/rag/load_financial_data.py
```

## Future Enhancements

- [ ] Incremental updates (load only new data since last run)
- [ ] Real-time streaming data via Kafka/Flink
- [ ] Alternative embedding models (e.g., Voyage, Cohere)
- [ ] Hybrid search (semantic + keyword/BM25)
- [ ] Document reranking after retrieval
- [ ] Time-aware retrieval (weight recent documents)
- [ ] Finnhub integration for detailed fundamentals
- [ ] SEC Edgar for 10-K/10-Q filings
- [ ] Sentiment analysis on news articles
