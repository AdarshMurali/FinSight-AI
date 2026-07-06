# backend/rag/historical_loader.py
import yfinance as yf
from fredapi import Fred
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os
import time
import requests
from datetime import datetime, timedelta
import pandas as pd
import json
from chromadb_setup import get_chroma_client, initialize_collections

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
fred_key = os.getenv("FRED_API_KEY")
finnhub_key = os.getenv("FINNHUB_API_KEY")

openai_client = OpenAI(api_key=openai_key)
fred_client = Fred(api_key=fred_key) if fred_key else None


def embed_texts(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """Batch embed texts using OpenAI text-embedding-3-small with chunking."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=batch
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def load_ohlcv_data(tickers: list[str], collection, years: int = 5):
    """Load 5+ years of OHLCV data for given tickers."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*years)

    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading OHLCV data for {ticker}...")
        try:
            hist = yf.download(ticker, start=start_date.strftime("%Y-%m-%d"),
                             end=end_date.strftime("%Y-%m-%d"), progress=False)

            if hist.empty:
                print(f"  No data found for {ticker}")
                continue

            # Handle MultiIndex columns - yfinance returns MultiIndex even for single ticker
            if isinstance(hist.columns, pd.MultiIndex):
                # Flatten MultiIndex columns - keep only the first level (Close, High, etc)
                hist.columns = [col[0] if isinstance(col, tuple) else col for col in hist.columns]

            # Rename columns to lowercase for consistency
            hist.columns = [str(col).lower() for col in hist.columns]

            # Create monthly summaries for embedding
            monthly = hist.resample('ME').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            })

            ticker_docs = 0
            for date, row in monthly.iterrows():
                if pd.isna(row['close']):
                    continue
                doc = (f"{ticker} monthly OHLCV: "
                      f"Open ${row['open']:.2f}, High ${row['high']:.2f}, "
                      f"Low ${row['low']:.2f}, Close ${row['close']:.2f}, "
                      f"Volume {int(row['volume']):,} shares in {date.strftime('%B %Y')}")
                docs.append(doc)
                metadatas.append({
                    "source": "yfinance",
                    "ticker": ticker,
                    "date": date.strftime("%Y-%m-%d"),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume']),
                    "data_type": "ohlcv"
                })
                ids.append(f"ohlcv_{ticker}_{date.strftime('%Y%m%d')}")
                ticker_docs += 1

            print(f"  Loaded {ticker_docs} OHLCV records for {ticker}")
        except Exception as e:
            print(f"  Error loading {ticker}: {e}")

    if docs:
        # Deduplicate by ID (guards against duplicate tickers in caller list)
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total OHLCV records to ChromaDB")


def load_dividends_data(tickers: list[str], collection, years: int = 5):
    """Load dividend history for given tickers."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*years)

    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading dividend data for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            dividends = t.dividends

            if dividends is None or dividends.empty:
                print(f"  No dividends found for {ticker}")
                continue

            # Filter to date range - convert dividend index to UTC for comparison
            if dividends.index.tz is not None:
                # Convert timezone-aware index to UTC, then remove timezone for comparison
                div_index_utc = dividends.index.tz_convert('UTC').tz_localize(None)
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                mask = (div_index_utc >= start_ts) & (div_index_utc <= end_ts)
                dividends = dividends[mask]
            else:
                # Simple comparison for naive datetime
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                dividends = dividends[(dividends.index >= start_ts) & (dividends.index <= end_ts)]

            for date, amount in dividends.items():
                doc = f"{ticker} paid dividend of ${amount:.2f} per share on {date.strftime('%B %d, %Y')}"
                docs.append(doc)
                metadatas.append({
                    "source": "yfinance",
                    "ticker": ticker,
                    "date": date.strftime("%Y-%m-%d"),
                    "amount": float(amount),
                    "data_type": "dividend",
                    "event_type": "dividend"
                })
                ids.append(f"div_{ticker}_{date.strftime('%Y%m%d')}")

            print(f"  Found {len(dividends)} dividend records for {ticker}")
        except Exception as e:
            print(f"  Error loading dividends for {ticker}: {e}")

    if docs:
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total dividend records to ChromaDB")


def load_splits_data(tickers: list[str], collection, years: int = 5):
    """Load stock split history for given tickers."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*years)

    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading split data for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            splits = t.splits

            if splits is None or splits.empty:
                print(f"  No splits found for {ticker}")
                continue

            # Filter to date range - convert splits index to UTC for comparison
            if splits.index.tz is not None:
                # Convert timezone-aware index to UTC, then remove timezone for comparison
                splits_index_utc = splits.index.tz_convert('UTC').tz_localize(None)
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                mask = (splits_index_utc >= start_ts) & (splits_index_utc <= end_ts)
                splits = splits[mask]
            else:
                # Simple comparison for naive datetime
                start_ts = pd.Timestamp(start_date)
                end_ts = pd.Timestamp(end_date)
                splits = splits[(splits.index >= start_ts) & (splits.index <= end_ts)]

            for date, ratio in splits.items():
                doc = f"{ticker} underwent a {ratio:.1f} stock split on {date.strftime('%B %d, %Y')}"
                docs.append(doc)
                metadatas.append({
                    "source": "yfinance",
                    "ticker": ticker,
                    "date": date.strftime("%Y-%m-%d"),
                    "split_ratio": float(ratio),
                    "data_type": "split",
                    "event_type": "stock_split"
                })
                ids.append(f"split_{ticker}_{date.strftime('%Y%m%d')}")

            print(f"  Found {len(splits)} split records for {ticker}")
        except Exception as e:
            print(f"  Error loading splits for {ticker}: {e}")

    if docs:
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total split records to ChromaDB")


def load_earnings_data(tickers: list[str], collection, years: int = 5):
    """Load earnings dates and data for given tickers."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*years)
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)

    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading earnings data for {ticker}...")
        ticker_docs = 0
        try:
            t = yf.Ticker(ticker)
            info = t.info

            # Get quarterly financials metadata
            try:
                if hasattr(t, 'quarterly_financials') and t.quarterly_financials is not None and not t.quarterly_financials.empty:
                    for col in t.quarterly_financials.columns[:4]:  # Last 4 quarters
                        try:
                            date = col if isinstance(col, pd.Timestamp) else pd.Timestamp(col)
                            # Remove timezone for naive comparison
                            if date.tz is not None:
                                date = date.tz_localize(None)
                            if start_ts <= date <= end_ts:
                                doc = f"{ticker} reported quarterly financials for {date.strftime('%B %Y')}"
                                docs.append(doc)
                                metadatas.append({
                                    "source": "yfinance",
                                    "ticker": ticker,
                                    "date": date.strftime("%Y-%m-%d"),
                                    "data_type": "quarterly_financials",
                                    "event_type": "earnings_report"
                                })
                                ids.append(f"qtr_{ticker}_{date.strftime('%Y%m%d')}")
                                ticker_docs += 1
                        except:
                            continue
            except:
                pass

            # Get earnings dates from info
            try:
                if 'earningsDate' in info and info['earningsDate']:
                    earnings_date = info['earningsDate']
                    if isinstance(earnings_date, (list, tuple)):
                        earnings_date = earnings_date[0]
                    earnings_date = pd.Timestamp(earnings_date)
                    # Remove timezone for naive comparison
                    if earnings_date.tz is not None:
                        earnings_date = earnings_date.tz_localize(None)
                    if start_ts <= earnings_date <= end_ts:
                        doc = f"{ticker} has upcoming earnings report on {earnings_date.strftime('%B %d, %Y')}"
                        docs.append(doc)
                        metadatas.append({
                            "source": "yfinance",
                            "ticker": ticker,
                            "date": earnings_date.strftime("%Y-%m-%d"),
                            "data_type": "earnings",
                            "event_type": "earnings_report"
                        })
                        ids.append(f"earn_{ticker}_{earnings_date.strftime('%Y%m%d')}")
                        ticker_docs += 1
            except:
                pass

            print(f"  Found {ticker_docs} earnings records for {ticker}")
        except Exception as e:
            print(f"  Error loading earnings for {ticker}: {e}")

    if docs:
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total earnings records to ChromaDB")


def load_analyst_recommendations(tickers: list[str], collection):
    """Load analyst recommendations for given tickers using yfinance."""
    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading analyst recommendations for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            info = t.info

            # Extract analyst rating info
            if 'recommendationKey' in info:
                recommendation = info.get('recommendationKey', 'N/A').upper()
                target_price = info.get('targetMeanPrice', 'N/A')
                num_analysts = info.get('numberOfAnalystOpinions', 0)

                doc = (f"{ticker}: Analyst consensus is {recommendation} with a target price of ${target_price} "
                      f"based on {num_analysts} analyst opinions")
                docs.append(doc)
                metadatas.append({
                    "source": "yfinance",
                    "ticker": ticker,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "recommendation": recommendation,
                    "target_price": float(target_price) if target_price != 'N/A' else None,
                    "num_analysts": int(num_analysts),
                    "data_type": "analyst_recommendation",
                    "event_type": "analyst_rating"
                })
                ids.append(f"analyst_{ticker}_{datetime.now().strftime('%Y%m%d')}")

            # Alternative: use analyst_ratings if available
            if hasattr(t, 'analyst_ratings') and t.analyst_ratings is not None:
                try:
                    ratings = t.analyst_ratings.tail(1)
                    for idx, row in ratings.iterrows():
                        doc = (f"{ticker} analyst ratings: {row.get('strong_buy', 0)} Strong Buy, "
                              f"{row.get('buy', 0)} Buy, {row.get('hold', 0)} Hold, "
                              f"{row.get('sell', 0)} Sell, {row.get('strong_sell', 0)} Strong Sell")
                        docs.append(doc)
                        metadatas.append({
                            "source": "yfinance",
                            "ticker": ticker,
                            "date": str(idx),
                            "strong_buy": int(row.get('strong_buy', 0)),
                            "buy": int(row.get('buy', 0)),
                            "hold": int(row.get('hold', 0)),
                            "sell": int(row.get('sell', 0)),
                            "strong_sell": int(row.get('strong_sell', 0)),
                            "data_type": "analyst_ratings",
                            "event_type": "analyst_rating"
                        })
                        ids.append(f"ratings_{ticker}_{str(idx)[:10]}")
                except:
                    pass

            print(f"  Found {len([d for d in docs if ticker in d])} analyst records for {ticker}")
        except Exception as e:
            print(f"  Error loading analyst recommendations for {ticker}: {e}")

    if docs:
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total analyst recommendation records to ChromaDB")


def load_company_news(tickers: list[str], collection):
    """Load recent company news for given tickers."""
    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        print(f"Loading news for {ticker}...")
        try:
            t = yf.Ticker(ticker)
            news = t.news

            if not news:
                print(f"  No news found for {ticker}")
                continue

            ticker_articles = 0
            for i, article in enumerate(news[:50]):  # Load up to 50 articles
                try:
                    # Handle new news structure with nested 'content' dict
                    if isinstance(article, dict):
                        # Try to get content from nested structure
                        content = article.get('content', {})
                        if isinstance(content, dict):
                            title = content.get('title', '')
                            summary = content.get('summary', '')
                            pub_date = content.get('pubDate', '')
                            provider = content.get('provider', {})
                            publisher = provider.get('displayName', '') if isinstance(provider, dict) else str(provider)
                            url = content.get('canonicalUrl', {})
                            if isinstance(url, dict):
                                url = url.get('url', '')
                        else:
                            # Fall back to old structure
                            title = article.get('title', '')
                            summary = article.get('summary', '')
                            pub_date = article.get('publishedDate', '')
                            publisher = article.get('publisher', '')
                            url = article.get('link', '')
                    else:
                        continue

                    if not title or not title.strip():
                        continue

                    # Create document
                    doc = f"{title}: {summary}" if summary else title
                    docs.append(doc)
                    metadatas.append({
                        "source": "yahoo_finance_news",
                        "ticker": ticker,
                        "title": title,
                        "publisher": publisher,
                        "url": url if url else "",
                        "published_at": str(pub_date),
                        "data_type": "news",
                        "event_type": "news"
                    })
                    ids.append(f"news_{ticker}_{i}_{str(pub_date)[:10]}")
                    ticker_articles += 1

                except Exception as e:
                    continue

            print(f"  Found {ticker_articles} news articles for {ticker}")
        except Exception as e:
            print(f"  Error loading news for {ticker}: {e}")

    if docs:
        seen: dict[str, tuple] = {}
        for d, m, i in zip(docs, metadatas, ids):
            if i not in seen:
                seen[i] = (d, m)
        docs      = [v[0] for v in seen.values()]
        metadatas = [v[1] for v in seen.values()]
        ids       = list(seen.keys())
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            embeddings = embed_texts(docs[i:i+batch_size])
            collection.upsert(documents=docs[i:i+batch_size], embeddings=embeddings,
                              metadatas=metadatas[i:i+batch_size], ids=ids[i:i+batch_size])
        print(f"Loaded {len(docs)} total news articles to ChromaDB")


def _build_fred_doc(series_id: str, name: str, category: str, date, value: float,
                    prev_value: float = None, year_ago_value: float = None, unit: str = "") -> str:
    """Build a rich natural-language document for a FRED data point."""
    unit_str = unit if unit else ""
    val_str = f"{value:.2f}{unit_str}"

    doc = f"{name} was {val_str} in {date.strftime('%B %Y')}."

    # Month-over-month change
    if prev_value is not None and not pd.isna(prev_value) and prev_value != 0:
        mom_chg = value - prev_value
        mom_pct = (mom_chg / abs(prev_value)) * 100
        direction = "up" if mom_chg > 0 else "down"
        doc += f" This is {direction} {abs(mom_pct):.2f}% from the prior month ({prev_value:.2f}{unit_str})."

    # Year-over-year change
    if year_ago_value is not None and not pd.isna(year_ago_value) and year_ago_value != 0:
        yoy_chg = value - year_ago_value
        yoy_pct = (yoy_chg / abs(year_ago_value)) * 100
        direction = "up" if yoy_chg > 0 else "down"
        doc += f" Year-over-year it is {direction} {abs(yoy_pct):.2f}% from {year_ago_value:.2f}{unit_str}."

    # Contextual thresholds
    if series_id in ("CPIAUCSL", "PCEPILFE", "PCEPI"):
        if value > 2.0:
            doc += f" Inflation is above the Federal Reserve's 2% target."
        elif value <= 2.0:
            doc += f" Inflation is at or below the Federal Reserve's 2% target."

    if series_id == "FEDFUNDS":
        if value >= 5.0:
            doc += " The Fed Funds Rate is in restrictive territory."
        elif value <= 0.25:
            doc += " The Fed Funds Rate is near zero, indicating accommodative monetary policy."

    if series_id == "UNRATE":
        if value >= 6.0:
            doc += " Unemployment is elevated, signaling labor market weakness."
        elif value <= 4.0:
            doc += " Unemployment is low, indicating a tight labor market."

    if series_id == "T10Y2Y":
        if value < 0:
            doc += f" The yield curve is inverted, a historically reliable recession indicator."
        elif value > 1.5:
            doc += f" The yield curve is steep, suggesting expectations of economic growth."

    if series_id == "VIXCLS":
        if value >= 30:
            doc += f" VIX above 30 signals high market fear and elevated volatility."
        elif value <= 15:
            doc += f" VIX below 15 reflects market complacency and low perceived risk."

    if series_id == "BAMLH0A0HYM2":
        if value >= 600:
            doc += f" High yield spreads above 600bps indicate stress in credit markets."
        elif value <= 300:
            doc += f" Tight high yield spreads signal strong risk appetite."

    return doc


def load_fred_macro(collection):
    """Load comprehensive FRED macro time series into the macro_indicators collection."""
    if not fred_client:
        print("FRED API key not configured, skipping macro data")
        return

    # 40+ FRED series grouped by macro category
    series_map = {
        # --- Monetary Policy / Interest Rates ---
        "FEDFUNDS":   ("Effective Federal Funds Rate", "interest_rates", "%"),
        "DGS1MO":     ("1-Month Treasury Yield", "interest_rates", "%"),
        "DGS3MO":     ("3-Month Treasury Yield", "interest_rates", "%"),
        "DGS6MO":     ("6-Month Treasury Yield", "interest_rates", "%"),
        "DGS1":       ("1-Year Treasury Yield", "interest_rates", "%"),
        "DGS2":       ("2-Year Treasury Yield", "interest_rates", "%"),
        "DGS5":       ("5-Year Treasury Yield", "interest_rates", "%"),
        "DGS10":      ("10-Year Treasury Yield", "interest_rates", "%"),
        "DGS30":      ("30-Year Treasury Yield", "interest_rates", "%"),
        "T10Y2Y":     ("Yield Curve Spread (10Y minus 2Y)", "yield_curve", "%"),
        "T10Y3M":     ("Yield Curve Spread (10Y minus 3M)", "yield_curve", "%"),
        "T10YIE":     ("10-Year Breakeven Inflation Rate", "inflation_expectations", "%"),
        # --- Inflation ---
        "CPIAUCSL":   ("Consumer Price Index (CPI All Items)", "inflation", ""),
        "CPILFESL":   ("Core CPI (Excluding Food and Energy)", "inflation", ""),
        "PCEPI":      ("PCE Price Index", "inflation", ""),
        "PCEPILFE":   ("Core PCE Price Index (Fed's Preferred Inflation Gauge)", "inflation", ""),
        "PPIFIS":     ("Producer Price Index (PPI Final Demand)", "inflation", ""),
        # --- Employment ---
        "UNRATE":     ("Unemployment Rate", "employment", "%"),
        "U6RATE":     ("U-6 Underemployment Rate (Broadest Measure)", "employment", "%"),
        "PAYEMS":     ("Total Nonfarm Payrolls", "employment", "K"),
        "ICSA":       ("Initial Jobless Claims (Weekly)", "employment", ""),
        "CIVPART":    ("Labor Force Participation Rate", "employment", "%"),
        "EMRATIO":    ("Employment-Population Ratio", "employment", "%"),
        "JTSJOL":     ("Job Openings (JOLTS)", "employment", "K"),
        # --- Growth / GDP ---
        "GDP":        ("US Nominal GDP", "gdp", "B$"),
        "GDPC1":      ("US Real GDP (Inflation-Adjusted)", "gdp", "B$"),
        "GDPCA":      ("US Real GDP Growth Rate (Annual)", "gdp", "%"),
        # --- Consumer / Spending ---
        "UMCSENT":    ("University of Michigan Consumer Sentiment Index", "consumer_sentiment", ""),
        "RSAFS":      ("US Retail Sales (Advance)", "consumer_spending", "M$"),
        "PSAVERT":    ("Personal Saving Rate", "consumer_spending", "%"),
        # --- Housing ---
        "CSUSHPISA":  ("Case-Shiller US Home Price Index", "housing", ""),
        "MORTGAGE30US": ("30-Year Fixed Mortgage Rate", "housing", "%"),
        "HOUST":      ("US Housing Starts", "housing", "K"),
        "PERMIT":     ("US Building Permits", "housing", "K"),
        # --- Money Supply ---
        "M2SL":       ("M2 Money Supply", "money_supply", "B$"),
        "BOGMBASE":   ("Monetary Base", "money_supply", "B$"),
        # --- Credit / Market Stress ---
        "VIXCLS":     ("CBOE VIX Volatility Index", "volatility", ""),
        "BAMLH0A0HYM2": ("US High Yield Corporate Bond Spread (OAS)", "credit_spreads", "bps"),
        "BAMLC0A0CM": ("US Investment Grade Corporate Bond Spread (OAS)", "credit_spreads", "bps"),
        "TEDRATE":    ("TED Spread (LIBOR minus T-Bill)", "credit_spreads", "%"),
        # --- Commodities & FX ---
        "DCOILWTICO": ("WTI Crude Oil Price", "commodities", "$/bbl"),
        "DEXUSEU":    ("USD to EUR Exchange Rate", "forex", ""),
        "DEXJPUS":    ("Japanese Yen per USD", "forex", ""),
    }

    docs, metadatas, ids = [], [], []
    total_series_loaded = 0

    for series_id, (name, category, unit) in series_map.items():
        try:
            print(f"  Loading {name} ({series_id})...")
            raw = fred_client.get_series(series_id, observation_start="2019-01-01")

            if raw.empty:
                print(f"    No data returned for {series_id}")
                continue

            # Resample to monthly (last observation of each month)
            monthly = raw.resample("ME").last().dropna()

            series_docs = 0
            for i, (date, value) in enumerate(monthly.items()):
                prev_value = monthly.iloc[i - 1] if i > 0 else None
                year_ago_value = monthly.iloc[i - 12] if i >= 12 else None

                doc = _build_fred_doc(
                    series_id, name, category, date, float(value),
                    prev_value=float(prev_value) if prev_value is not None else None,
                    year_ago_value=float(year_ago_value) if year_ago_value is not None else None,
                    unit=unit
                )
                doc_id = f"fred_{series_id}_{date.strftime('%Y%m')}"

                # Skip if already in collection (idempotent)
                docs.append(doc)
                metadatas.append({
                    "source": "fred",
                    "series_id": series_id,
                    "series_name": name,
                    "date": date.strftime("%Y-%m-%d"),
                    "value": float(value),
                    "macro_category": category,
                    "unit": unit,
                    "data_type": "macro_indicator",
                    "event_type": "macro_data"
                })
                ids.append(doc_id)
                series_docs += 1

            print(f"    Loaded {series_docs} monthly records")
            total_series_loaded += 1

        except Exception as e:
            print(f"    Error loading {series_id}: {e}")

    if docs:
        # Upsert in batches to avoid ChromaDB size limits
        batch_size = 200
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            embeddings = embed_texts(batch_docs)
            collection.upsert(documents=batch_docs, embeddings=embeddings,
                              metadatas=batch_meta, ids=batch_ids)

        print(f"\nLoaded {len(docs)} FRED macro data points across {total_series_loaded} series")
    else:
        print("No FRED data loaded")


def load_fed_communications(collection):
    """Load Fed-related time series into the fed_communications collection.

    Uses FRED series that represent FOMC decisions and Fed communications context:
    rate decisions, dot plot signals, and balance sheet data.
    """
    if not fred_client:
        print("FRED API key not configured, skipping Fed communications data")
        return

    fed_series = {
        "DFEDTARU": ("Federal Funds Rate Upper Target", "rate_decision", "%"),
        "DFEDTARL": ("Federal Funds Rate Lower Target", "rate_decision", "%"),
        "WALCL":    ("Fed Balance Sheet Total Assets", "balance_sheet", "M$"),
        "WRESBAL":  ("Reserve Balances at Federal Reserve Banks", "balance_sheet", "B$"),
        "TREAST":   ("US Treasury Securities Held by the Fed", "balance_sheet", "M$"),
        "WSHOMCB":  ("Mortgage-Backed Securities Held by the Fed", "balance_sheet", "M$"),
        "EFFR":     ("Effective Federal Funds Rate (Daily, monthly avg)", "rate_decision", "%"),
        "IOER":     ("Interest on Excess Reserves Rate", "rate_decision", "%"),
        "IORB":     ("Interest Rate on Reserve Balances", "rate_decision", "%"),
    }

    docs, metadatas, ids = [], [], []

    for series_id, (name, category, unit) in fed_series.items():
        try:
            print(f"  Loading {name} ({series_id})...")
            raw = fred_client.get_series(series_id, observation_start="2019-01-01")

            if raw.empty:
                print(f"    No data for {series_id}")
                continue

            monthly = raw.resample("ME").last().dropna()

            for i, (date, value) in enumerate(monthly.items()):
                prev_value = monthly.iloc[i - 1] if i > 0 else None

                doc = f"Federal Reserve {name} was {value:.2f}{unit} in {date.strftime('%B %Y')}."
                if prev_value is not None and not pd.isna(prev_value):
                    chg = value - float(prev_value)
                    if abs(chg) >= 0.01:
                        direction = "raised" if chg > 0 else "lowered"
                        doc += f" The Fed {direction} this by {abs(chg):.2f}{unit} from the prior month."

                # Balance sheet context
                if series_id == "WALCL":
                    if value > 8_000_000:
                        doc += " The Fed balance sheet is historically elevated, reflecting quantitative easing."
                    elif value < 4_000_000:
                        doc += " The Fed balance sheet is at pre-QE levels."

                docs.append(doc)
                metadatas.append({
                    "source": "fred",
                    "series_id": series_id,
                    "series_name": name,
                    "date": date.strftime("%Y-%m-%d"),
                    "value": float(value),
                    "fed_category": category,
                    "unit": unit,
                    "data_type": "fed_communication",
                    "event_type": "monetary_policy"
                })
                ids.append(f"fed_{series_id}_{date.strftime('%Y%m')}")

            print(f"    Loaded {len(monthly)} records")
        except Exception as e:
            print(f"    Error loading {series_id}: {e}")

    if docs:
        batch_size = 200
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i+batch_size]
            batch_meta = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            embeddings = embed_texts(batch_docs)
            collection.upsert(documents=batch_docs, embeddings=embeddings,
                              metadatas=batch_meta, ids=batch_ids)

        print(f"\nLoaded {len(docs)} Fed communications data points")


def load_sec_edgar(tickers: list[str], collection, years: int = 5):
    """Load SEC EDGAR XBRL financial facts for given tickers into earnings_filings collection.

    Uses SEC's public REST API — no API key required.
    Fetches quarterly and annual income statement + balance sheet data for each ticker.
    Rate-limited to ~8 requests/second to stay within SEC guidelines.
    """
    HEADERS = {
        "User-Agent": "FinSightAI adarsh.5.88@gmail.com",
        "Accept-Encoding": "gzip, deflate",
    }
    REQUEST_DELAY = 0.15  # SEC allows ~10 req/sec; 0.15s gives comfortable headroom

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=365 * years)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    # --- Step 1: Fetch ticker -> zero-padded CIK mapping ---
    print("  Fetching ticker-to-CIK mapping from SEC EDGAR...")
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=30
        )
        resp.raise_for_status()
        ticker_to_cik = {
            v["ticker"]: str(v["cik_str"]).zfill(10)
            for v in resp.json().values()
        }
        print(f"  Loaded {len(ticker_to_cik)} tickers from SEC EDGAR")
    except Exception as e:
        print(f"  Failed to fetch CIK mapping: {e}")
        return

    # --- Income statement metrics (duration-based, quarterly + annual) ---
    # Format: (us-gaap concept, label, unit)
    INCOME_METRICS = [
        ("Revenues",                                              "Revenue",             "B$"),
        ("RevenueFromContractWithCustomerExcludingAssessedTax",   "Revenue",             "B$"),
        ("SalesRevenueNet",                                       "Revenue",             "B$"),
        ("GrossProfit",                                           "Gross Profit",        "B$"),
        ("OperatingIncomeLoss",                                   "Operating Income",    "B$"),
        ("NetIncomeLoss",                                         "Net Income",          "B$"),
        ("EarningsPerShareDiluted",                               "EPS Diluted",         "$/share"),
        ("ResearchAndDevelopmentExpense",                         "R&D Expense",         "B$"),
        ("SellingGeneralAndAdministrativeExpense",                "SG&A Expense",        "B$"),
        ("NetCashProvidedByUsedInOperatingActivities",            "Operating Cash Flow", "B$"),
        ("PaymentsToAcquirePropertyPlantAndEquipment",            "CapEx",               "B$"),
    ]

    # --- Balance sheet metrics (instant / point-in-time) ---
    BALANCE_METRICS = [
        ("Assets",                                    "Total Assets",         "B$"),
        ("Liabilities",                               "Total Liabilities",    "B$"),
        ("StockholdersEquity",                        "Stockholders Equity",  "B$"),
        ("CashAndCashEquivalentsAtCarryingValue",      "Cash & Equivalents",   "B$"),
        ("LongTermDebt",                               "Long-Term Debt",       "B$"),
        ("CommonStockSharesOutstanding",               "Shares Outstanding",   "M shares"),
    ]

    docs: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for ticker in tickers:
        # SEC uses hyphens/periods differently — try original then swapped
        sec_ticker = ticker.replace("-", ".")
        cik = ticker_to_cik.get(ticker) or ticker_to_cik.get(sec_ticker)

        if not cik:
            print(f"  [{ticker}] CIK not found in SEC mapping, skipping")
            continue

        print(f"  [{ticker}] Fetching XBRL facts (CIK {cik})...")
        time.sleep(REQUEST_DELAY)

        try:
            resp = requests.get(
                f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                headers=HEADERS, timeout=60
            )
            resp.raise_for_status()
            facts = resp.json()
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else "?"
            print(f"  [{ticker}] HTTP {code} — skipping")
            continue
        except Exception as e:
            print(f"  [{ticker}] Error fetching XBRL: {e}")
            continue

        company_name = facts.get("entityName", ticker)
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        ticker_count = 0

        # ---- Income statement (duration entries) ----
        found_revenue = False
        for concept, label, unit in INCOME_METRICS:
            # Use only the first matching revenue concept
            if label == "Revenue" and found_revenue:
                continue

            concept_data = us_gaap.get(concept)
            if not concept_data:
                continue

            is_per_share = "share" in unit.lower()
            unit_key = "USD/shares" if is_per_share else "USD"
            raw_entries = concept_data.get("units", {}).get(unit_key, [])
            if not raw_entries:
                continue

            # Keep one entry per (period_end, report_type), preferring latest filed
            seen: dict[tuple, dict] = {}
            for entry in raw_entries:
                start = entry.get("start")
                end = entry.get("end", "")
                form = entry.get("form", "")
                filed = entry.get("filed", "")

                if not start or not end:
                    continue
                if form not in ("10-Q", "10-K"):
                    continue
                if end < start_str or end > end_str:
                    continue

                try:
                    duration = (pd.Timestamp(end) - pd.Timestamp(start)).days
                except Exception:
                    continue

                is_annual = 340 <= duration <= 390
                is_quarterly = 75 <= duration <= 105
                if not (is_quarterly or is_annual):
                    continue

                key = (end, "annual" if is_annual else "quarterly")
                if key not in seen or filed > seen[key].get("filed", ""):
                    seen[key] = {**entry, "_annual": is_annual}

            if label == "Revenue" and seen:
                found_revenue = True

            for (period_end, _period_type), entry in sorted(seen.items()):
                val = entry.get("val")
                if val is None:
                    continue

                filed = entry.get("filed", "N/A")
                is_annual = entry["_annual"]
                form = entry.get("form", "")

                # Scale large USD values to billions
                if not is_per_share and abs(val) >= 1_000_000:
                    display_val = val / 1_000_000_000
                    display_unit = "B$"
                else:
                    display_val = val
                    display_unit = unit

                try:
                    ts = pd.Timestamp(period_end)
                    period_str = ts.strftime("%B %Y")
                    q_num = (ts.month - 1) // 3 + 1
                    fiscal_q = f"{'FY' if is_annual else f'Q{q_num}'} {ts.year}"
                except Exception:
                    period_str = period_end
                    fiscal_q = period_end

                report_type = "annual" if is_annual else "quarterly"
                doc = (
                    f"{company_name} ({ticker}) {report_type} {label} was "
                    f"${display_val:.2f}{display_unit} for {fiscal_q} "
                    f"(period ending {period_str}, filed {filed})."
                )
                doc_id = f"sec_{ticker}_{concept}_{period_end}_{report_type}"
                if doc_id in ids:
                    continue

                docs.append(doc)
                metadatas.append({
                    "source": "sec_edgar",
                    "ticker": ticker,
                    "company_name": company_name,
                    "cik": cik,
                    "metric": label,
                    "concept": concept,
                    "value": float(display_val),
                    "unit": display_unit,
                    "period_end": period_end,
                    "filed_date": filed,
                    "form_type": form,
                    "fiscal_period": fiscal_q,
                    "report_type": report_type,
                    "data_type": "financial_filing",
                    "event_type": "earnings_report",
                })
                ids.append(doc_id)
                ticker_count += 1

        # ---- Balance sheet (instant entries — no 'start' field) ----
        for concept, label, unit in BALANCE_METRICS:
            concept_data = us_gaap.get(concept)
            if not concept_data:
                continue

            is_shares = "shares" in unit.lower()
            unit_key = "shares" if is_shares else "USD"
            raw_entries = concept_data.get("units", {}).get(unit_key, [])
            if not raw_entries:
                continue

            seen: dict[str, dict] = {}
            for entry in raw_entries:
                if entry.get("start"):  # Skip duration entries for balance sheet
                    continue
                end = entry.get("end", "")
                form = entry.get("form", "")
                filed = entry.get("filed", "")

                if form not in ("10-Q", "10-K"):
                    continue
                if end < start_str or end > end_str:
                    continue

                if end not in seen or filed > seen[end].get("filed", ""):
                    seen[end] = entry

            for period_end, entry in sorted(seen.items()):
                val = entry.get("val")
                if val is None:
                    continue

                filed = entry.get("filed", "N/A")
                form = entry.get("form", "")

                if is_shares and abs(val) >= 1_000_000:
                    display_val = val / 1_000_000
                    display_unit = "M shares"
                elif not is_shares and abs(val) >= 1_000_000:
                    display_val = val / 1_000_000_000
                    display_unit = "B$"
                else:
                    display_val = val
                    display_unit = unit

                try:
                    ts = pd.Timestamp(period_end)
                    period_str = ts.strftime("%B %Y")
                    q_num = (ts.month - 1) // 3 + 1
                    is_annual = form == "10-K"
                    fiscal_q = f"{'FY' if is_annual else f'Q{q_num}'} {ts.year}"
                except Exception:
                    period_str = period_end
                    fiscal_q = period_end

                report_type = "annual" if form == "10-K" else "quarterly"
                doc = (
                    f"{company_name} ({ticker}) {label} was "
                    f"${display_val:.2f}{display_unit} as of {period_str} "
                    f"({report_type} filing, filed {filed})."
                )
                doc_id = f"sec_{ticker}_{concept}_{period_end}"
                if doc_id in ids:
                    continue

                docs.append(doc)
                metadatas.append({
                    "source": "sec_edgar",
                    "ticker": ticker,
                    "company_name": company_name,
                    "cik": cik,
                    "metric": label,
                    "concept": concept,
                    "value": float(display_val),
                    "unit": display_unit,
                    "period_end": period_end,
                    "filed_date": filed,
                    "form_type": form,
                    "fiscal_period": fiscal_q,
                    "report_type": report_type,
                    "data_type": "financial_filing",
                    "event_type": "balance_sheet",
                })
                ids.append(doc_id)
                ticker_count += 1

        print(f"    Loaded {ticker_count} records for {ticker}")
        time.sleep(REQUEST_DELAY)

    if docs:
        batch_size = 200
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            embeddings = embed_texts(batch_docs)
            collection.upsert(
                documents=batch_docs, embeddings=embeddings,
                metadatas=batch_meta, ids=batch_ids
            )
        print(f"\nLoaded {len(docs)} SEC EDGAR financial records to ChromaDB")
    else:
        print("No SEC EDGAR data loaded")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load financial data to ChromaDB")
    parser.add_argument("--tickers", nargs="+", default=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "JNJ", "V"],
                       help="List of stock tickers to load")
    parser.add_argument("--years", type=int, default=5, help="Years of historical data to load")
    parser.add_argument("--ohlcv", action="store_true", default=True, help="Load OHLCV data")
    parser.add_argument("--dividends", action="store_true", default=True, help="Load dividend data")
    parser.add_argument("--splits", action="store_true", default=True, help="Load stock split data")
    parser.add_argument("--earnings", action="store_true", default=True, help="Load earnings data")
    parser.add_argument("--analysts", action="store_true", default=True, help="Load analyst recommendations")
    parser.add_argument("--news", action="store_true", default=True, help="Load company news")
    parser.add_argument("--macro", action="store_true", default=True, help="Load FRED macro indicators")
    parser.add_argument("--fed", action="store_true", default=True, help="Load Fed communications / balance sheet")
    parser.add_argument("--edgar", action="store_true", default=False, help="Load SEC EDGAR XBRL financial facts")

    args = parser.parse_args()

    print("Initializing ChromaDB client...")
    chroma_client = get_chroma_client()
    collections = initialize_collections(chroma_client)

    print(f"\nLoading data for tickers: {', '.join(args.tickers)}")
    print(f"Time period: {args.years} years of history\n")

    if args.ohlcv:
        load_ohlcv_data(args.tickers, collections["ohlcv_data"], years=args.years)

    if args.dividends:
        load_dividends_data(args.tickers, collections["dividends_data"], years=args.years)

    if args.splits:
        load_splits_data(args.tickers, collections["splits_data"], years=args.years)

    if args.earnings:
        load_earnings_data(args.tickers, collections["earnings_data"], years=args.years)

    if args.analysts:
        load_analyst_recommendations(args.tickers, collections["analyst_recommendations"])

    if args.news:
        load_company_news(args.tickers, collections["market_news"])

    if args.macro:
        print("\n[*] Loading FRED macro indicators (40+ series)...")
        load_fred_macro(collections["macro_indicators"])

    if args.fed:
        print("\n[*] Loading Fed communications and balance sheet data...")
        load_fed_communications(collections["fed_communications"])

    if args.edgar:
        print("\n[*] Loading SEC EDGAR XBRL financial facts...")
        load_sec_edgar(args.tickers, collections["earnings_filings"], years=args.years)

    print("\n[+] Data loading complete!")