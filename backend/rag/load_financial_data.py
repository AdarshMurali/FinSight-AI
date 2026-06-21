#!/usr/bin/env python3
"""
Convenience script to load 5+ years of financial data to ChromaDB.
Supports OHLCV, dividends, splits, earnings, analyst recommendations, and news.
"""
import sys
from pathlib import Path
from historical_loader import (
    get_chroma_client,
    initialize_collections,
    load_ohlcv_data,
    load_dividends_data,
    load_splits_data,
    load_earnings_data,
    load_analyst_recommendations,
    load_company_news,
    load_fred_macro
)

# Default S&P 500 index components (top 50)
DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B",
    "JPM", "JNJ", "V", "WMT", "PG", "MA", "INTC", "NFLX",
    "MCD", "DIS", "KO", "PEP", "ABT", "TMO", "MRK", "IBM",
    "CSCO", "CAT", "F", "GM", "BA", "HON", "UNP", "AXP",
    "SPG", "XOM", "CVX", "COP", "MPC", "PSX", "VLO", "EQR",
    "VZ", "T", "TMUS", "DELL", "ORCL", "AMD", "PYPL", "ADBE",
    "AVGO", "INTU"
]

def main():
    print("=" * 60)
    print("FinSight AI - Financial Data Loader for ChromaDB")
    print("=" * 60)

    # Initialize ChromaDB
    print("\n[*] Initializing ChromaDB client...")
    try:
        chroma_client = get_chroma_client()
        collections = initialize_collections(chroma_client)
        print("[+] ChromaDB initialized successfully")
    except Exception as e:
        print(f"[-] Failed to connect to ChromaDB: {e}")
        print("   Make sure ChromaDB is running: chromadb run --port 8001")
        sys.exit(1)

    # Load data
    tickers = DEFAULT_TICKERS
    years = 5

    print(f"\n[*] Loading {years} years of data for {len(tickers)} tickers:")
    print(f"   {', '.join(tickers[:10])}...")

    try:
        print("\n[1] Loading OHLCV data (Open-High-Low-Close-Volume)...")
        load_ohlcv_data(tickers, collections["ohlcv_data"], years=years)

        print("\n[2] Loading dividend history...")
        load_dividends_data(tickers, collections["dividends_data"], years=years)

        print("\n[3] Loading stock split history...")
        load_splits_data(tickers, collections["splits_data"], years=years)

        print("\n[4] Loading earnings data...")
        load_earnings_data(tickers, collections["earnings_data"], years=years)

        print("\n[5] Loading analyst recommendations...")
        load_analyst_recommendations(tickers, collections["analyst_recommendations"])

        print("\n[6] Loading company news...")
        load_company_news(tickers, collections["market_news"])

        print("\n[7] Loading macro indicators...")
        load_fred_macro(collections["macro_indicators"])

        print("\n" + "=" * 60)
        print("[+] ALL DATA LOADED SUCCESSFULLY!")
        print("=" * 60)
        print("\nData is now ready for RAG queries. Collections initialized:")
        for coll_name in collections.keys():
            count = collections[coll_name].count()
            print(f"  * {coll_name}: {count} documents")

    except Exception as e:
        print(f"\n[-] Error during data loading: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
