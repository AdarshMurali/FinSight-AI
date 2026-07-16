#!/bin/bash
# ============================================================
# start_pipeline.sh — called by cron at 9:25 AM ET Mon-Fri
# Starts the streaming stack and submits the Flink job
# ============================================================
set -e

REPO=/home/ec2-user/FinSight-AI
COMPOSE_FILE=$REPO/aws/ec2-flink/docker-compose.yml
LOG=/home/ec2-user/logs/finsight-pipeline.log

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$LOG"; }

log "=== Starting FinSight streaming pipeline ==="

# ── Step 1: Start Docker stack ────────────────────────────────
log "Starting Kafka + Flink docker-compose..."
cd $REPO/aws/ec2-flink
docker compose -f docker-compose.yml up -d

# ── Step 2: Wait for Kafka to be ready ───────────────────────
log "Waiting for Kafka to be ready..."
for i in $(seq 1 30); do
  if docker exec finsight-kafka kafka-topics --bootstrap-server localhost:29092 --list &>/dev/null; then
    log "Kafka is ready."
    break
  fi
  sleep 5
done

# ── Step 3: Ensure Kafka topics exist ────────────────────────
log "Ensuring Kafka topics exist..."
docker exec finsight-kafka kafka-topics --bootstrap-server localhost:29092 \
  --create --if-not-exists --topic market.trades --partitions 1 --replication-factor 1
docker exec finsight-kafka kafka-topics --bootstrap-server localhost:29092 \
  --create --if-not-exists --topic market.news --partitions 1 --replication-factor 1
log "Kafka topics ready."

# ── Step 4: Wait for Flink JobManager ────────────────────────
log "Waiting for Flink JobManager REST API..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8082/overview &>/dev/null; then
    log "Flink JobManager is ready."
    break
  fi
  sleep 5
done

# ── Step 5: Submit volatility detector job ───────────────────
log "Submitting volatility detector Flink job..."
docker exec finsight-flink-jobmanager \
  flink run --detached -py /opt/flink/jobs/volatility_detector_job.py

# ── Step 6: Submit news sentiment job ────────────────────────
log "Submitting news sentiment Flink job..."
docker exec finsight-flink-jobmanager \
  flink run --detached -py /opt/flink/jobs/news_sentiment_job.py

log "Flink jobs submitted. Verifying state..."
sleep 10
curl -s http://localhost:8082/jobs/overview | \
  grep -o '"name":"[^"]*","[^}]*"state":"[^"]*"' | \
  while IFS= read -r line; do
    NAME=$(echo "$line" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    STATE=$(echo "$line" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
    log "  Job [$NAME] state: $STATE"
  done

# ── Step 7: Confirm Finnhub producers ────────────────────────
# Containerized (2026-07-16, restart: unless-stopped) -- already started by
# Step 1's `docker compose up -d` along with the rest of the stack. No more
# nohup/PID-file launch here: that's exactly what let the trade producer sit
# dead for ~18hrs on 2026-07-14 (nothing would restart it) and let duplicate
# processes accumulate (no PID cleanup before relaunch). A named container
# can't do either -- `up -d` on an existing one just leaves it running.
log "Confirming Finnhub producer containers..."
docker compose -f "$COMPOSE_FILE" ps trade-producer news-producer

log "=== Pipeline started successfully ==="
