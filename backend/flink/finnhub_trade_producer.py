"""
Finnhub Trade Producer — runs natively on Windows in your venv.

Opens a Finnhub WebSocket connection, subscribes to live trade data
for all covered tickers, and publishes each trade to the Kafka topic
'market.trades' as a JSON message.

Usage:
    cd backend/flink
    python finnhub_trade_producer.py

Requirements (add to venv):
    pip install kafka-python websocket-client
"""

import json
import time
import sys
import os
import threading
from typing import Optional
from datetime import datetime, timezone

import websocket
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    FINNHUB_API_KEY, FINNHUB_WS_URL,
    KAFKA_BOOTSTRAP_SERVERS, TOPIC_MARKET_TRADES,
    TICKERS,
)

producer: Optional[KafkaProducer] = None
trade_count = 0
last_prices: dict[str, float] = {}


def make_producer() -> KafkaProducer:
    for attempt in range(10):
        try:
            p = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks=1,
                linger_ms=50,   # Small batch window for throughput
            )
            print(f"[+] Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return p
        except NoBrokersAvailable:
            print(f"  Kafka not ready, retrying ({attempt + 1}/10)...")
            time.sleep(6)
    raise RuntimeError("Could not connect to Kafka after 10 attempts.")


def on_message(ws, message):
    global trade_count
    try:
        data = json.loads(message)
        if data.get("type") != "trade":
            return

        now_iso = datetime.now(tz=timezone.utc).isoformat()
        for trade in data.get("data", []):
            symbol   = trade.get("s", "")
            price    = trade.get("p", 0.0)
            volume   = trade.get("v", 0)
            ts_ms    = trade.get("t", 0)

            # Compute price change from last known price
            prev_price = last_prices.get(symbol)
            pct_change = ((price - prev_price) / prev_price * 100) if prev_price else 0.0
            last_prices[symbol] = price

            message_payload = {
                "symbol":         symbol,
                "price":          price,
                "volume":         volume,
                "timestamp_ms":   ts_ms,
                "timestamp_iso":  datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat() if ts_ms else now_iso,
                "ingested_at":    now_iso,
                "prev_price":     prev_price,
                "pct_change":     round(pct_change, 4),
                "conditions":     trade.get("c", []),
            }
            producer.send(TOPIC_MARKET_TRADES, key=symbol, value=message_payload)
            trade_count += 1

            if trade_count % 500 == 0:
                print(f"  [{now_iso[:19]}] {trade_count} trades published")

    except Exception as e:
        print(f"  [on_message error] {e}")


def on_error(ws, error):
    print(f"[WebSocket error] {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[WebSocket closed] code={close_status_code} msg={close_msg}")


def on_open(ws):
    print(f"[+] WebSocket connected. Subscribing to {len(TICKERS)} symbols...")
    for ticker in TICKERS:
        ws.send(json.dumps({"type": "subscribe", "symbol": ticker}))
    print(f"[+] Subscribed to: {', '.join(TICKERS[:10])}...")


def main():
    global producer
    print("=" * 60)
    print("FinSight AI — Finnhub Trade Producer (WebSocket)")
    print("=" * 60)
    print(f"Symbols: {len(TICKERS)}")
    print(f"Kafka topic: {TOPIC_MARKET_TRADES}")
    print()

    producer = make_producer()

    # Periodic flush thread
    def flush_loop():
        while True:
            time.sleep(5)
            if producer:
                producer.flush()

    threading.Thread(target=flush_loop, daemon=True).start()

    # Reconnect loop — WebSocket can drop, especially on free tier
    while True:
        try:
            print(f"[*] Connecting to Finnhub WebSocket...")
            ws = websocket.WebSocketApp(
                FINNHUB_WS_URL,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as e:
            print(f"[WebSocket exception] {e}")

        print("[*] Reconnecting in 10s...")
        time.sleep(10)


if __name__ == "__main__":
    main()
