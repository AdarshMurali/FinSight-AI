import os
from dotenv import load_dotenv

load_dotenv()

from secrets_loader import load_aws_secrets
load_aws_secrets()

# ── Kafka ─────────────────────────────────────────────────────────────────
# When running natively on Windows, producers connect via localhost:9092.
# When running inside Docker (Flink jobs), connect via kafka:29092.
KAFKA_BOOTSTRAP_SERVERS_EXTERNAL = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_BOOTSTRAP_SERVERS_INTERNAL = "kafka:29092"       # used by Flink jobs in Docker

# KAFKA_MODE=docker is set in aws/ec2-flink/docker-compose.yml for the
# trade-producer/news-producer services (2026-07-16) so they use the internal
# listener like the Flink jobs already do, instead of the external IP:9092
# route they need when running as bare host processes.
KAFKA_BOOTSTRAP_SERVERS = (
    KAFKA_BOOTSTRAP_SERVERS_INTERNAL if os.getenv("KAFKA_MODE") == "docker"
    else KAFKA_BOOTSTRAP_SERVERS_EXTERNAL
)

TOPIC_MARKET_NEWS   = "market.news"
TOPIC_MARKET_TRADES = "market.trades"

# ── Finnhub ───────────────────────────────────────────────────────────────
FINNHUB_API_KEY     = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_WS_URL      = f"wss://ws.finnhub.io?token={FINNHUB_API_KEY}"
FINNHUB_REST_BASE   = "https://finnhub.io/api/v1"

# ── ChromaDB ─────────────────────────────────────────────────────────────
# ChromaDB runs on the host at port 8001.
# From inside Docker, use host.docker.internal to reach it.
CHROMA_HOST_INTERNAL = "host.docker.internal"  # Flink jobs reach ChromaDB via this
CHROMA_HOST_EXTERNAL = "localhost"              # Producers / local scripts
CHROMA_PORT          = 8001

# ── OpenAI ───────────────────────────────────────────────────────────────
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL      = "text-embedding-3-small"

# ── Covered tickers ──────────────────────────────────────────────────────
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK.B",
    "JPM", "JNJ", "V", "WMT", "PG", "MA", "INTC", "NFLX",
    "MCD", "DIS", "KO", "PEP", "ABT", "TMO", "MRK", "IBM",
    "CSCO", "CAT", "F", "GM", "BA", "HON", "UNP", "AXP",
    "SPG", "XOM", "CVX", "COP", "MPC", "PSX", "VLO", "EQR",
    "VZ", "T", "TMUS", "DELL", "ORCL", "AMD", "PYPL", "ADBE",
    "AVGO", "INTU",
]

# News poll interval in seconds (Finnhub free: 60 req/min across all endpoints)
NEWS_POLL_INTERVAL_SECONDS = 120

# How many hours back to look for news on startup
NEWS_LOOKBACK_HOURS = 24
