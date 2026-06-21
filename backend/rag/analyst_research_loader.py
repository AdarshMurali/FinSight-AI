"""
Analyst Research Loader
=======================
Loads analyst research data into ChromaDB 'analyst_research' collection.

Data sources:
  1. Recommendation trends  — Finnhub free API (monthly buy/hold/sell history)
  2. Price targets          — yfinance (current analyst target high/mean/low)
  3. Upgrade/downgrades     — yfinance (firm-level rating changes, past 12 months)
  4. EPS estimates          — yfinance (quarterly forward earnings estimates)

Note: Finnhub /price-target, /upgrade-downgrade, /eps-estimate require a paid plan.
      Sections 2-4 use yfinance which provides the same data free.

Usage:
    cd backend/rag
    python analyst_research_loader.py                        # all 50 tickers
    python analyst_research_loader.py --tickers AAPL MSFT   # specific tickers

Runtime: ~6-8 minutes for all 50 tickers (Finnhub rate limit on section 1).
"""

import os
import sys
import time
import hashlib
import argparse
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from chromadb_setup import get_chroma_client, initialize_collections

load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
FINNHUB_BASE    = "https://finnhub.io/api/v1"
FINNHUB_DELAY   = 1.1   # seconds between Finnhub calls — stays under 60 req/min
YFINANCE_DELAY  = 0.5   # polite delay between yfinance calls

ALL_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B",
    "JPM",  "JNJ",  "V",     "WMT",  "PG",   "MA",   "INTC", "NFLX",
    "MCD",  "DIS",  "KO",    "PEP",  "ABT",  "TMO",  "MRK",  "IBM",
    "CSCO", "CAT",  "F",     "GM",   "BA",   "HON",  "UNP",  "AXP",
    "SPG",  "XOM",  "CVX",   "COP",  "MPC",  "PSX",  "VLO",  "EQR",
    "VZ",   "T",    "TMUS",  "DELL", "ORCL", "AMD",  "PYPL", "ADBE",
    "AVGO", "INTU",
]

openai_client = OpenAI(api_key=OPENAI_API_KEY)


# ── Helpers ───────────────────────────────────────────────────────────────────

def embed_texts(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def finnhub_get(endpoint: str, params: dict):
    params["token"] = FINNHUB_API_KEY
    try:
        resp = requests.get(f"{FINNHUB_BASE}/{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    [Finnhub error] /{endpoint} {params.get('symbol', '')}: {e}")
        return None


def upsert_batch(collection, docs, metadatas, ids, label: str):
    if not docs:
        print(f"  No {label} docs to upsert.")
        return
    print(f"  Embedding {len(docs)} {label} docs...")
    embeddings = embed_texts(docs)
    collection.upsert(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)


# ── Section 1: Finnhub — Recommendation Trends ───────────────────────────────

def load_recommendation_trends(tickers: list[str], collection) -> int:
    """Monthly analyst buy/hold/sell counts via Finnhub — up to 18 months history."""
    print("\n[1/4] Recommendation trends (Finnhub)...")
    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        # Finnhub uses BRK.B not BRK-B
        fh_ticker = ticker.replace("-", ".")
        data = finnhub_get("stock/recommendation", {"symbol": fh_ticker})
        time.sleep(FINNHUB_DELAY)
        if not data:
            continue

        ticker_count = 0
        for entry in data:
            period      = entry.get("period", "")
            strong_buy  = int(entry.get("strongBuy",  0))
            buy         = int(entry.get("buy",         0))
            hold        = int(entry.get("hold",        0))
            sell        = int(entry.get("sell",        0))
            strong_sell = int(entry.get("strongSell",  0))
            total = strong_buy + buy + hold + sell + strong_sell
            if total == 0:
                continue

            bull_pct = round((buy + strong_buy) / total * 100, 1)
            bear_pct = round((sell + strong_sell) / total * 100, 1)

            if bull_pct >= 70:
                consensus = "strongly bullish"
            elif bull_pct >= 50:
                consensus = "moderately bullish"
            elif bear_pct >= 50:
                consensus = "bearish"
            else:
                consensus = "neutral/mixed"

            try:
                period_label = datetime.strptime(period[:7], "%Y-%m").strftime("%B %Y")
            except Exception:
                period_label = period

            doc = (
                f"{ticker} analyst consensus in {period_label}: "
                f"{strong_buy} Strong Buy, {buy} Buy, {hold} Hold, "
                f"{sell} Sell, {strong_sell} Strong Sell "
                f"({total} analysts total). "
                f"Bullish: {bull_pct}%, Bearish: {bear_pct}%. "
                f"Overall sentiment: {consensus}."
            )
            docs.append(doc)
            metadatas.append({
                "source":         "finnhub",
                "ticker":         ticker,
                "period":         period[:7] if period else "",
                "strong_buy":     strong_buy,
                "buy":            buy,
                "hold":           hold,
                "sell":           sell,
                "strong_sell":    strong_sell,
                "total_analysts": total,
                "bull_pct":       float(bull_pct),
                "bear_pct":       float(bear_pct),
                "consensus":      consensus,
                "data_type":      "recommendation_trend",
                "event_type":     "analyst_rating",
                "ingested_via":   "batch_loader",
            })
            ids.append(f"rec_{ticker}_{period[:7]}")
            ticker_count += 1

        print(f"  {ticker}: {ticker_count} monthly snapshots")

    upsert_batch(collection, docs, metadatas, ids, "recommendation trend")
    print(f"  Total: {len(docs)} records")
    return len(docs)


# ── Section 2: yfinance — Price Targets ──────────────────────────────────────

def load_price_targets(tickers: list[str], collection) -> int:
    """Current analyst price target consensus (high/mean/low) via yfinance."""
    print("\n[2/4] Price targets (yfinance)...")
    docs, metadatas, ids = [], [], []
    today = datetime.now().strftime("%Y-%m-%d")

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            pt = t.analyst_price_targets
            time.sleep(YFINANCE_DELAY)

            if not pt or not isinstance(pt, dict):
                print(f"  {ticker}: no data")
                continue

            current     = pt.get("current") or pt.get("currentPrice", 0)
            target_mean = pt.get("mean",   0)
            target_high = pt.get("high",   0)
            target_low  = pt.get("low",    0)

            if not target_mean:
                print(f"  {ticker}: no target data")
                continue

            target_mean = float(target_mean)
            target_high = float(target_high)
            target_low  = float(target_low)
            current     = float(current) if current else 0.0
            spread_pct  = round((target_high - target_low) / target_mean * 100, 1) if target_mean else 0
            upside_pct  = round((target_mean - current) / current * 100, 1) if current else 0

            doc = (
                f"{ticker} analyst price targets (as of {today}): "
                f"Mean target ${target_mean:.2f}, "
                f"Bull case ${target_high:.2f}, Bear case ${target_low:.2f}. "
                f"Current price ${current:.2f} — "
                f"implied upside to mean: {upside_pct:+.1f}%. "
                f"Target range spread: {spread_pct:.1f}% of mean."
            )
            docs.append(doc)
            metadatas.append({
                "source":        "yfinance",
                "ticker":        ticker,
                "current_price": current,
                "target_mean":   target_mean,
                "target_high":   target_high,
                "target_low":    target_low,
                "upside_pct":    upside_pct,
                "spread_pct":    spread_pct,
                "as_of":         today,
                "data_type":     "price_target",
                "event_type":    "analyst_rating",
                "ingested_via":  "batch_loader",
            })
            ids.append(f"pt_{ticker}_{today}")
            print(f"  {ticker}: mean=${target_mean:.2f}  high=${target_high:.2f}  low=${target_low:.2f}  upside={upside_pct:+.1f}%")

        except Exception as e:
            print(f"  {ticker}: error — {e}")

    upsert_batch(collection, docs, metadatas, ids, "price target")
    print(f"  Total: {len(docs)} records")
    return len(docs)


# ── Section 3: yfinance — Upgrade/Downgrade History ──────────────────────────

def load_upgrade_downgrades(tickers: list[str], collection) -> int:
    """Firm-level rating changes over past 12 months via yfinance."""
    print("\n[3/4] Upgrade/downgrade history (yfinance, past 12 months)...")
    docs, metadatas, ids = [], [], []
    cutoff = datetime.now() - timedelta(days=365)

    for ticker in tickers:
        try:
            t  = yf.Ticker(ticker)
            df = t.upgrades_downgrades
            time.sleep(YFINANCE_DELAY)

            if df is None or df.empty:
                print(f"  {ticker}: no data")
                continue

            # Filter to past 12 months
            if isinstance(df.index, pd.DatetimeIndex):
                df = df[df.index >= cutoff]
            elif "GradeDate" in df.columns:
                df["GradeDate"] = pd.to_datetime(df["GradeDate"])
                df = df[df["GradeDate"] >= cutoff]

            ticker_count = 0
            for date_idx, row in df.iterrows():
                firm       = str(row.get("Firm",      "Unknown firm"))
                to_grade   = str(row.get("ToGrade",   ""))
                from_grade = str(row.get("FromGrade", ""))
                action     = str(row.get("Action",    "reit")).lower()

                if not to_grade or to_grade == "nan":
                    continue

                date_str = (
                    date_idx.strftime("%Y-%m-%d")
                    if isinstance(date_idx, pd.Timestamp)
                    else str(date_idx)[:10]
                )

                if action in ("up", "upgrade"):
                    action_text = f"upgraded {ticker} from {from_grade} to {to_grade}"
                    action_norm = "upgrade"
                elif action in ("down", "downgrade"):
                    action_text = f"downgraded {ticker} from {from_grade} to {to_grade}"
                    action_norm = "downgrade"
                elif action in ("init", "initiated"):
                    action_text = f"initiated coverage on {ticker} with {to_grade}"
                    action_norm = "init"
                else:
                    action_text = f"reiterated {to_grade} on {ticker}"
                    action_norm = "reiterate"

                doc = f"{firm} {action_text} on {date_str}."
                if from_grade and from_grade != "nan" and action_norm in ("upgrade", "downgrade"):
                    doc += f" Previous rating: {from_grade}."

                dedup_key = hashlib.md5(f"{ticker}{firm}{date_str}{to_grade}{len(ids)}".encode()).hexdigest()[:12]
                docs.append(doc)
                metadatas.append({
                    "source":       "yfinance",
                    "ticker":       ticker,
                    "firm":         firm,
                    "action":       action_norm,
                    "from_grade":   from_grade if from_grade != "nan" else "",
                    "to_grade":     to_grade,
                    "date":         date_str,
                    "data_type":    "upgrade_downgrade",
                    "event_type":   "analyst_rating",
                    "ingested_via": "batch_loader",
                })
                ids.append(f"ud_{ticker}_{dedup_key}")
                ticker_count += 1

            print(f"  {ticker}: {ticker_count} rating actions")

        except Exception as e:
            print(f"  {ticker}: error — {e}")

    upsert_batch(collection, docs, metadatas, ids, "upgrade/downgrade")
    print(f"  Total: {len(docs)} records")
    return len(docs)


# ── Section 4: yfinance — EPS Estimates ──────────────────────────────────────

def load_eps_estimates(tickers: list[str], collection) -> int:
    """Forward quarterly EPS estimates via yfinance."""
    print("\n[4/4] EPS estimates (yfinance)...")
    docs, metadatas, ids = [], [], []

    for ticker in tickers:
        try:
            t   = yf.Ticker(ticker)
            df  = t.earnings_estimate
            time.sleep(YFINANCE_DELAY)

            if df is None or df.empty:
                print(f"  {ticker}: no earnings estimate data")
                continue

            ticker_count = 0
            for period_label, row in df.iterrows():
                avg_est    = row.get("avg",              None)
                low_est    = row.get("low",              None)
                high_est   = row.get("high",             None)
                n_analysts = row.get("numberOfAnalysts", 0)
                year_ago   = row.get("yearAgoEps",       None)

                if avg_est is None or pd.isna(avg_est):
                    continue

                avg_est    = float(avg_est)
                low_est    = float(low_est)    if low_est    is not None and not pd.isna(low_est)    else 0.0
                high_est   = float(high_est)   if high_est   is not None and not pd.isna(high_est)   else 0.0
                year_ago   = float(year_ago)   if year_ago   is not None and not pd.isna(year_ago)   else None
                n_analysts = int(n_analysts)   if not pd.isna(n_analysts) else 0

                yoy_str = ""
                if year_ago and year_ago != 0:
                    yoy_pct = round((avg_est - year_ago) / abs(year_ago) * 100, 1)
                    yoy_str = f" Year-over-year change: {yoy_pct:+.1f}% vs ${year_ago:.2f} last year."

                doc = (
                    f"{ticker} EPS estimate for {period_label}: "
                    f"consensus ${avg_est:.2f} from {n_analysts} analysts "
                    f"(range: ${low_est:.2f} to ${high_est:.2f}).{yoy_str}"
                )
                docs.append(doc)
                metadatas.append({
                    "source":       "yfinance",
                    "ticker":       ticker,
                    "period":       str(period_label),
                    "eps_estimate": avg_est,
                    "eps_high":     high_est,
                    "eps_low":      low_est,
                    "year_ago_eps": year_ago if year_ago is not None else 0.0,
                    "n_analysts":   n_analysts,
                    "data_type":    "eps_estimate",
                    "event_type":   "earnings_estimate",
                    "ingested_via": "batch_loader",
                })
                ids.append(f"eps_{ticker}_{str(period_label).replace(' ', '_')}")
                ticker_count += 1

            print(f"  {ticker}: {ticker_count} quarterly estimates")

        except Exception as e:
            print(f"  {ticker}: error — {e}")

    upsert_batch(collection, docs, metadatas, ids, "EPS estimate")
    print(f"  Total: {len(docs)} records")
    return len(docs)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Load analyst research into ChromaDB")
    parser.add_argument("--tickers", nargs="+", default=None,
                        help="Tickers to load (default: all 50 covered tickers)")
    parser.add_argument("--skip-recommendations", action="store_true")
    parser.add_argument("--skip-price-targets",   action="store_true")
    parser.add_argument("--skip-upgrades",         action="store_true")
    parser.add_argument("--skip-eps",              action="store_true")
    args = parser.parse_args()

    if not FINNHUB_API_KEY:
        print("ERROR: FINNHUB_API_KEY not set in backend/.env")
        sys.exit(1)
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set in backend/.env")
        sys.exit(1)

    tickers = args.tickers or ALL_TICKERS

    print("=" * 60)
    print("FinSight AI — Analyst Research Loader")
    print("=" * 60)
    print(f"Tickers : {len(tickers)}")
    print(f"Sources : Finnhub (recommendation trends) + yfinance (price targets, upgrades, EPS)")
    print()

    client      = get_chroma_client()
    collections = initialize_collections(client)
    col         = collections["analyst_research"]

    total = 0
    if not args.skip_recommendations:
        total += load_recommendation_trends(tickers, col)
    if not args.skip_price_targets:
        total += load_price_targets(tickers, col)
    if not args.skip_upgrades:
        total += load_upgrade_downgrades(tickers, col)
    if not args.skip_eps:
        total += load_eps_estimates(tickers, col)

    print("\n" + "=" * 60)
    print(f"Done. {total} total records loaded into 'analyst_research'.")
    print(f"ChromaDB collection count: {col.count()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
