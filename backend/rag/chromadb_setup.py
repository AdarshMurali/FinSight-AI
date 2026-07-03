# backend/rag/chromadb_setup.py
import os
import chromadb
from chromadb.config import Settings

def get_chroma_client():
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8001"))
    return chromadb.HttpClient(
        host=host,
        port=port,
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
        "reddit_sentiment",
        "ohlcv_data",
        "dividends_data",
        "splits_data",
        "earnings_data",
        "analyst_recommendations"
    ]
    for name in collections:
        client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    return {name: client.get_collection(name) for name in collections}