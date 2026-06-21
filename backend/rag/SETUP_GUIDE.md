# RAG Setup & Data Loading Guide

Complete guide to set up ChromaDB and load 5+ years of financial data for FinSight AI.

## Prerequisites

- Python 3.10+
- Dependencies installed: `pip install -r backend/requirements.txt`
- Docker (for ChromaDB) OR native ChromaDB installation

## Step 1: Start ChromaDB

### Option A: Docker (Recommended)

```bash
docker run -d -p 8001:8000 \
  -e ALLOW_RESET=true \
  --name chromadb \
  chromadb/chroma:latest
```

### Option B: Native Installation

```bash
pip install chromadb
chromadb run --port 8001
```

### Option C: Python API (Embedded)

```python
import chromadb
client = chromadb.HttpClient(host="localhost", port=8001)
```

**Verify ChromaDB is running:**

```bash
curl http://localhost:8001/api/v1/heartbeat
# Should return: {"nanosecond heartbeat": XXXXX}
```

## Step 2: Configure API Keys

Create or update `backend/.env` with:

```bash
# REQUIRED: OpenAI API key (for embeddings)
OPENAI_API_KEY=sk-your_key_here

# OPTIONAL: FRED API key (for macro indicators)
FRED_API_KEY=your_fred_key

# OPTIONAL: Finnhub API key (for analyst data)
FINNHUB_API_KEY=your_finnhub_key
```

### Getting API Keys

1. **OpenAI API Key** (REQUIRED)
   - Visit: https://platform.openai.com/api-keys
   - Create new secret key
   - Cost: ~$0.02-0.05 per full data load

2. **FRED API Key** (Optional - for macro indicators)
   - Visit: https://fredaccount.stlouisfed.org/login/secure/
   - Register and create API key
   - Free

3. **Finnhub API Key** (Optional - for detailed analyst data)
   - Visit: https://finnhub.io/dashboard/api-key
   - Create API key
   - Free tier available

## Step 3: Load Financial Data

### Quick Start (50 top S&P 500 stocks, 5 years)

```bash
cd backend/rag
python load_financial_data.py
```

This loads:
- ✅ 5 years of daily OHLCV price data
- ✅ Dividend history
- ✅ Stock split events
- ✅ Earnings data
- ✅ Analyst recommendations
- ✅ Recent company news
- ✅ Macro economic indicators

**Estimated time:** 10-15 minutes (first run)

### Custom Configuration

Load specific tickers and time period:

```bash
cd backend/rag
python historical_loader.py \
  --tickers AAPL MSFT GOOGL AMZN TSLA META NVDA JPM JNJ V \
  --years 5 \
  --ohlcv --dividends --splits --earnings --analysts --news --macro
```

**Options:**
- `--tickers`: Space-separated list of stock symbols
- `--years`: Number of years of history (default: 5)
- `--ohlcv`: Load OHLCV data (default: True)
- `--dividends`: Load dividend data (default: True)
- `--splits`: Load stock split data (default: True)
- `--earnings`: Load earnings data (default: True)
- `--analysts`: Load analyst recommendations (default: True)
- `--news`: Load company news (default: True)
- `--macro`: Load macro indicators (default: True)

### Example: Single Stock, Detailed

```bash
python historical_loader.py \
  --tickers AAPL \
  --years 10 \
  --ohlcv --earnings --analysts --news
```

## Step 4: Validate Data

Check that data was loaded successfully:

```bash
cd backend/rag
python validate_data.py
```

**Output example:**

```
============================================================
ChromaDB Data Validation Report
============================================================

📊 Collection Statistics:

✅ ohlcv_data                    1,250 documents
✅ dividends_data                  342 documents
✅ splits_data                      15 documents
✅ earnings_data                   342 documents
✅ analyst_recommendations          50 documents
✅ market_news                    2,500 documents
✅ macro_indicators               2,100 documents
────────────────────────────────────────────────────
Total                            6,599 documents

[Sample documents and semantic search test...]
```

## Step 5: Use in Your Application

### Query the RAG System

```python
from rag.query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Retrieve relevant documents
context = engine.retrieve_context(
    query="Apple's recent earnings and analyst outlook",
    n_results=10
)

# Build RAG prompt for LLM
prompt = engine.build_context_prompt(
    query="Should I invest in Apple stock?"
)

# Use with LLM
from openai import OpenAI
client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}]
)
print(response.choices[0].message.content)
```

### Direct ChromaDB Access

```python
from rag.chromadb_setup import get_chroma_client, initialize_collections

chroma_client = get_chroma_client()
collections = initialize_collections(chroma_client)

# Query a collection
results = collections["ohlcv_data"].query(
    query_embeddings=[...],  # Embed your query with OpenAI
    n_results=5
)

print(results["documents"])
print(results["metadatas"])
```

## Monitoring & Maintenance

### Check Data Freshness

```bash
python validate_data.py
```

### Update Existing Data

Re-run the loader to upsert/update documents:

```bash
python load_financial_data.py
```

### Delete a Collection

```python
from rag.chromadb_setup import get_chroma_client
client = get_chroma_client()
client.delete_collection("ohlcv_data")
```

### Reset All Data

```python
from rag.chromadb_setup import get_chroma_client
client = get_chroma_client()
# Get all collections
client.reset()  # Reset entire database
```

## Troubleshooting

### "Failed to connect to ChromaDB"

```
❌ Failed to connect to ChromaDB: ...
   Make sure ChromaDB is running: chromadb run --port 8001
```

**Solution:**
- Start ChromaDB: `chromadb run --port 8001`
- Or check Docker: `docker ps | grep chromadb`
- Or verify port: `netstat -an | grep 8001`

### "Invalid API key" for OpenAI

```
AuthenticationError: Invalid API key provided
```

**Solution:**
- Verify key in `.env`: `echo $OPENAI_API_KEY`
- Get new key: https://platform.openai.com/api-keys
- Key format should be: `sk-...`

### "No data found for ticker"

```
Loading OHLCV data for ABC...
  No data found for ABC
```

**Solution:**
- Verify ticker is valid (e.g., `AAPL`, not `apple`)
- Check yfinance can fetch it: `python -c "import yfinance; yf.Ticker('ABC').history()"`
- Try a different ticker

### Slow Loading Speed

**Cause:** API rate limits or network latency

**Solutions:**
1. Add delays: Edit `historical_loader.py` to add `time.sleep(0.5)` between tickers
2. Load fewer tickers: `--tickers AAPL MSFT GOOGL`
3. Reduce years: `--years 2` instead of 5

### High OpenAI Costs

**Cause:** Embedding costs (~$0.02 per 1M tokens)

**Solutions:**
1. Use smaller batch: `--tickers AAPL MSFT` (2 stocks = ~$0.01)
2. Reduce years: `--years 2` (2 years of data)
3. Use alternative embeddings (see future roadmap in README.md)

## Performance Metrics

### Data Loading Times

| Operation | Time | Tickers |
|-----------|------|---------|
| OHLCV (5yr) | 2-3 min | 50 |
| Dividends | 1 min | 50 |
| Splits | <1 min | 50 |
| Earnings | 1 min | 50 |
| Analysts | 1 min | 50 |
| News | 1-2 min | 50 |
| Macro | 1 min | 7 series |
| **TOTAL** | **~10-15 min** | **50** |

### Collection Sizes

| Collection | Docs | Size (approx) | Example Query Time |
|-----------|------|---------------|--------------------|
| ohlcv_data | 1,250 | 2.5 MB | 50ms |
| dividends_data | 342 | 0.7 MB | 30ms |
| earnings_data | 342 | 0.7 MB | 30ms |
| analyst_recommendations | 50 | 0.1 MB | 20ms |
| market_news | 2,500 | 5 MB | 80ms |
| macro_indicators | 2,100 | 4 MB | 70ms |

### Cost Breakdown

| Component | Estimated Cost |
|-----------|----------------|
| OpenAI Embeddings (~100k tokens) | $0.02-0.05 |
| ChromaDB Storage | Free (localhost) |
| yfinance API | Free |
| FRED API | Free |
| **Total per load** | **~$0.03** |

## Next Steps

1. **Test RAG queries** → Run `validate_data.py`
2. **Integrate with API** → Use `query_engine.MarketRAGEngine` in your FastAPI routes
3. **Set up automatic updates** → Use Celery/scheduled tasks to refresh data weekly
4. **Monitor costs** → Track OpenAI embeddings usage
5. **Optimize retrieval** → Add semantic search tuning based on user queries

## Documentation

- **README.md** - Architecture and system overview
- **historical_loader.py** - Data loading functions
- **query_engine.py** - RAG retrieval interface
- **chromadb_setup.py** - ChromaDB initialization
