# backend/rag/query_engine.py
import chromadb
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class MarketRAGEngine:
    def __init__(self, chroma_host=None, chroma_port=None):
        host = chroma_host or os.getenv("CHROMA_HOST", "localhost")
        port = chroma_port or int(os.getenv("CHROMA_PORT", "8001"))
        self.chroma = chromadb.HttpClient(host=host, port=port)
        openai_key = os.getenv("OPENAI_API_KEY")
        self.openai = OpenAI(api_key=openai_key)
        self.collections = [
            "market_news", "macro_indicators", "earnings_filings",
            "volatility_events", "fed_communications",
            "analyst_research", "ohlcv_data", "dividends_data",
            "earnings_data", "analyst_recommendations",
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