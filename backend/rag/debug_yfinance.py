#!/usr/bin/env python3
"""
Debug script to understand yfinance data structure
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

print("=" * 60)
print("YFinance Data Structure Debug")
print("=" * 60)

# Test with one ticker
ticker = "AAPL"
end_date = datetime.now()
start_date = end_date - timedelta(days=365*5)

print(f"\nDownloading {ticker} from {start_date.date()} to {end_date.date()}...")

try:
    hist = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"),
                      end=end_date.strftime("%Y-%m-%d"), progress=False)

    print(f"\nDataFrame shape: {hist.shape}")
    print(f"Column names: {hist.columns.tolist()}")
    print(f"Column types: {hist.columns}")
    print(f"Is MultiIndex: {isinstance(hist.columns, pd.MultiIndex)}")

    if isinstance(hist.columns, pd.MultiIndex):
        print(f"MultiIndex levels: {hist.columns.nlevels}")
        print(f"Level 0: {hist.columns.get_level_values(0).unique().tolist()}")
        print(f"Level 1: {hist.columns.get_level_values(1).unique().tolist()}")

    print(f"\nFirst few rows:")
    print(hist.head(3))

    print(f"\nDtype of each column:")
    print(hist.dtypes)

    print(f"\nIndex type: {type(hist.index)}")
    print(f"Index dtype: {hist.index.dtype}")
    print(f"Index is timezone-aware: {hist.index.tz is not None}")

    # Test resampling
    print(f"\n\nTesting resample to monthly...")
    monthly = hist.resample('ME').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    print(f"Monthly shape: {monthly.shape}")
    print(f"Monthly head:")
    print(monthly.head(3))

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

# Test dividends
print("\n" + "=" * 60)
print("Testing Dividends")
print("=" * 60)

try:
    t = yf.Ticker(ticker)
    dividends = t.dividends

    print(f"\nDividends type: {type(dividends)}")
    print(f"Dividends empty: {dividends.empty if dividends is not None else 'None'}")

    if dividends is not None and not dividends.empty:
        print(f"Dividends shape: {dividends.shape}")
        print(f"Index type: {type(dividends.index)}")
        print(f"Index dtype: {dividends.index.dtype}")
        print(f"Index is timezone-aware: {dividends.index.tz is not None if hasattr(dividends.index, 'tz') else 'N/A'}")
        print(f"\nFirst 5 dividends:")
        print(dividends.head(5))

        # Test filtering
        start_date_ts = pd.Timestamp(start_date)
        end_date_ts = pd.Timestamp(end_date)

        print(f"\nAttempting to filter...")
        print(f"Start date: {start_date_ts}")
        print(f"End date: {end_date_ts}")

        if dividends.index.tz is not None:
            print(f"Dividends are timezone-aware, converting dates...")
            start_date_ts = pd.Timestamp(start_date, tz=dividends.index.tz)
            end_date_ts = pd.Timestamp(end_date, tz=dividends.index.tz)

        filtered = dividends[(dividends.index >= start_date_ts) & (dividends.index <= end_date_ts)]
        print(f"Filtered shape: {filtered.shape}")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()

# Test news
print("\n" + "=" * 60)
print("Testing News")
print("=" * 60)

try:
    t = yf.Ticker(ticker)
    news = t.news

    print(f"\nNews type: {type(news)}")
    print(f"News length: {len(news) if news else 'None'}")

    if news:
        print(f"\nFirst news item:")
        print(f"Keys: {news[0].keys() if isinstance(news[0], dict) else 'Not a dict'}")
        print(f"Content: {news[0]}")
    else:
        print("No news found")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
