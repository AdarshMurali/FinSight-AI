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