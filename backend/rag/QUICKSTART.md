# FinSight AI RAG - Quick Start (2 Minutes)

## TL;DR

```bash
# 1. Start ChromaDB
chromadb run --port 8001

# 2. Set up .env (copy from .env.example)
# Add OPENAI_API_KEY from https://platform.openai.com/api-keys

# 3. Load data (one command)
cd backend/rag
python load_financial_data.py

# 4. Validate (check if it worked)
python validate_data.py

# Done! Now use in your code:
from query_engine import MarketRAGEngine
engine = MarketRAGEngine()
docs = engine.retrieve_context("Apple stock performance")
```

## What Gets Loaded

| Type | Amount | Source |
|------|--------|--------|
| Stocks | 50 (S&P 500 top) | yfinance |
| Years of data | 5 years | historical |
| OHLCV records | ~1,250 per stock | yfinance |
| News articles | ~50 per stock | Yahoo Finance |
| Earnings dates | ~20 per stock | yfinance |
| Analyst ratings | Latest | yfinance |
| Macro indicators | 7 economic series | FRED |

**Total documents:** ~6,600 documents embedded with OpenAI

## Files Created

✅ **historical_loader.py** - Main data loading functions
✅ **load_financial_data.py** - One-command loader script  
✅ **validate_data.py** - Inspect loaded data
✅ **README.md** - Complete technical documentation
✅ **SETUP_GUIDE.md** - Detailed setup instructions
✅ **QUICKSTART.md** - This file

## Key Functions

### Load Data
```python
from historical_loader import (
    load_ohlcv_data,
    load_dividends_data,
    load_earnings_data,
    load_analyst_recommendations,
    load_company_news
)

# Load specific data type
load_ohlcv_data(
    tickers=["AAPL", "MSFT"],
    collection=collections["ohlcv_data"],
    years=5
)
```

### Query Data
```python
from query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Semantic search across all collections
results = engine.retrieve_context(
    query="Apple earnings and stock performance",
    n_results=10
)

# Build RAG prompt for LLM
prompt = engine.build_context_prompt(
    query="Should I buy Apple stock?"
)

# results[i] has:
# - document: text
# - metadata: {ticker, date, source, ...}
# - relevance_score: 0-1
```

### Validate Data
```python
from validate_data import validate_collections, test_query

# Check all collections
validate_collections()

# Test semantic search
test_query("Apple stock performance and earnings growth")
```

## Configuration

**.env file:**
```
OPENAI_API_KEY=sk-...           # Required
FRED_API_KEY=...                # Optional (for macro data)
FINNHUB_API_KEY=...             # Optional (for Finnhub)
```

## Command-Line Usage

**Load all data (default: 50 stocks, 5 years):**
```bash
python load_financial_data.py
```

**Load specific stocks:**
```bash
python historical_loader.py \
  --tickers AAPL MSFT GOOGL \
  --years 5 \
  --ohlcv --earnings --analysts --news
```

**Check what's loaded:**
```bash
python validate_data.py
```

## Data Collections

All data is stored in 7 ChromaDB collections:

1. **ohlcv_data** - Price movements (Open, High, Low, Close, Volume)
2. **dividends_data** - Dividend payments
3. **splits_data** - Stock split events
4. **earnings_data** - Earnings release dates
5. **analyst_recommendations** - Analyst ratings and price targets
6. **market_news** - Recent company news
7. **macro_indicators** - Economic indicators (Fed Funds Rate, CPI, VIX, etc.)

## Embedding Details

- **Model:** `text-embedding-3-small` (OpenAI)
- **Dimensions:** 1536
- **Distance Metric:** Cosine similarity
- **Cost:** ~$0.02-0.05 per full load

## Estimated Times

- **First load:** 10-15 minutes
- **Query response:** <100ms (semantic search)
- **Update existing data:** 10-15 minutes (re-run loader)

## Example: Integration with FastAPI

```python
from fastapi import FastAPI
from rag.query_engine import MarketRAGEngine

app = FastAPI()
rag_engine = MarketRAGEngine()

@app.post("/api/analyze")
async def analyze(query: str):
    # Get market context
    context_docs = rag_engine.retrieve_context(query, n_results=10)
    
    # Build RAG prompt
    rag_prompt = rag_engine.build_context_prompt(query)
    
    # Call LLM
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": rag_prompt}]
    )
    
    return {
        "query": query,
        "market_context": context_docs,
        "analysis": response.choices[0].message.content
    }
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Failed to connect to ChromaDB" | Start: `chromadb run --port 8001` |
| "Invalid API key" | Get key from https://platform.openai.com/api-keys |
| "No documents in collection" | Re-run: `python load_financial_data.py` |
| "Slow queries" | Check ChromaDB is running and network connection |

## Next Steps

1. ✅ Load data: `python load_financial_data.py`
2. ✅ Validate: `python validate_data.py`
3. ✅ Integrate: Import `MarketRAGEngine` in your FastAPI app
4. ✅ Deploy: Add RAG routes to your backend API
5. ✅ Monitor: Track OpenAI API costs

---

**Full documentation:** See README.md and SETUP_GUIDE.md

**Questions?** Check the troubleshooting sections or review the code comments.
