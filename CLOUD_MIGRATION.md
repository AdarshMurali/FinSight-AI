# Cloud Migration Tracker

**Goal**: Move fully off local infrastructure. Destination is AWS today — could be Azure, Databricks, or something else for a given piece later. This file exists so "what's actually off local vs. still local" has one place to check, instead of being buried across `status.md`/`plan.md`.

**Rule going forward**: any time something is pushed from local to a cloud target (or moved between cloud targets), update this file in the same unit of work — not batched at the end.

---

## ✅ Already on Cloud

| Component | Platform | Location | Status | Notes |
|---|---|---|---|---|
| SQL Server | Azure SQL | `finsight-sql-server.database.windows.net` | Live | Free tier, auto-pauses after ~1hr idle (~20-60s cold start) |
| ChromaDB | AWS EC2 `finsight-chromadb` (t3.micro) | `13.206.225.80:8001` | Live | 36,595+ docs across 10 collections; Flink writes to it live |
| Flink + Kafka pipeline | AWS EC2 `finsight-flink` (t3.medium) | `13.233.21.229` | Live | Market-hours only — auto start (9:20 ET) / stop (16:45 ET) via EventBridge + Lambda |
| `risk_job.py` (daily risk computation) | Same Flink EC2, via EventBridge → SSM | `/home/ec2-user/FinSight-AI/backend/scripts/risk_job.py` | Live, fixed 2026-07-07 | Runs Mon–Fri 16:10 ET. Was silently 100% failing since creation (wrong path) until fixed this session. |
| `price_update_job.py` (daily price refresh) | Same Flink EC2, via EventBridge → SSM (`finsight-daily-price-update`) | `/home/ec2-user/FinSight-AI/backend/scripts/price_update_job.py` | Live, deployed 2026-07-08 | Runs Mon–Fri 16:00 ET, 10 min before `risk_job.py`. Verified via manual SSM trigger before relying on the schedule (lesson from `risk_job.py`'s silent failure — see [[eventbridge-risk-job]]). |
| MCP Server | Same Flink EC2 (SSE transport) | `http://13.233.21.229:8002/sse` | Live | |
| Frontend | Vercel | `https://frontend-sandy-seven-21.vercel.app` | Live | Deployed from git |

**AWS account note**: this infra lives in account `301276846405` (alias `aws-adarsh-lavanya`), not the local CLI's default profile — use `--profile lavanya`. See `aws_deployment.md` memory for full detail.

---

## ⚠️ Still Local Only — Pending Push

| Component | Current State | Blocking on | Priority |
|---|---|---|---|
| FastAPI backend (`main.py` + all routers/services) | Runs only on `localhost:8000` | Phase 6 Task 6.3 (CI/CD + cloud deploy) — not started | High — this is the main app, everything else is scaffolding around it |
| AI chat fixes (`ai_chat_service.py`, `ai_tools.py`, `query_engine.py`) — 2026-07-07 Bug 1 fixes | Verified locally only, via local backend hitting AWS ChromaDB/Azure SQL | Same as above — ships once the backend itself is deployed | Tied to backend deploy above |
| Next.js frontend (dev copy) | Runs on `localhost:3000` | N/A — Vercel is already production; local copy is dev-only | Low, not blocking |

`models.py` (`Security.current_price` added 2026-07-07) is now on EC2 too, pushed alongside `price_update_job.py` — but NOT yet in the local FastAPI backend's deployed environment, since that backend isn't deployed anywhere (see row above).

---

## Explored and Rejected: Lambda for `price_update_job.py`

Built a full Lambda container-image pipeline for this job (Dockerfile with msodbcsql18 on Debian, ECR repo `finsight-price-update`, Lambda function, IAM execution role) before deciding against it. **Root blocker**: Azure SQL's firewall is IP-allowlist based, and a Lambda function without VPC config egresses through AWS's shared, non-static IP pool — confirmed via a real failed invocation (`Client with IP address '13.200.222.100' is not allowed to access the server`). Fixing this properly requires a NAT Gateway (~$32+/month) or a dedicated NAT instance (~$3-4/month) for a stable egress IP — both defeat the point of avoiding an always-on EC2 for this job, especially since `finsight-flink`'s IP is already allow-listed and already running during market hours at $0 marginal cost.

**Cleaned up 2026-07-09**: ECR repo `finsight-price-update`, Lambda function `finsight-price-update`, and IAM role `finsight-price-update-role` were all manually deleted (confirmed gone via `aws ecr describe-repositories` / `aws lambda get-function` / `aws iam get-role`, all now return not-found). The container-image-for-Lambda pattern is still documented above if it's worth reapplying to a future job that talks to AWS-native services (no IP-firewall problem there).

---

## Not Started (Phase 6+, no local/cloud split yet)
- Dockerization (`plan.md` Task 6.1)
- Redis caching (`plan.md` Task 6.2)
- CI/CD pipeline (`plan.md` Task 6.3)
- JWT auth / multi-tenant portfolio access (`plan.md` Task 6.4)

---

## Session Log
- **2026-07-07**: Fixed `risk_job.py`'s EventBridge schedule (was pointing at a stale, out-of-sync code copy — 100% failure rate since creation on 6/27, never noticed because manual test runs during setup were mistaken for successful automated runs). Consolidated to one code copy on the Flink EC2. Fixed two AI-chat data-staleness bugs (date injection, live quote tool, recency-aware RAG ranking) — local only, not yet deployed. Built and verified `price_update_job.py` locally — not yet pushed to EC2 or scheduled.
- **2026-07-08**: Confirmed `risk_job.py`'s automated run fired correctly overnight for the first time ever. Explored moving `price_update_job.py` to Lambda (full container-image pipeline built, hit Azure SQL firewall/static-IP blocker, decided against it — see "Explored and Rejected" above). Deployed `price_update_job.py` + updated `models.py` to the Flink EC2, created `finsight-daily-price-update` EventBridge schedule (16:00 ET, before `risk_job.py`), verified via manual SSM trigger before trusting the schedule.
- **2026-07-09**: Deleted the unused Lambda/ECR/IAM artifacts from the rejected Lambda attempt (confirmed gone via AWS CLI).

---

## Resume Steps for Next Session
1. Confirm `finsight-daily-price-update`'s first real automated fire succeeded (16:00 ET) — check `/var/log/finsight_price_update.log` on the EC2 and/or `Securities.current_price` timestamps.
2. Push the FastAPI backend itself to the cloud (Phase 6 Task 6.3) — this is the biggest remaining "still local" item; the 2026-07-07 AI chat fixes and `models.py` change only take effect once this ships.
3. Continue with remaining pending items per `plan.md` (Phase 6, JWT auth/multi-tenant access, etc.).
