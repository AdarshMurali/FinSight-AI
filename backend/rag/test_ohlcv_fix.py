#!/usr/bin/env python3
"""Test the fixed OHLCV loading"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

ticker = "AAPL"
end_date = datetime.now()
start_date = end_date - timedelta(days=365*5)

print(f"Testing OHLCV fix for {ticker}...")

try:
    hist = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"),
                      end=end_date.strftime("%Y-%m-%d"), progress=False)

    print(f"[OK] Downloaded {hist.shape[0]} rows")
    print(f"  Columns before fix: {hist.columns.tolist()}")

    # Apply the fix
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = [col[0] if isinstance(col, tuple) else col for col in hist.columns]

    print(f"  Columns after fix: {hist.columns.tolist()}")

    # Rename to lowercase
    hist.columns = [str(col).lower() for col in hist.columns]

    print(f"  Columns after lowercase: {hist.columns.tolist()}")

    # Test resampling
    monthly = hist.resample('ME').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    print(f"[OK] Resampled to {monthly.shape[0]} monthly records")
    print(f"  First month:")
    print(monthly.iloc[0])

    # Generate document
    row = monthly.iloc[0]
    date = monthly.index[0]
    doc = (f"{ticker} monthly OHLCV: "
          f"Open ${row['open']:.2f}, High ${row['high']:.2f}, "
          f"Low ${row['low']:.2f}, Close ${row['close']:.2f}, "
          f"Volume {int(row['volume']):,} shares in {date.strftime('%B %Y')}")

    print(f"\n[OK] Generated document:")
    print(f"  {doc}")

    print(f"\n[SUCCESS] OHLCV fix is working correctly!")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
