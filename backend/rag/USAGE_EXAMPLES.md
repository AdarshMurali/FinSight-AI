# ChromaDB RAG - Usage Examples

Complete code examples for using the financial data RAG system in your FinSight AI application.

## Table of Contents

1. [Basic Query Engine Setup](#basic-query-engine-setup)
2. [Simple Semantic Search](#simple-semantic-search)
3. [RAG with LLM Integration](#rag-with-llm-integration)
4. [Direct ChromaDB Queries](#direct-chromadb-queries)
5. [FastAPI Integration](#fastapi-integration)
6. [Advanced Scenarios](#advanced-scenarios)

## Basic Query Engine Setup

```python
from rag.query_engine import MarketRAGEngine

# Initialize the RAG engine
engine = MarketRAGEngine()

# The engine will:
# - Connect to ChromaDB on localhost:8001
# - Initialize embeddings with OpenAI
# - Set up access to all collections
```

## Simple Semantic Search

### Example 1: Find All Apple-Related Documents

```python
from rag.query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Retrieve relevant documents
results = engine.retrieve_context(
    query="Apple Inc stock performance",
    n_results=10
)

# Results format:
# [
#   {
#       "collection": "ohlcv_data",
#       "document": "AAPL monthly OHLCV: Open $150.23...",
#       "metadata": {"ticker": "AAPL", "date": "2024-01-31", ...},
#       "relevance_score": 0.95
#   },
#   ...
# ]

# Print results
for result in results:
    print(f"[{result['relevance_score']:.2f}] {result['collection']}")
    print(f"  {result['document'][:100]}...")
    print(f"  Date: {result['metadata'].get('date', 'N/A')}")
    print()
```

### Example 2: Search for Dividend Information

```python
engine = MarketRAGEngine()

results = engine.retrieve_context(
    query="Apple dividend payment history recent",
    n_results=5
)

# Filter to only dividend collection
dividends = [r for r in results if r['collection'] == 'dividends_data']

for div in dividends:
    print(f"{div['document']}")
    print(f"  Amount: {div['metadata'].get('amount', 'N/A')}")
```

### Example 3: Analyst Ratings and Price Targets

```python
engine = MarketRAGEngine()

results = engine.retrieve_context(
    query="What are analysts saying about Apple Microsoft Google",
    n_results=15
)

# Group by ticker
by_ticker = {}
for result in results:
    ticker = result['metadata'].get('ticker', 'UNKNOWN')
    if ticker not in by_ticker:
        by_ticker[ticker] = []
    by_ticker[ticker].append(result)

# Display by ticker
for ticker, results in sorted(by_ticker.items()):
    print(f"\n{ticker}:")
    for result in results:
        if 'analyst' in result['collection']:
            print(f"  {result['document']}")
```

## RAG with LLM Integration

### Example 1: Investment Analysis with GPT-4

```python
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

engine = MarketRAGEngine()
openai_client = OpenAI()

# User query
query = "Should I invest in Apple stock? What's the analyst consensus?"

# Build RAG prompt
rag_prompt = engine.build_context_prompt(query)

# Call GPT-4
response = openai_client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a financial analyst AI. Analyze market data and provide investment insights."
        },
        {
            "role": "user",
            "content": rag_prompt
        }
    ],
    temperature=0.7,
    max_tokens=1000
)

# Print analysis
analysis = response.choices[0].message.content
print("Investment Analysis:")
print("=" * 60)
print(analysis)
```

### Example 2: Market Trend Report

```python
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

engine = MarketRAGEngine()
client = OpenAI()

# Query market data
query = "Tech sector performance earnings growth recent trends"
rag_prompt = engine.build_context_prompt(query)

# Generate report
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "system",
            "content": "You are a financial report writer. Create concise, data-driven market analysis."
        },
        {
            "role": "user",
            "content": f"Write a brief market analysis report based on this context:\n{rag_prompt}"
        }
    ]
)

print(response.choices[0].message.content)
```

### Example 3: Portfolio Analysis

```python
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

engine = MarketRAGEngine()
client = OpenAI()

# Portfolio tickers
portfolio = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

# Analyze each holding
for ticker in portfolio:
    query = f"{ticker} recent earnings analyst recommendations dividend"
    context = engine.retrieve_context(query, n_results=5)

    # Summarize
    context_text = "\n".join([c['document'] for c in context])

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": f"Briefly analyze {ticker} based on:\n{context_text}"
            }
        ]
    )

    print(f"\n{ticker} Analysis:")
    print(response.choices[0].message.content)
    print("-" * 40)
```

## Direct ChromaDB Queries

### Example 1: Query Specific Collection

```python
from rag.chromadb_setup import get_chroma_client, initialize_collections
from openai import OpenAI

# Initialize
chroma_client = get_chroma_client()
collections = initialize_collections(chroma_client)
openai_client = OpenAI()

# Embed query
query = "Microsoft stock price movement"
query_embedding = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=[query]
).data[0].embedding

# Query OHLCV collection directly
ohlcv_results = collections["ohlcv_data"].query(
    query_embeddings=[query_embedding],
    n_results=10,
    include=["documents", "metadatas", "distances"]
)

# Display results
print(f"Found {len(ohlcv_results['documents'][0])} OHLCV records:")
for doc, meta, dist in zip(
    ohlcv_results["documents"][0],
    ohlcv_results["metadatas"][0],
    ohlcv_results["distances"][0]
):
    relevance = 1 - dist
    print(f"[{relevance:.3f}] {doc}")
    print(f"  Date: {meta.get('date')}, Ticker: {meta.get('ticker')}")
```

### Example 2: Get Collection Statistics

```python
from rag.chromadb_setup import get_chroma_client, initialize_collections

chroma_client = get_chroma_client()
collections = initialize_collections(chroma_client)

# Print collection stats
print("Collection Statistics:")
print("-" * 40)

total = 0
for coll_name, collection in collections.items():
    count = collection.count()
    total += count
    status = "OK" if count > 0 else "EMPTY"
    print(f"{coll_name:<25} {count:>6} docs [{status}]")

print("-" * 40)
print(f"{'TOTAL':<25} {total:>6} docs")
```

### Example 3: Raw Collection Access

```python
from rag.chromadb_setup import get_chroma_client, initialize_collections

chroma_client = get_chroma_client()
collections = initialize_collections(chroma_client)

# Get raw collection
news_collection = collections["market_news"]

# Peek at data
results = news_collection.peek(limit=5)

print("Recent news documents:")
for doc, meta in zip(results["documents"], results["metadatas"]):
    print(f"Ticker: {meta.get('ticker')}")
    print(f"Date: {meta.get('published_at')}")
    print(f"Title: {doc}")
    print()
```

## FastAPI Integration

### Example 1: Basic Market Analysis Endpoint

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

app = FastAPI(title="FinSight RAG API")
rag_engine = MarketRAGEngine()
openai_client = OpenAI()

class AnalysisRequest(BaseModel):
    query: str
    n_results: int = 10
    use_llm: bool = True

class AnalysisResponse(BaseModel):
    query: str
    market_context: list
    analysis: str = None

@app.post("/api/v1/analyze")
async def analyze(request: AnalysisRequest):
    try:
        # Get context
        context = rag_engine.retrieve_context(
            request.query,
            n_results=request.n_results
        )

        # Build response
        response = AnalysisResponse(
            query=request.query,
            market_context=[
                {
                    "document": c["document"],
                    "collection": c["collection"],
                    "date": c["metadata"].get("date", "N/A"),
                    "relevance": c["relevance_score"]
                }
                for c in context
            ]
        )

        # Optional: Generate LLM analysis
        if request.use_llm:
            rag_prompt = rag_engine.build_context_prompt(request.query)
            llm_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": rag_prompt}]
            )
            response.analysis = llm_response.choices[0].message.content

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Example 2: Stock-Specific Endpoint

```python
from fastapi import FastAPI
from rag.query_engine import MarketRAGEngine

app = FastAPI()
rag_engine = MarketRAGEngine()

@app.get("/api/v1/stock/{ticker}")
async def get_stock_analysis(ticker: str):
    """Get comprehensive analysis for a stock"""
    
    query = f"{ticker} stock price earnings analyst recommendations dividend"
    
    context = rag_engine.retrieve_context(query, n_results=15)
    
    # Group by data type
    by_type = {}
    for item in context:
        data_type = item["metadata"].get("data_type", "unknown")
        if data_type not in by_type:
            by_type[data_type] = []
        by_type[data_type].append(item)
    
    return {
        "ticker": ticker,
        "data_by_type": by_type,
        "total_documents": len(context)
    }
```

### Example 3: Streaming LLM Analysis

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

app = FastAPI()
rag_engine = MarketRAGEngine()
openai_client = OpenAI()

@app.post("/api/v1/analyze-stream")
async def analyze_stream(query: str):
    """Stream LLM analysis with RAG context"""
    
    rag_prompt = rag_engine.build_context_prompt(query)

    def generate():
        stream = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": rag_prompt}],
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    return StreamingResponse(generate(), media_type="text/plain")
```

## Advanced Scenarios

### Scenario 1: Portfolio Rebalancing Analysis

```python
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

engine = MarketRAGEngine()
client = OpenAI()

# Current portfolio allocation
portfolio = {
    "AAPL": 0.30,
    "MSFT": 0.25,
    "GOOGL": 0.20,
    "NVDA": 0.15,
    "JNJ": 0.10
}

# Analyze each position
analysis = {}
for ticker, weight in portfolio.items():
    query = f"{ticker} recent performance analyst rating earnings growth potential"
    context = engine.retrieve_context(query, n_results=8)

    prompt = f"""
    Analyze {ticker} (current portfolio weight: {weight*100:.0f}%)
    
    Market context:
    {chr(10).join([c['document'] for c in context])}
    
    Should we increase, maintain, or decrease this position?
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    analysis[ticker] = response.choices[0].message.content

# Print recommendations
for ticker, recommendation in analysis.items():
    print(f"\n{ticker}:")
    print(recommendation)
```

### Scenario 2: Risk Assessment

```python
from rag.query_engine import MarketRAGEngine
from openai import OpenAI

engine = MarketRAGEngine()
client = OpenAI()

# Risk query
query = "market volatility stock splits earnings surprises analyst downgrades"

context = engine.retrieve_context(query, n_results=20)

# Categorize risk factors
risk_factors = {
    "macro_indicators": [c for c in context if "macro" in c['collection']],
    "volatility_events": [c for c in context if "split" in str(c)],
    "analyst_downgrades": [c for c in context if "analyst" in c['collection']],
    "earnings_surprises": [c for c in context if "earnings" in c['collection']]
}

# Generate risk report
context_str = "\n".join([c['document'] for c in context])

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{
        "role": "user",
        "content": f"""
        Generate a risk assessment report based on these market indicators:
        
        {context_str}
        
        Include:
        1. Current market risk level (low/medium/high)
        2. Key risk factors
        3. Recommended hedge positions
        """
    }]
)

print("Market Risk Assessment Report")
print("=" * 60)
print(response.choices[0].message.content)
```

### Scenario 3: Sector Performance Comparison

```python
from rag.query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Compare tech stocks
tech_stocks = ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]

print("Tech Sector Comparison")
print("=" * 60)

for ticker in tech_stocks:
    query = f"{ticker} quarterly earnings earnings growth revenue performance"
    context = engine.retrieve_context(query, n_results=5)

    print(f"\n{ticker}:")
    print("-" * 40)
    for item in context:
        if "earnings" in item['collection'] or "ohlcv" in item['collection']:
            print(f"  * {item['document'][:80]}...")
```

## Error Handling

```python
from rag.query_engine import MarketRAGEngine
import logging

logger = logging.getLogger(__name__)

def safe_rag_query(query: str, n_results: int = 10):
    """Safely query RAG engine with error handling"""
    try:
        engine = MarketRAGEngine()
        results = engine.retrieve_context(query, n_results=n_results)
        return results, None
    except ConnectionError as e:
        logger.error(f"ChromaDB connection error: {e}")
        return None, "ChromaDB server not running"
    except AuthenticationError as e:
        logger.error(f"OpenAI authentication error: {e}")
        return None, "Invalid OpenAI API key"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None, str(e)

# Usage
results, error = safe_rag_query("Apple stock performance")
if error:
    print(f"Error: {error}")
else:
    for result in results:
        print(result['document'])
```

## Performance Optimization

### Caching Queries

```python
from functools import lru_cache
from rag.query_engine import MarketRAGEngine

class CachedRAGEngine:
    def __init__(self):
        self.engine = MarketRAGEngine()

    @lru_cache(maxsize=128)
    def get_context(self, query: str, n_results: int = 10):
        """Cache RAG results"""
        return tuple(
            self.engine.retrieve_context(query, n_results)
        )

# Usage
cached_engine = CachedRAGEngine()
# First call - fetches from ChromaDB
results1 = cached_engine.get_context("Apple earnings")
# Second call - returns cached result
results2 = cached_engine.get_context("Apple earnings")
```

---

For more information, see:
- README.md - Technical architecture
- SETUP_GUIDE.md - Setup and troubleshooting
- QUICKSTART.md - Quick reference
