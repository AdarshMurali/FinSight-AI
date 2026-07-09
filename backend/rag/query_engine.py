# backend/rag/query_engine.py
import chromadb
import os
from datetime import date, datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Recency blend: final_score = (1 - RECENCY_WEIGHT) * relevance + RECENCY_WEIGHT * recency
# Soft nudge, not a hard filter — a strongly-relevant old document (e.g. "2008 crisis"
# matching a stress-test query) can still outrank a marginally-relevant recent one.
RECENCY_WEIGHT = 0.3
RECENCY_HALF_LIFE_DAYS = 180  # score halves every ~6 months of age


_DATE_KEYS = ("date", "published_at", "event_date", "filed_date", "detected_at", "period_end", "period")


def _parse_doc_date(meta: dict) -> date | None:
    """Best-effort parse of whichever date-like key this collection's metadata uses."""
    raw = next((meta[k] for k in _DATE_KEYS if meta.get(k)), None)
    if not raw:
        return None
    raw = str(raw)
    try:
        if len(raw) == 7:  # "YYYY-MM" (e.g. macro_indicators periods)
            raw = f"{raw}-01"
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _recency_score(doc_date: date | None) -> float:
    if doc_date is None:
        return 0.4  # neutral — don't punish or favor docs with no parseable date
    age_days = max((date.today() - doc_date).days, 0)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)

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
                    relevance = 1 - dist  # cosine similarity
                    recency = _recency_score(_parse_doc_date(meta))
                    final_score = (1 - RECENCY_WEIGHT) * relevance + RECENCY_WEIGHT * recency
                    all_results.append({
                        "collection": coll_name,
                        "document": doc,
                        "metadata": meta,
                        "relevance_score": relevance,
                        "recency_score": round(recency, 3),
                        "final_score": final_score,
                    })
            except Exception:
                continue

        # Sort by blended relevance+recency score, return top-K
        return sorted(all_results, key=lambda x: x["final_score"], reverse=True)[:n_results * 2]
    
    def build_context_prompt(self, query: str) -> str:
        """Build RAG-enhanced prompt for LLM."""
        docs = self.retrieve_context(query, n_results=10)
        
        context_blocks = []
        for i, doc in enumerate(docs, 1):
            meta = doc["metadata"]
            doc_date = _parse_doc_date(meta)
            context_blocks.append(
                f"[Source {i} — {doc['collection']} | {doc_date.isoformat() if doc_date else 'N/A'}]\n"
                f"{doc['document']}"
            )
        
        return f"""You are a financial analyst AI. Use the following retrieved market context to answer the query.

RETRIEVED MARKET CONTEXT:
{chr(10).join(context_blocks)}

USER QUERY: {query}

Provide a detailed, grounded analysis citing the sources above. Identify causal relationships between events and market movements."""