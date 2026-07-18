"""
PyFlink Job: Real-Time Volatility Detector
===========================================
Reads live trades from Kafka topic 'market.trades', applies a 5-minute
tumbling window per symbol, detects price moves or volume spikes past
configurable thresholds, and writes volatility event documents to ChromaDB
'volatility_events' collection.

Thresholds are read from SSM Parameter Store (/finsight/volatility_*) and
re-polled every SSM_REFRESH_SECONDS while the job runs, so they can be
tuned without a redeploy. Falls back to the DEFAULT_* constants below --
silently, logging once per refresh attempt -- if SSM is unreachable or the
IAM permission isn't present (e.g. running locally without an instance
profile), so a Parameter Store hiccup never takes the whole stream down.

Submit from inside the Flink container:
    docker exec finsight-flink-jobmanager \
        flink run -py /opt/flink/jobs/volatility_detector_job.py

Runs continuously (streaming mode).
"""

import os
import json
import time
import hashlib
from datetime import datetime, timezone

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer,
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.datastream.functions import MapFunction, ReduceFunction
from pyflink.datastream.window import TumblingProcessingTimeWindows
from pyflink.common import Time

from openai import OpenAI
import chromadb

# ── Config ────────────────────────────────────────────────────────────────
KAFKA_BROKERS   = os.getenv("KAFKA_BROKERS", "kafka:29092")
CHROMA_HOST     = os.getenv("CHROMA_HOST",   "host.docker.internal")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", "8001"))
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
COLLECTION_NAME = "volatility_events"

AWS_REGION      = os.getenv("AWS_REGION", "ap-south-1")

# Used only if SSM is unreachable (no instance-profile permission, local dev
# without AWS creds, transient API error) -- same values as the original
# hardcoded thresholds.
DEFAULT_PRICE_MOVE_THRESHOLD_PCT = 1.5   # Flag if price moves >1.5% in 5-min window
DEFAULT_VOLUME_SPIKE_MULTIPLIER  = 2.0   # Flag if volume > 2x average

SSM_PARAM_PRICE_THRESHOLD  = "/finsight/volatility_price_threshold_pct"
SSM_PARAM_VOLUME_MULTIPLIER = "/finsight/volatility_volume_spike_multiplier"
SSM_REFRESH_SECONDS         = int(os.getenv("SSM_REFRESH_SECONDS", "300"))

WINDOW_MINUTES            = 5


class TradeDeserializer(MapFunction):
    """Parse raw JSON trade messages into structured dicts."""

    def map(self, raw_json: str) -> dict:
        try:
            return json.loads(raw_json)
        except Exception:
            return {}


class WindowAggregator(ReduceFunction):
    """Aggregate trades within a window: track OHLCV + price extremes."""

    def reduce(self, a: dict, b: dict) -> dict:
        if not a:
            return b
        if not b:
            return a
        return {
            "symbol":      a["symbol"],
            "open_price":  a["open_price"],
            "high_price":  max(a["high_price"], b["high_price"]),
            "low_price":   min(a["low_price"],  b["low_price"]),
            "close_price": b["close_price"],   # last trade wins
            "total_volume": a["total_volume"] + b["total_volume"],
            "trade_count":  a.get("trade_count", 1) + b.get("trade_count", 1),
            "window_start": a.get("window_start", a.get("timestamp_iso", "")),
            "window_end":   b.get("window_end", ""),
        }


class TradeToWindowEntry(MapFunction):
    """Convert a raw trade to the initial aggregation shape."""

    def map(self, trade: dict) -> dict:
        p = trade.get("price", 0.0)
        return {
            "symbol":       trade.get("symbol", ""),
            "open_price":   p,
            "high_price":   p,
            "low_price":    p,
            "close_price":  p,
            "total_volume": trade.get("volume", 0),
            "trade_count":  1,
            "window_start": trade.get("timestamp_iso", ""),
            "window_end":   trade.get("timestamp_iso", ""),
        }


class VolatilityEventSink(MapFunction):
    """Evaluate windowed OHLCV, detect spikes, write events to ChromaDB."""

    def open(self, runtime_context):
        self.openai     = OpenAI(api_key=OPENAI_API_KEY)
        self.chroma     = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.collection = self.chroma.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.avg_volumes: dict[str, float] = {}  # rolling avg volume per symbol

        try:
            import boto3
            self.ssm = boto3.client("ssm", region_name=AWS_REGION)
        except Exception as e:
            print(f"[WARN] boto3/SSM client unavailable, using default thresholds only: {e}")
            self.ssm = None

        self.price_threshold  = DEFAULT_PRICE_MOVE_THRESHOLD_PCT
        self.volume_multiplier = DEFAULT_VOLUME_SPIKE_MULTIPLIER
        self._last_threshold_refresh = 0.0
        self._refresh_thresholds()

    def _refresh_thresholds(self):
        """Best-effort pull of both thresholds from SSM. Keeps last-known-good
        values on any failure -- a stream job should degrade, not crash, on a
        transient Parameter Store error."""
        self._last_threshold_refresh = time.time()
        if self.ssm is None:
            return
        try:
            self.price_threshold = float(
                self.ssm.get_parameter(Name=SSM_PARAM_PRICE_THRESHOLD)["Parameter"]["Value"]
            )
            self.volume_multiplier = float(
                self.ssm.get_parameter(Name=SSM_PARAM_VOLUME_MULTIPLIER)["Parameter"]["Value"]
            )
        except Exception as e:
            print(
                f"[WARN] SSM threshold refresh failed, keeping price={self.price_threshold} "
                f"volume={self.volume_multiplier}: {e}"
            )

    def map(self, window_data: dict) -> str:
        try:
            if time.time() - self._last_threshold_refresh >= SSM_REFRESH_SECONDS:
                self._refresh_thresholds()

            symbol       = window_data.get("symbol", "")
            open_price   = window_data.get("open_price", 0.0)
            close_price  = window_data.get("close_price", 0.0)
            high_price   = window_data.get("high_price", 0.0)
            low_price    = window_data.get("low_price", 0.0)
            total_volume = window_data.get("total_volume", 0)
            window_start = window_data.get("window_start", "")
            window_end   = window_data.get("window_end", "")

            if not symbol or open_price == 0:
                return f"SKIP:{symbol}"

            # Price move in window
            price_move_pct = ((close_price - open_price) / open_price) * 100 if open_price else 0.0
            high_low_pct   = ((high_price - low_price) / low_price) * 100 if low_price else 0.0

            # Rolling average volume (exponential moving average)
            avg_vol = self.avg_volumes.get(symbol, total_volume)
            self.avg_volumes[symbol] = avg_vol * 0.9 + total_volume * 0.1
            volume_ratio = total_volume / avg_vol if avg_vol > 0 else 1.0

            # Detect volatility
            price_spike  = abs(price_move_pct) >= self.price_threshold
            volume_spike = volume_ratio >= self.volume_multiplier

            if not (price_spike or volume_spike):
                return f"NORMAL:{symbol}:{price_move_pct:.2f}%"

            # Build volatility event document
            direction = "UP" if price_move_pct > 0 else "DOWN"
            triggers  = []
            if price_spike:
                triggers.append(f"price moved {price_move_pct:+.2f}% in {WINDOW_MINUTES} minutes")
            if volume_spike:
                triggers.append(f"volume was {volume_ratio:.1f}x the rolling average")

            now_iso = datetime.now(tz=timezone.utc).isoformat()
            doc = (
                f"{symbol} experienced a volatility event on {window_end[:10]}. "
                f"Price moved {price_move_pct:+.2f}% ({direction}) from ${open_price:.2f} to ${close_price:.2f} "
                f"in a {WINDOW_MINUTES}-minute window (high ${high_price:.2f}, low ${low_price:.2f}). "
                f"Volume: {total_volume:,} shares ({volume_ratio:.1f}x average). "
                f"Triggers: {'; '.join(triggers)}."
            )

            doc_id = f"vol_{symbol}_{hashlib.md5(window_start.encode()).hexdigest()[:10]}"

            metadata = {
                "source":           "flink_volatility_detector",
                "ticker":           symbol,
                "event_date":       window_end[:10] if window_end else now_iso[:10],
                "window_start":     window_start,
                "window_end":       window_end,
                "open_price":       float(open_price),
                "close_price":      float(close_price),
                "high_price":       float(high_price),
                "low_price":        float(low_price),
                "price_move_pct":   float(round(price_move_pct, 4)),
                "high_low_range_pct": float(round(high_low_pct, 4)),
                "total_volume":     int(total_volume),
                "volume_ratio":     float(round(volume_ratio, 2)),
                "direction":        direction,
                "price_spike":      price_spike,
                "volume_spike":     volume_spike,
                "window_minutes":   WINDOW_MINUTES,
                "data_type":        "volatility_event",
                "event_type":       "volatility",
                "ingested_via":     "flink_stream",
                "detected_at":      now_iso,
            }

            embedding = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=doc,
            ).data[0].embedding

            self.collection.upsert(
                documents=[doc],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            return f"ALERT:{symbol}:{price_move_pct:+.2f}%:vol={volume_ratio:.1f}x"

        except Exception as e:
            return f"ERROR:{e}"


def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)

    kafka_source = (
        KafkaSource.builder()
        .set_bootstrap_servers(KAFKA_BROKERS)
        .set_topics("market.trades")
        .set_group_id("flink-volatility-detector")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),
        "Finnhub Trade Source",
    )

    results = (
        stream
        .map(TradeDeserializer())
        .filter(lambda t: bool(t.get("symbol")))
        .map(TradeToWindowEntry())
        .key_by(lambda t: t["symbol"])
        .window(TumblingProcessingTimeWindows.of(Time.minutes(WINDOW_MINUTES)))
        .reduce(WindowAggregator())
        .map(VolatilityEventSink())
    )

    results.print()

    env.execute("FinSight Volatility Detector")


if __name__ == "__main__":
    main()
