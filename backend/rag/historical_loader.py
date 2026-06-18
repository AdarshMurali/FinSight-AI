# backend/rag/historical_loader.py
import yfinance as yf
from fredapi import Fred
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import os
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
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
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
        print(f"Loaded {len(docs)} total news articles to ChromaDB")


def load_fred_macro(collection):
    """Load FRED macro indicator summaries."""
    if not fred_client:
        print("FRED API key not configured, skipping macro data")
        return

    series_map = {
        "FEDFUNDS": ("Fed Funds Rate", "interest_rates"),
        "CPIAUCSL": ("CPI Inflation", "inflation"),
        "UNRATE": ("Unemployment Rate", "employment"),
        "T10Y2Y": ("Yield Curve (10Y-2Y)", "yield_curve"),
        "VIXCLS": ("VIX Volatility Index", "volatility"),
        "GDP": ("US GDP Growth", "gdp"),
        "DGS10": ("10-Year Treasury Yield", "interest_rates"),
    }

    docs, metadatas, ids = [], [], []

    for series_id, (name, category) in series_map.items():
        try:
            print(f"Loading {name} ({series_id})...")
            data = fred_client.get_series(series_id, observation_start="2019-01-01")

            # Create monthly summary documents
            monthly = data.resample("M").last()
            for date, value in monthly.items():
                if pd.isna(value):
                    continue
                doc = f"{name} was {value:.2f} as of {date.strftime('%B %Y')}."
                docs.append(doc)
                metadatas.append({
                    "source": "fred",
                    "series_id": series_id,
                    "series_name": name,
                    "date": date.strftime("%Y-%m-%d"),
                    "value": float(value),
                    "macro_category": category,
                    "data_type": "macro_indicator"
                })
                ids.append(f"fred_{series_id}_{date.strftime('%Y%m')}")

            print(f"  Loaded {len(monthly)} data points for {name}")
        except Exception as e:
            print(f"  Error loading {name}: {e}")

    if docs:
        embeddings = embed_texts(docs)
        collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
        print(f"Loaded {len(docs)} FRED macro data points")


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
    parser.add_argument("--macro", action="store_true", default=True, help="Load macro indicators")

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
        load_fred_macro(collections["macro_indicators"])

    print("\n✅ Data loading complete!")