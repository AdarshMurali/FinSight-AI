"""
Finnhub News Producer — runs natively on Windows in your venv.

Polls Finnhub REST API for company news every NEWS_POLL_INTERVAL_SECONDS,
deduplicates by article ID, and publishes new articles to the Kafka
topic 'market.news' as JSON messages.

Usage:
    cd backend/flink
    python finnhub_news_producer.py

Requirements (add to venv):
    pip install kafka-python requests
"""

import json
import time
import hashlib
import sys
import os
from datetime import datetime, timedelta, timezone

import requests
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    FINNHUB_API_KEY, FINNHUB_REST_BASE,
    KAFKA_BOOTSTRAP_SERVERS_EXTERNAL, TOPIC_MARKET_NEWS,
    TICKERS, NEWS_POLL_INTERVAL_SECONDS, NEWS_LOOKBACK_HOURS,
)


def make_producer() -> KafkaProducer:
    for attempt in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS_EXTERNAL,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
            )
            print(f"[+] Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS_EXTERNAL}")
            return producer
        except NoBrokersAvailable:
            print(f"  Kafka not ready, retrying ({attempt + 1}/10)...")
            time.sleep(6)
    raise RuntimeError("Could not connect to Kafka after 10 attempts. Is the stack running?")


def fetch_news(ticker: str, from_ts: int, to_ts: int) -> list[dict]:
    from_date = datetime.fromtimestamp(from_ts, tz=timezone.utc).strftime("%Y-%m-%d")
    to_date   = datetime.fromtimestamp(to_ts,   tz=timezone.utc).strftime("%Y-%m-%d")
    url = f"{FINNHUB_REST_BASE}/company-news"
    params = {
        "symbol": ticker,
        "from": from_date,
        "to": to_date,
        "token": FINNHUB_API_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json() or []
    except Exception as e:
        print(f"  [{ticker}] News fetch error: {e}")
        return []


def article_id(article: dict) -> str:
    raw = article.get("id") or article.get("url") or article.get("headline", "")
    return hashlib.md5(str(raw).encode()).hexdigest()


def main():
    print("=" * 60)
    print("FinSight AI — Finnhub News Producer")
    print("=" * 60)
    print(f"Tickers: {len(TICKERS)}")
    print(f"Poll interval: {NEWS_POLL_INTERVAL_SECONDS}s")
    print(f"Kafka topic: {TOPIC_MARKET_NEWS}")
    print()

    producer = make_producer()
    seen_ids: set[str] = set()

    to_ts   = int(datetime.now(tz=timezone.utc).timestamp())
    from_ts = to_ts - (NEWS_LOOKBACK_HOURS * 3600)

    cycle = 0
    while True:
        cycle += 1
        now = datetime.now(tz=timezone.utc)
        print(f"\n[Cycle {cycle}] {now.strftime('%Y-%m-%d %H:%M:%S UTC')} — polling {len(TICKERS)} tickers...")

        new_articles = 0
        for ticker in TICKERS:
            articles = fetch_news(ticker, from_ts, to_ts)
            for article in articles:
                aid = article_id(article)
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)

                message = {
                    "id":           aid,
                    "ticker":       ticker,
                    "headline":     article.get("headline", ""),
                    "summary":      article.get("summary", ""),
                    "source":       article.get("source", ""),
                    "url":          article.get("url", ""),
                    "datetime":     article.get("datetime", 0),
                    "category":     article.get("category", ""),
                    "image":        article.get("image", ""),
                    "published_at": datetime.fromtimestamp(
                        article.get("datetime", 0), tz=timezone.utc
                    ).isoformat() if article.get("datetime") else "",
                    "ingested_at":  now.isoformat(),
                }
                producer.send(TOPIC_MARKET_NEWS, key=ticker, value=message)
                new_articles += 1

            time.sleep(1.0)  # ~60 req/min limit; 1s between ticker calls

        producer.flush()
        print(f"  Published {new_articles} new articles to {TOPIC_MARKET_NEWS}")
        print(f"  Total unique articles seen: {len(seen_ids)}")

        # Next poll: from now, look back slightly to catch any stragglers
        to_ts   = int(datetime.now(tz=timezone.utc).timestamp())
        from_ts = to_ts - 3600  # last 1 hour on subsequent cycles

        print(f"  Next poll in {NEWS_POLL_INTERVAL_SECONDS}s...")
        time.sleep(NEWS_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
