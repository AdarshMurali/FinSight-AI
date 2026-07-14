"""
FinSight AI — EC2 Market Hours Scheduler
=========================================
Lambda function triggered by two EventBridge Scheduler rules:
  - 9:20 AM ET Mon-Fri  → action=start  (starts the Flink EC2 instance)
  - 4:25 PM ET Mon-Fri  → action=stop   (stops the Flink EC2 instance)

The cron already on the Flink EC2 handles pipeline start/stop:
  - 9:25 AM ET → start_pipeline.sh
  - 4:15 PM ET → stop_pipeline.sh

This Lambda only manages the EC2 instance (power on/off).
NYSE holidays are checked before any action — on holidays, Lambda exits silently.

Update NYSE_HOLIDAYS each January for the new year.

NOTE (2026-07-14): finsight-chromadb was removed from this scheduler.
It now also hosts the FastAPI backend, MCP server, and Redis/Valkey — all
always-on production services — so it must never be auto-stopped. Only
add it back if it reverts to being a dev-only, market-hours resource.
"""

import boto3
import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
REGION      = "ap-south-1"
INSTANCE_IDS = [
    "i-06df445415d082798",   # finsight-flink (t3.medium) — market-hours only
]

# NYSE holidays — update each January
# Source: https://www.nyse.com/markets/hours-calendars
NYSE_HOLIDAYS = {
    # 2026
    "2026-01-01",   # New Year's Day
    "2026-01-19",   # Martin Luther King Jr. Day
    "2026-02-16",   # Presidents' Day
    "2026-04-03",   # Good Friday
    "2026-05-25",   # Memorial Day
    "2026-07-03",   # Independence Day (observed, Jul 4 falls on Saturday)
    "2026-09-07",   # Labor Day
    "2026-11-26",   # Thanksgiving Day
    "2026-12-25",   # Christmas Day
    # 2027 — add next January
}

# ── Handler ───────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    today = datetime.date.today().isoformat()
    action = event.get("action", "start")

    if today in NYSE_HOLIDAYS:
        print(f"[SKIP] {today} is a NYSE holiday. No action taken.")
        return {"status": "skipped", "reason": "NYSE holiday", "date": today}

    ec2 = boto3.client("ec2", region_name=REGION)

    if action == "start":
        response = ec2.start_instances(InstanceIds=INSTANCE_IDS)
        states = {i["InstanceId"]: i["CurrentState"]["Name"] for i in response["StartingInstances"]}
        print(f"[START] {today} — {states}")
        return {"status": "started", "instances": states}

    elif action == "stop":
        response = ec2.stop_instances(InstanceIds=INSTANCE_IDS)
        states = {i["InstanceId"]: i["CurrentState"]["Name"] for i in response["StoppingInstances"]}
        print(f"[STOP] {today} — {states}")
        return {"status": "stopped", "instances": states}

    else:
        print(f"[ERROR] Unknown action: {action}")
        return {"status": "error", "reason": f"unknown action: {action}"}
