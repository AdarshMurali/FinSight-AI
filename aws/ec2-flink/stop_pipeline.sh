#!/bin/bash
# ============================================================
# stop_pipeline.sh — called by cron at 4:15 PM ET Mon-Fri
# Cancels the Flink job and stops the trade producer
# Docker stack stays up so next morning restart is fast
# ============================================================

LOG=/var/log/finsight-pipeline.log
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$LOG"; }

log "=== Stopping FinSight streaming pipeline ==="

# ── Step 1: Stop trade producer ───────────────────────────────
if [ -f /tmp/trade_producer.pid ]; then
  PID=$(cat /tmp/trade_producer.pid)
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    log "Trade producer stopped (PID $PID)"
  else
    log "Trade producer was not running (PID $PID already gone)"
  fi
  rm -f /tmp/trade_producer.pid
else
  pkill -f finnhub_trade_producer.py 2>/dev/null || true
  log "Trade producer stopped (fallback pkill)"
fi

# ── Step 1b: Stop news producer ──────────────────────────────
if [ -f /tmp/news_producer.pid ]; then
  PID=$(cat /tmp/news_producer.pid)
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    log "News producer stopped (PID $PID)"
  else
    log "News producer was not running (PID $PID already gone)"
  fi
  rm -f /tmp/news_producer.pid
else
  pkill -f finnhub_news_producer.py 2>/dev/null || true
  log "News producer stopped (fallback pkill)"
fi

# ── Step 2: Cancel running Flink jobs ────────────────────────
log "Cancelling Flink jobs..."
RUNNING_JOBS=$(curl -s http://localhost:8082/jobs/overview | \
  grep -o '"jid":"[^"]*","name":"[^"]*","[^}]*"state":"RUNNING"' | \
  grep -o '"jid":"[^"]*"' | cut -d'"' -f4)

if [ -z "$RUNNING_JOBS" ]; then
  log "No running Flink jobs found."
else
  for JID in $RUNNING_JOBS; do
    curl -s -X PATCH "http://localhost:8082/jobs/$JID?mode=cancel" > /dev/null
    log "Cancelled job: $JID"
  done
fi

# ── Step 3: Kafka + Flink stack stays running ─────────────────
# We leave docker-compose up intentionally:
# - Kafka retains the market.trades topic (useful for debugging)
# - Flink cluster restarts faster tomorrow without a cold boot
# To fully stop: docker compose -f /home/ubuntu/FinSight-AI/aws/ec2-flink/docker-compose.yml down

log "=== Pipeline stopped. Docker stack left running for fast restart. ==="
