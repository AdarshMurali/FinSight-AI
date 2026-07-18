"""
PyFlink Job: Real-Time Volatility Detector
===========================================
Reads live trades from Kafka topic 'market.trades', applies a tumbling
window per symbol (size configurable, see WINDOW_MINUTES below), and
writes two independent kinds of volatility event documents to ChromaDB's
'volatility_events' collection:
  - scope="window": price/volume spike within a single window
  - scope="daily":  cumulative price move / volume pace since the day's
    open, catching a slow bleed that never trips any single window's
    thresholds (at most one per symbol per day)

The four threshold values (window price %, window volume x, daily price %,
daily volume x) are read from SSM Parameter Store (/finsight/volatility_*)
and re-polled every SSM_REFRESH_SECONDS while the job runs, so they can be
tuned without a redeploy. Falls back to the DEFAULT_* constants below --
logging a warning -- if SSM is unreachable or the IAM permission isn't
present (e.g. running locally without an instance profile), so a
Parameter Store hiccup never takes the whole stream down.

WINDOW_MINUTES itself is different: it's baked into the Flink job graph at
submission time (TumblingProcessingTimeWindows), so it's read once from SSM
at module-import time, not polled -- changing it requires resubmitting the
job, not just waiting out the refresh interval.

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

from secrets_loader import load_aws_secrets
load_aws_secrets()

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
DEFAULT_PRICE_MOVE_THRESHOLD_PCT = 1.5   # Flag if price moves >1.5% in a window
DEFAULT_VOLUME_SPIKE_MULTIPLIER  = 2.0   # Flag if volume > 2x average
DEFAULT_DAILY_PRICE_MOVE_THRESHOLD_PCT = 5.0   # Flag if cumulative move since day's open >5%
DEFAULT_DAILY_VOLUME_MULTIPLIER        = 3.0   # Flag if day's cumulative volume > 3x expected pace
DEFAULT_WINDOW_MINUTES                 = 15    # 5 min was confirmed live to almost never trip on price

SSM_PARAM_PRICE_THRESHOLD         = "/finsight/volatility_price_threshold_pct"
SSM_PARAM_VOLUME_MULTIPLIER       = "/finsight/volatility_volume_spike_multiplier"
SSM_PARAM_DAILY_PRICE_THRESHOLD   = "/finsight/volatility_daily_price_threshold_pct"
SSM_PARAM_DAILY_VOLUME_MULTIPLIER = "/finsight/volatility_daily_volume_multiplier"
SSM_PARAM_WINDOW_MINUTES          = "/finsight/volatility_window_minutes"
SSM_REFRESH_SECONDS                = int(os.getenv("SSM_REFRESH_SECONDS", "300"))


def _fetch_window_minutes() -> int:
    """Window size is baked into the Flink job graph at submission time
    (TumblingProcessingTimeWindows below) -- unlike the threshold values,
    it can't be hot-reloaded by a running job, so this is read once here
    at module-import time, not inside the periodic threshold refresh."""
    try:
        import boto3
        ssm = boto3.client("ssm", region_name=AWS_REGION)
        return int(ssm.get_parameter(Name=SSM_PARAM_WINDOW_MINUTES)["Parameter"]["Value"])
    except Exception as e:
        print(f"[WARN] Could not fetch window size from SSM, using default {DEFAULT_WINDOW_MINUTES}m: {e}")
        return DEFAULT_WINDOW_MINUTES


WINDOW_MINUTES = _fetch_window_minutes()


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

        # Day-scoped cumulative tracking (Part B) -- reset whenever the
        # trading date changes, see _roll_day_if_needed().
        self.current_day: str = ""
        self.day_open_price: dict[str, float] = {}
        self.day_cum_volume: dict[str, int] = {}
        self.day_windows_seen: dict[str, int] = {}
        self.day_alerted: set[str] = set()

        try:
            import boto3
            self.ssm = boto3.client("ssm", region_name=AWS_REGION)
        except Exception as e:
            print(f"[WARN] boto3/SSM client unavailable, using default thresholds only: {e}")
            self.ssm = None

        self.price_threshold        = DEFAULT_PRICE_MOVE_THRESHOLD_PCT
        self.volume_multiplier      = DEFAULT_VOLUME_SPIKE_MULTIPLIER
        self.daily_price_threshold  = DEFAULT_DAILY_PRICE_MOVE_THRESHOLD_PCT
        self.daily_volume_multiplier = DEFAULT_DAILY_VOLUME_MULTIPLIER
        self._last_threshold_refresh = 0.0
        self._refresh_thresholds()

    def _refresh_thresholds(self):
        """Best-effort pull of all four thresholds from SSM. Keeps last-known-good
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
            self.daily_price_threshold = float(
                self.ssm.get_parameter(Name=SSM_PARAM_DAILY_PRICE_THRESHOLD)["Parameter"]["Value"]
            )
            self.daily_volume_multiplier = float(
                self.ssm.get_parameter(Name=SSM_PARAM_DAILY_VOLUME_MULTIPLIER)["Parameter"]["Value"]
            )
        except Exception as e:
            print(
                f"[WARN] SSM threshold refresh failed, keeping price={self.price_threshold} "
                f"volume={self.volume_multiplier} daily_price={self.daily_price_threshold} "
                f"daily_volume={self.daily_volume_multiplier}: {e}"
            )

    def _roll_day_if_needed(self, window_date: str):
        """Reset all day-scoped state the first time we see a new trading date."""
        if window_date == self.current_day:
            return
        self.current_day = window_date
        self.day_open_price.clear()
        self.day_cum_volume.clear()
        self.day_windows_seen.clear()
        self.day_alerted.clear()

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

            now_iso = datetime.now(tz=timezone.utc).isoformat()
            window_date = window_end[:10] if window_end else now_iso[:10]

            # Price move in window
            price_move_pct = ((close_price - open_price) / open_price) * 100 if open_price else 0.0
            high_low_pct   = ((high_price - low_price) / low_price) * 100 if low_price else 0.0

            # Rolling average volume (exponential moving average)
            avg_vol = self.avg_volumes.get(symbol, total_volume)
            self.avg_volumes[symbol] = avg_vol * 0.9 + total_volume * 0.1
            volume_ratio = total_volume / avg_vol if avg_vol > 0 else 1.0

            # ── Day-scoped cumulative check (Part B) -- independent of the
            # per-window check below; a slow bleed across the day with no
            # single window ever tripping the thresholds still gets caught.
            self._roll_day_if_needed(window_date)
            self.day_windows_seen[symbol] = self.day_windows_seen.get(symbol, 0) + 1
            if symbol not in self.day_open_price:
                self.day_open_price[symbol] = open_price
            self.day_cum_volume[symbol] = self.day_cum_volume.get(symbol, 0) + total_volume

            day_open = self.day_open_price[symbol]
            daily_price_move_pct = ((close_price - day_open) / day_open) * 100 if day_open else 0.0
            daily_volume_baseline = avg_vol * self.day_windows_seen[symbol]
            daily_volume_ratio = (
                self.day_cum_volume[symbol] / daily_volume_baseline if daily_volume_baseline > 0 else 1.0
            )
            daily_price_spike  = abs(daily_price_move_pct) >= self.daily_price_threshold
            daily_volume_spike = daily_volume_ratio >= self.daily_volume_multiplier

            if (daily_price_spike or daily_volume_spike) and symbol not in self.day_alerted:
                self.day_alerted.add(symbol)
                try:
                    daily_direction = "UP" if daily_price_move_pct > 0 else "DOWN"
                    daily_triggers = []
                    if daily_price_spike:
                        daily_triggers.append(
                            f"cumulative price move since today's open was {daily_price_move_pct:+.2f}%"
                        )
                    if daily_volume_spike:
                        daily_triggers.append(
                            f"today's volume is running {daily_volume_ratio:.1f}x the typical pace for this point in the day"
                        )
                    daily_doc = (
                        f"{symbol} has moved {daily_price_move_pct:+.2f}% ({daily_direction}) since today's open "
                        f"(${day_open:.2f} -> ${close_price:.2f}) as of {window_date}. "
                        f"Volume today: {self.day_cum_volume[symbol]:,} shares "
                        f"({daily_volume_ratio:.1f}x the typical pace so far). "
                        f"Triggers: {'; '.join(daily_triggers)}."
                    )
                    daily_embedding = self.openai.embeddings.create(
                        model="text-embedding-3-small",
                        input=daily_doc,
                    ).data[0].embedding
                    self.collection.upsert(
                        documents=[daily_doc],
                        embeddings=[daily_embedding],
                        metadatas=[{
                            "source":         "flink_volatility_detector",
                            "ticker":         symbol,
                            "event_date":     window_date,
                            "day_open_price": float(day_open),
                            "close_price":    float(close_price),
                            "price_move_pct": float(round(daily_price_move_pct, 4)),
                            "total_volume":   int(self.day_cum_volume[symbol]),
                            "volume_ratio":   float(round(daily_volume_ratio, 2)),
                            "direction":      daily_direction,
                            "price_spike":    daily_price_spike,
                            "volume_spike":   daily_volume_spike,
                            "scope":          "daily",
                            "data_type":      "volatility_event",
                            "event_type":     "volatility",
                            "ingested_via":   "flink_stream",
                            "detected_at":    now_iso,
                        }],
                        ids=[f"vol_daily_{symbol}_{window_date}"],
                    )
                except Exception as e:
                    print(f"[WARN] Failed to write daily volatility doc for {symbol}: {e}")

            # Detect volatility (per-window)
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

            doc = (
                f"{symbol} experienced a volatility event on {window_date}. "
                f"Price moved {price_move_pct:+.2f}% ({direction}) from ${open_price:.2f} to ${close_price:.2f} "
                f"in a {WINDOW_MINUTES}-minute window (high ${high_price:.2f}, low ${low_price:.2f}). "
                f"Volume: {total_volume:,} shares ({volume_ratio:.1f}x average). "
                f"Triggers: {'; '.join(triggers)}."
            )

            doc_id = f"vol_{symbol}_{hashlib.md5(window_start.encode()).hexdigest()[:10]}"

            metadata = {
                "source":           "flink_volatility_detector",
                "ticker":           symbol,
                "event_date":       window_date,
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
                "scope":            "window",
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
