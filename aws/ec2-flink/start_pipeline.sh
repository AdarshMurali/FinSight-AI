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

# ── Step 5+6: Submit jobs, resubmitting only when code changed ──
# Not idempotent before 2026-07-17: every invocation called `flink run`
# unconditionally, so a manual retry, a re-approved CD deploy, or cron
# overlapping either of those created a second concurrent instance of the
# same job. With only 4 task slots total, two "FinSight Volatility Detector"
# + two "FinSight News Sentiment Stream" instances fighting over them left
# every one of the four in a terminal FAILED state within ~20 minutes
# (NoResourceAvailableException, no restart strategy configured) -- found
# live via a production-flink CD approval test.
#
# A plain "skip if a RUNNING job with this name exists" check (the
# first fix) closes that hole but opens a different one: it can't tell
# a healthy job apart from a *stale* one, so editing volatility_detector_job.py
# or news_sentiment_job.py and redeploying while the old job is still up
# silently never loads the new code. Fixed here by tracking a content hash
# of each job's .py file alongside the running job -- same name AND same
# hash means truly nothing changed (skip, matching the first fix's
# behavior exactly), same name but different hash means the code moved out
# from under a still-running job (cancel it, then resubmit), and no running
# job at all just submits fresh either way.
VERSION_DIR=/home/ec2-user/.flink_job_versions
# world-writable on purpose: this script runs as root when CD invokes it via
# SSM but as ec2-user when cron invokes it directly, and whichever one
# creates the directory/files first would otherwise leave the other unable
# to write here on its next run (the exact ownership-mismatch pattern that
# broke git pull and SSH for this same root-vs-ec2-user split earlier today).
# Contents are just non-sensitive hash markers, so permissive perms cost
# nothing here.
mkdir -p "$VERSION_DIR"
chmod 777 "$VERSION_DIR"

get_running_job_id() {
  # Flatten out the nested "tasks":{...} object first -- grep -oE '\{[^{}]*\}'
  # can't see past nested braces, so without this it would silently match
  # each job's inner tasks object instead of the job object itself and never
  # find "name" at all (verified against a captured jobs/overview payload
  # before trusting this).
  curl -s http://localhost:8082/jobs/overview \
    | sed 's/,"tasks":{[^}]*}//g' \
    | grep -oE '\{[^{}]*\}' \
    | grep -F "\"name\":\"$1\"" \
    | grep '"state":"RUNNING"' \
    | grep -oE '"jid":"[^"]*"' \
    | head -1 \
    | cut -d'"' -f4
}

deploy_job() {
  local job_name="$1"      # Flink's own display name, e.g. "FinSight Volatility Detector"
  local job_file="$2"      # filename only, e.g. volatility_detector_job.py
  local version_key="$3"   # filesystem-safe key for the stored hash, e.g. volatility_detector

  local current_hash
  current_hash=$(sha256sum "$REPO/backend/flink/$job_file" | cut -d' ' -f1)
  local version_file="$VERSION_DIR/$version_key.sha256"
  local stored_hash=""
  [ -f "$version_file" ] && stored_hash=$(cat "$version_file")

  local running_jid
  running_jid=$(get_running_job_id "$job_name")

  if [ -n "$running_jid" ] && [ "$current_hash" = "$stored_hash" ]; then
    log "$job_name already RUNNING with current code ($running_jid), skipping submission."
    return
  fi

  if [ -n "$running_jid" ]; then
    log "$job_name RUNNING ($running_jid) but code changed, cancelling before resubmitting..."
    docker exec finsight-flink-jobmanager flink cancel "$running_jid"
  fi

  log "Submitting $job_name Flink job..."
  docker exec finsight-flink-jobmanager \
    flink run --detached -py "/opt/flink/jobs/$job_file"
  echo "$current_hash" > "$version_file"
  chmod 666 "$version_file"
}

deploy_job "FinSight Volatility Detector" "volatility_detector_job.py" "volatility_detector"
deploy_job "FinSight News Sentiment Stream" "news_sentiment_job.py" "news_sentiment"

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
