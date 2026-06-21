# Test the RAG system with various queries
from query_engine import MarketRAGEngine

engine = MarketRAGEngine()

# Test queries
test_queries = [
    "Apple earnings growth and iPhone sales",
    "Federal Reserve interest rate policy",
    "stock market volatility today",
    "earnings reports for tech companies"
]

for query in test_queries:
    print(f"\n{'='*50}")
    print(f"Query: {query}")
    print('='*50)

    try:
        results = engine.retrieve_context(query, n_results=3)
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"Collection: {result['collection']}")
            print(f"Document: {result['document'][:150]}...")
            print(f"Relevance: {result['relevance_score']:.3f}")
            print(f"Metadata: {result['metadata']}")
    except Exception as e:
        print(f"Error: {e}")