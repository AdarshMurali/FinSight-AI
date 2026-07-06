#!/usr/bin/env python3
"""
Re-run only the 4 collections that failed on the first pass due to duplicate SLB ticker.
FRED macro, Fed comms, SEC EDGAR already loaded — skipped here.

Usage:
    nohup python rerun_failed.py > /home/ec2-user/logs/rerun_failed.log 2>&1 &
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historical_loader import (
    load_ohlcv_data,
    load_dividends_data,
    load_earnings_data,
    load_analyst_recommendations,
)
from chromadb_setup import get_chroma_client, initialize_collections


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

ALL_TICKERS    = list(dict.fromkeys(ALL_TICKERS))
EQUITY_TICKERS = [t for t in ALL_TICKERS if "=F" not in t and "=X" not in t]


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def section(title):
    print(f"\n{'='*60}")
    print(f"[{ts()}] {title}")
    print(f"{'='*60}")


def run():
    section("Re-run failed collections (OHLCV, Dividends, Earnings, Analyst Recs)")
    print(f"  CHROMA_HOST : {os.getenv('CHROMA_HOST', '13.206.225.80')}")
    print(f"  All tickers : {len(ALL_TICKERS)}")
    print(f"  Equity only : {len(EQUITY_TICKERS)}")

    client = get_chroma_client()
    collections = initialize_collections(client)
    print(f"[{ts()}] Connected. Collections ready.")

    section("1/4  OHLCV Data — 5yr monthly summaries")
    try:
        load_ohlcv_data(ALL_TICKERS, collections["ohlcv_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] OHLCV failed: {e}")

    section("2/4  Dividend History")
    try:
        load_dividends_data(EQUITY_TICKERS, collections["dividends_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] Dividends failed: {e}")

    section("3/4  Earnings Data")
    try:
        load_earnings_data(EQUITY_TICKERS, collections["earnings_data"], years=5)
    except Exception as e:
        print(f"[{ts()}] Earnings failed: {e}")

    section("4/4  Analyst Recommendations")
    try:
        load_analyst_recommendations(EQUITY_TICKERS, collections["analyst_recommendations"])
    except Exception as e:
        print(f"[{ts()}] Analyst recs failed: {e}")

    section("DONE — Final Collection Counts")
    for name, col in collections.items():
        try:
            count = col.count()
            print(f"  {name:<30} {count:>6} docs")
        except Exception as e:
            print(f"  {name:<30} ERROR: {e}")

    print(f"\n[{ts()}] Re-run complete.")


if __name__ == "__main__":
    run()
