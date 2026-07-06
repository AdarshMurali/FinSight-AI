#!/usr/bin/env python3
"""
FinSight AI — AWS ChromaDB Historical Data Loader
Runs on the Flink EC2, writes to the ChromaDB EC2 over private VPC network.

Usage:
    nohup python load_rag_aws.py > /home/ec2-user/logs/rag_loader.log 2>&1 &

Config (all read from .env — change IPs there, not here):
    CHROMA_HOST    → ChromaDB EC2 IP         (default: 13.206.225.80)
    CHROMA_PORT    → ChromaDB port            (default: 8001)
    OPENAI_API_KEY → for text-embedding-3-small
    FRED_API_KEY   → for macro + Fed series
    FINNHUB_API_KEY→ (not used here, Flink handles live news)

Collections loaded here (Flink owns market_news + volatility_events):
    ohlcv_data, dividends_data, splits_data, earnings_data,
    analyst_recommendations, macro_indicators, fed_communications, earnings_filings
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# ── Load .env from the ec2-flink directory ───────────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
    print(f"[config] Loaded .env from {ENV_PATH}")
else:
    load_dotenv()
    print("[config] .env not found at script dir, trying cwd")

# ── Add script directory to path so historical_loader.py can be imported ─────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historical_loader import (
    embed_texts,
    load_ohlcv_data,
    load_dividends_data,
    load_splits_data,
    load_earnings_data,
    load_analyst_recommendations,
    load_company_news,
    load_fred_macro,
    load_fed_communications,
    load_sec_edgar,
)
from chromadb_setup import get_chroma_client, initialize_collections


# ── Ticker lists ─────────────────────────────────────────────────────────────
# All 135 securities in the database.
# Futures (=F) and forex (=X) are valid for OHLCV via yfinance
# but excluded from equity-specific APIs (SEC EDGAR, earnings, analysts).

ALL_TICKERS = [
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "ASML",
    "AMD", "INTC", "CSCO", "ADBE", "CRM", "SHOP", "UBER",
    # Healthcare / Biotech
    "JNJ", "LLY", "UNH", "ABBV", "MRK", "TMO", "ABT", "ISRG",
    "GILD", "AMGN", "REGN", "VRTX", "DHR", "CVS", "NVO",
    # Financials
    "JPM", "BAC", "GS", "MS", "BLK", "C", "WFC", "AXP",
    "COF", "SCHW", "SPGI", "CME", "ICE",
    # Consumer
    "AMZN", "TSLA", "WMT", "HD", "MCD", "PG", "KO", "PEP",
    "COST", "TGT", "NKE", "SBUX", "CL", "DIS", "NFLX",
    # Energy
    "XOM", "CVX", "COP", "SLB", "HAL", "OXY", "DVN", "EOG",
    "MPC", "KMI",
    # Industrials / Materials
    "BA", "HON", "CAT", "DE", "GE", "LMT", "RTX", "NOC",
    "UPS", "FDX", "APD", "LIN", "FCX", "NEM", "SHW",
    # Telecom / Utilities
    "VZ", "CMCSA", "TMUS", "NEE", "DUK", "SO", "EXC", "AEP",
    # Real Estate
    "AMT", "CCI", "EQIX", "SPG", "PLD",
    # Diversified / Other
    "SAP", "TSM", "ABNB", "SPOT",
    # ETFs
    "SPY", "QQQ", "VTI", "IWM", "EEM", "EFA",
    "GLD", "SLV", "AGG", "BND", "HYG", "LQD", "VNQ",
    "TLT", "XLE", "XLF", "XLI", "XLK", "XLP", "XLV", "XLY",
    # Futures (OHLCV only)
    "CL=F", "GC=F", "NG=F", "SI=F", "ZC=F", "ZW=F",
    # Forex (OHLCV only)
    "EURUSD=X", "GBPUSD=X", "USDCAD=X", "USDJPY=X",
]

# Deduplicate while preserving order (guards against accidental repeat entries)
ALL_TICKERS = list(dict.fromkeys(ALL_TICKERS))

# Equity-only: no futures/forex — used for dividends, splits, earnings, analysts, SEC EDGAR
EQUITY_TICKERS = [t for t in ALL_TICKERS if "=F" not in t and "=X" not in t]


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def section(title):
    print(f"\n{'='*60}")
    print(f"[{ts()}] {title}")
    print(f"{'='*60}")


def run():
    section("FinSight AI — AWS ChromaDB Historical Data Loader")
    print(f"  CHROMA_HOST : {os.getenv('CHROMA_HOST', '13.206.225.80')}")
    print(f"  CHROMA_PORT : {os.getenv('CHROMA_PORT', '8001')}")
    print(f"  All tickers : {len(ALL_TICKERS)}")
    print(f"  Equity only : {len(EQUITY_TICKERS)}")

    # ── Connect to ChromaDB ───────────────────────────────────────────────
    section("Connecting to ChromaDB")
    try:
        client = get_chroma_client()
        collections = initialize_collections(client)
        print(f"[{ts()}] Connected. Collections ready.")
    except Exception as e:
        print(f"[{ts()}] ERROR: Cannot connect to ChromaDB: {e}")
        sys.exit(1)

    # ── 1. OHLCV (all tickers incl. futures + forex) ─────────────────────
    section("1/8  OHLCV Data — 5yr monthly summaries (all 135 tickers)")
    try:
        load_ohlcv_data(ALL_TICKERS, collections["ohlcv_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] OHLCV failed: {e}")

    # ── 2. Dividends ──────────────────────────────────────────────────────
    section("2/8  Dividend History (equity + ETFs)")
    try:
        load_dividends_data(EQUITY_TICKERS, collections["dividends_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] Dividends failed: {e}")

    # ── 3. Stock Splits ───────────────────────────────────────────────────
    section("3/8  Stock Split History (equity + ETFs)")
    try:
        load_splits_data(EQUITY_TICKERS, collections["splits_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] Splits failed: {e}")

    # ── 4. Earnings ───────────────────────────────────────────────────────
    section("4/8  Earnings Data (equity + ETFs)")
    try:
        load_earnings_data(EQUITY_TICKERS, collections["earnings_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] Earnings failed: {e}")

    # ── 5. Analyst Recommendations ────────────────────────────────────────
    section("5/8  Analyst Recommendations (equity only)")
    try:
        load_analyst_recommendations(EQUITY_TICKERS, collections["analyst_recommendations"])
    except Exception as e:
        print(f"[{ts()}] Analyst recs failed: {e}")

    # ── 6. FRED Macro Indicators ──────────────────────────────────────────
    section("6/8  FRED Macro Indicators (40+ series, 2019–present)")
    try:
        load_fred_macro(collections["macro_indicators"])
    except Exception as e:
        print(f"[{ts()}] FRED macro failed: {e}")

    # ── 7. Fed Communications ─────────────────────────────────────────────
    section("7/8  Fed Communications & Balance Sheet (FRED)")
    try:
        load_fed_communications(collections["fed_communications"])
    except Exception as e:
        print(f"[{ts()}] Fed comms failed: {e}")

    # ── 8. SEC EDGAR XBRL Filings ─────────────────────────────────────────
    section("8/8  SEC EDGAR XBRL Financial Filings (stocks only, skips ETFs gracefully)")
    try:
        load_sec_edgar(EQUITY_TICKERS, collections["earnings_filings"], years=5)
    except Exception as e:
        print(f"[{ts()}] SEC EDGAR failed: {e}")

    # ── Final doc counts ──────────────────────────────────────────────────
    section("DONE — Collection Document Counts")
    for name, col in collections.items():
        try:
            count = col.count()
            print(f"  {name:<30} {count:>6} docs")
        except Exception as e:
            print(f"  {name:<30} ERROR: {e}")

    print(f"\n[{ts()}] Load complete.")


if __name__ == "__main__":
    run()
