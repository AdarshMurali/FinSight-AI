"""
PyFlink Job: News Sentiment Stream
===================================
Reads from Kafka topic 'market.news', scores each article with VADER sentiment,
generates an embedding via OpenAI, and upserts the enriched document into
ChromaDB 'market_news' collection.

Submit from inside the Flink container:
    docker exec finsight-flink-jobmanager \
        flink run -py /opt/flink/jobs/news_sentiment_job.py

Runs continuously (streaming mode) — Ctrl+C to cancel, or use Flink UI.
"""

import os
import sys
import json
import hashlib
import time
from datetime import datetime, timezone

# PyFlink imports
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer,
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.watermark_strategy import WatermarkStrategy
from pyflink.datastream.functions import MapFunction

# External packages (installed in custom Flink Docker image)
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from openai import OpenAI
import chromadb

# ── Config (env vars injected via docker-compose env_file) ───────────────
KAFKA_BROKERS    = os.getenv("KAFKA_BROKERS", "kafka:29092")
CHROMA_HOST      = os.getenv("CHROMA_HOST",   "host.docker.internal")
CHROMA_PORT      = int(os.getenv("CHROMA_PORT", "8001"))
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
COLLECTION_NAME  = "market_news"
EMBED_BATCH_SIZE = 10


class NewsEnricher(MapFunction):
    """Scores VADER sentiment, embeds, and upserts each article to ChromaDB."""

    def open(self, runtime_context):
        self.analyzer    = SentimentIntensityAnalyzer()
        self.openai      = OpenAI(api_key=OPENAI_API_KEY)
        self.chroma      = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        self.collection  = self.chroma.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.buffer_docs:  list[str]  = []
        self.buffer_meta:  list[dict] = []
        self.buffer_ids:   list[str]  = []

    def map(self, raw_json: str) -> str:
        try:
            article = json.loads(raw_json)
            headline = article.get("headline", "")
            summary  = article.get("summary", "")
            ticker   = article.get("ticker", "")

            if not headline:
                return f"SKIP:empty_headline:{ticker}"

            # Build document text
            text = f"{headline}: {summary}" if summary else headline

            # VADER sentiment
            scores = self.analyzer.polarity_scores(text)
            compound = scores["compound"]
            if compound >= 0.05:
                sentiment_label = "Bullish"
            elif compound <= -0.05:
                sentiment_label = "Bearish"
            else:
                sentiment_label = "Neutral"

            # Stable dedup ID
            raw_id = article.get("id") or article.get("url") or headline
            doc_id = f"fn_news_{ticker}_{hashlib.md5(str(raw_id).encode()).hexdigest()[:12]}"

            metadata = {
                "source":           "finnhub",
                "ticker":           ticker,
                "title":            headline,
                "publisher":        article.get("source", ""),
                "url":              article.get("url", ""),
                "published_at":     article.get("published_at", ""),
                "category":         article.get("category", ""),
                "sentiment_score":  float(compound),
                "sentiment_pos":    float(scores["pos"]),
                "sentiment_neg":    float(scores["neg"]),
                "sentiment_label":  sentiment_label,
                "data_type":        "news",
                "event_type":       "news",
                "ingested_via":     "flink_stream",
            }

            # Embed + upsert
            embedding = self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            ).data[0].embedding

            self.collection.upsert(
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            return f"OK:{ticker}:{sentiment_label}:{compound:.3f}"

        except Exception as e:
            return f"ERROR:{e}"


def main():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)

    kafka_source = (
        KafkaSource.builder()
        .set_bootstrap_servers(KAFKA_BROKERS)
        .set_topics("market.news")
        .set_group_id("flink-news-sentiment")
        .set_starting_offsets(KafkaOffsetsInitializer.latest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    stream = env.from_source(
        kafka_source,
        WatermarkStrategy.no_watermarks(),
        "Finnhub News Source",
    )

    results = stream.map(NewsEnricher())
    results.print()  # Shows OK/ERROR lines in Flink task logs

    env.execute("FinSight News Sentiment Stream")


if __name__ == "__main__":
    main()
