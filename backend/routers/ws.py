"""
WebSocket Router — Task 4.2
============================
Endpoint:   ws://localhost:8000/ws
HTTP stats: GET /ws/stats

Background tasks (started by main.py lifespan):
  • run_price_simulator()   — ticks portfolio values every 4 s
  • run_kafka_consumer()    — bridges market.news Kafka → WebSocket broadcast

Message schema (all messages have a "type" field):

  connected       → confirmation on join
  pong            → response to client "ping"
  portfolio_update → {portfolio_id, portfolio_name, total_value, change_pct, currency, strategy_type, timestamp}
  market_event    → {source:"kafka", data:{...}, timestamp}
"""

import asyncio
import json
import logging
import random
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database import SessionLocal
from models import Portfolio
from services.connection_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Confirm connection immediately
        await websocket.send_text(json.dumps({
            "type":        "connected",
            "message":     "FinSight AI real-time feed active",
            "connections": manager.count,
            "timestamp":   _now(),
        }))
        # Keep connection open; client sends "ping" every 20 s
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({
                    "type":      "pong",
                    "timestamp": _now(),
                }))
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WS error: %s", e)
        await manager.disconnect(websocket)


@router.get("/ws/stats")
def ws_stats():
    """Returns active WebSocket connection count — useful for debugging."""
    return {"active_connections": manager.count}


# ── Background task 1: Portfolio price simulator ──────────────────────────────

async def run_price_simulator():
    """
    Simulates real-time portfolio value fluctuations.

    Every 4 seconds a random subset of portfolios receives a small
    Gaussian price tick (mean=0, std=0.15%, clamped ±0.5%) and the
    update is broadcast to all connected WebSocket clients.

    In production, replace this with a consumer of real price data
    arriving through Flink → Kafka.
    """
    logger.info("Price simulator started")

    while True:
        await asyncio.sleep(4)

        if manager.count == 0:
            continue  # skip if nobody is connected

        db = SessionLocal()
        try:
            portfolios = (
                db.query(
                    Portfolio.portfolio_id,
                    Portfolio.portfolio_name,
                    Portfolio.total_value,
                    Portfolio.strategy_type,
                    Portfolio.currency,
                )
                .limit(100)
                .all()
            )

            # Tick a random 8-portfolio sample per cycle
            sample = random.sample(portfolios, min(8, len(portfolios)))

            for p in sample:
                if not p.total_value:
                    continue

                # Gaussian tick: realistic micro-fluctuations
                change_pct = random.gauss(0, 0.15)
                change_pct = max(-0.5, min(0.5, change_pct))
                new_value  = float(p.total_value) * (1 + change_pct / 100)

                await manager.broadcast({
                    "type":           "portfolio_update",
                    "portfolio_id":   p.portfolio_id,
                    "portfolio_name": p.portfolio_name,
                    "total_value":    round(new_value, 2),
                    "change_pct":     round(change_pct, 4),
                    "currency":       p.currency or "USD",
                    "strategy_type":  p.strategy_type,
                    "timestamp":      _now(),
                })

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Price simulator error: %s", e)
        finally:
            db.close()


# ── Background task 2: Kafka → WebSocket bridge ───────────────────────────────

async def run_kafka_consumer():
    """
    Consumes from the market.news Kafka topic written by the Flink pipeline
    and broadcasts each message to all connected WebSocket clients.

    Architecture:
      Kafka consumer (blocking, daemon thread)
        → asyncio.Queue (thread-safe handoff)
          → this coroutine (async drain loop)
            → manager.broadcast()

    Falls back silently if Kafka is not available so the rest of the
    app continues to work without the streaming stack.
    """
    loop  = asyncio.get_event_loop()
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def _kafka_thread():
        try:
            from kafka import KafkaConsumer  # type: ignore
            consumer = KafkaConsumer(
                "market.news",
                bootstrap_servers="localhost:9092",
                auto_offset_reset="latest",
                group_id="finsight-ws-bridge",
                value_deserializer=lambda m: json.loads(
                    m.decode("utf-8", errors="replace")
                ),
                session_timeout_ms=10_000,
                request_timeout_ms=15_000,
            )
            logger.info("Kafka WS bridge connected → market.news")

            while True:
                batch = consumer.poll(timeout_ms=2_000)
                for _tp, messages in batch.items():
                    for msg in messages:
                        asyncio.run_coroutine_threadsafe(
                            queue.put(msg.value), loop
                        )

        except ImportError:
            logger.warning("kafka-python not installed — Kafka WS bridge disabled")
        except Exception as e:
            logger.warning("Kafka WS bridge unavailable: %s", e)

    # Start daemon thread — dies automatically when the process exits
    threading.Thread(
        target=_kafka_thread,
        daemon=True,
        name="kafka-ws-bridge",
    ).start()

    # Async drain loop
    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=10.0)
            await manager.broadcast({
                "type":      "market_event",
                "source":    "kafka",
                "data":      data,
                "timestamp": _now(),
            })
        except asyncio.TimeoutError:
            continue          # nothing in queue, keep looping
        except asyncio.CancelledError:
            raise             # propagate so lifespan can clean up


# ── Helper ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
