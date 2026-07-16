#!/bin/bash
# ============================================================
# stop_pipeline.sh — called by cron at 4:15 PM ET Mon-Fri
# Cancels the Flink job and stops the trade producer
# Docker stack stays up so next morning restart is fast
# ============================================================

REPO=/home/ec2-user/FinSight-AI
COMPOSE_FILE=$REPO/aws/ec2-flink/docker-compose.yml
# Was /var/log/finsight-pipeline.log -- stale (start_pipeline.sh already used
# the correct path; this one just silently failed to write and only ever
# surfaced via cron's own log redirect). Fixed to match, 2026-07-16.
LOG=/home/ec2-user/logs/finsight-pipeline.log
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$LOG"; }

log "=== Stopping FinSight streaming pipeline ==="

# ── Step 1: Stop trade + news producers ──────────────────────
# Containerized (2026-07-16, restart: unless-stopped) -- `docker compose
# stop` instead of the old PID-file kill/pkill fallback.
docker compose -f "$COMPOSE_FILE" stop trade-producer news-producer
log "Trade + news producers stopped"

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
# To fully stop: docker compose -f "$COMPOSE_FILE" down

log "=== Pipeline stopped. Docker stack left running for fast restart. ==="
