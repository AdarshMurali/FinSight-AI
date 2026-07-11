# Cloud Migration Tracker

**Goal**: Move fully off local infrastructure. Destination is AWS today — could be Azure, Databricks, or something else for a given piece later. This file exists so "what's actually off local vs. still local" has one place to check, instead of being buried across `status.md`/`plan.md`.

**Rule going forward**: any time something is pushed from local to a cloud target (or moved between cloud targets), update this file in the same unit of work — not batched at the end.

---

## ✅ Already on Cloud

| Component | Platform | Location | Status | Notes |
|---|---|---|---|---|
| SQL Server | Azure SQL | `finsight-sql-server.database.windows.net` | Live | Free tier, auto-pauses after ~1hr idle (~20-60s cold start) |
| ChromaDB | AWS EC2 `finsight-chromadb` (t3.small, resized 2026-07-11 from t3.micro) | `13.206.225.80:8001` | Live | 36,595+ docs across 10 collections; Flink writes to it live |
| Flink + Kafka pipeline | AWS EC2 `finsight-flink` (t3.medium) | `13.233.21.229` | Live | Market-hours only — auto start (9:20 ET) / stop (16:45 ET) via EventBridge + Lambda |
| `risk_job.py` (daily risk computation) | Same Flink EC2, via EventBridge → SSM | `/home/ec2-user/FinSight-AI/backend/scripts/risk_job.py` | Live, fixed 2026-07-07 | Runs Mon–Fri 16:10 ET. Was silently 100% failing since creation (wrong path) until fixed this session. |
| `price_update_job.py` (daily price refresh) | Same Flink EC2, via EventBridge → SSM (`finsight-daily-price-update`) | `/home/ec2-user/FinSight-AI/backend/scripts/price_update_job.py` | Live, deployed 2026-07-08 | Runs Mon–Fri 16:00 ET, 10 min before `risk_job.py`. Verified via manual SSM trigger before relying on the schedule (lesson from `risk_job.py`'s silent failure — see [[eventbridge-risk-job]]). |
| MCP Server | ChromaDB EC2 (SSE transport), moved 2026-07-11 | `http://13.206.225.80:8002/sse` | Live | Moved off the Flink EC2 — see writeup below. Own isolated venv (`mcpvenv`), own systemd service (`finsight-mcp`), bound to the admin identity. |
| Frontend | Vercel | `https://www.fin-sightai.space` (also `https://frontend-sandy-seven-21.vercel.app`) | Live | Deployed from git; custom domain added 2026-07-09 |
| FastAPI backend | Same EC2 as ChromaDB (`13.206.225.80`), reused for $0 extra cost | `https://api.fin-sightai.space` | Live | Deployed 2026-07-09 — see below |

**AWS account note**: this infra lives in account `301276846405` (alias `aws-adarsh-lavanya`), not the local CLI's default profile — use `--profile lavanya`. See `aws_deployment.md` memory for full detail.

---

## ⚠️ Still Local Only — Pending Push

| Component | Current State | Blocking on | Priority |
|---|---|---|---|
| Next.js frontend (dev copy) | Runs on `localhost:3000` | N/A — Vercel is already production; local copy is dev-only | Low, not blocking |

FastAPI backend and its 2026-07-07 AI chat fixes are now live on EC2 (see "Already on Cloud" above) — no longer pending.

## Backend Cloud Deployment — Domain, Infra, Full Writeup (2026-07-09)

**Domain**: `fin-sightai.space`, registered via GoDaddy (1-year, UPI one-time payment, auto-renew off, 2FA + transfer lock enabled on the GoDaddy account). DNS hosted at GoDaddy (not Route53 — AWS credits explicitly exclude domain registration fees, and Route53 hosted-zone hosting wasn't worth the $0.50/mo when GoDaddy's own DNS manager is free).
- `api.fin-sightai.space` → `A` record → `13.206.225.80` (backend)
- `fin-sightai.space` → `A` record → `216.198.79.1` (Vercel), 308-redirects to `www`
- `www.fin-sightai.space` → `CNAME` → Vercel DNS target (frontend, canonical URL)

**Backend host**: reused the existing always-on ChromaDB EC2 (`13.206.225.80`, Amazon Linux 2023, t3.micro-class, 912MB RAM) instead of a new box — $0 marginal cost. Runs alongside the ChromaDB Docker container; ~180MB RAM for the backend process, leaves headroom that's fine for demo/interview traffic but worth watching if traffic grows (would need a t3.small resize if so).

**Setup performed**:
- `git sparse-checkout` clone (backend/ only, not the full repo — frontend/docs/aws stay off the production box) via a dedicated read-only GitHub Deploy Key (not a personal token)
- `python3.11` + venv (`backendvenv`) — numpy 2.1 requires 3.10+, box's default python3.9 wasn't enough
- Microsoft ODBC Driver 18 for SQL Server (`msodbcsql18` + `unixODBC-devel` via `dnf`, after adding Microsoft's RHEL9 repo) — Driver 17 (the app's config default) isn't available on AL2023, had to set `DB_ODBC_DRIVER=ODBC Driver 18 for SQL Server` in the EC2's `.env` to override
- Trimmed `requirements.txt` install: skipped `apache-flink`/`apache-beam` (~350MB, unused by the FastAPI app — only the separate Flink job scripts need it) and `confluent-kafka`/`celery` (unused). Added missing `scipy` (used by `risk_analytics.py`, was never in `requirements.txt` at all — same gap the MCP server venv had silently worked around)
- `systemd` service `finsight-backend.service` (not the `nohup`+pid pattern used for the MCP server — deliberate, this is the primary always-on surface and needs auto-restart on crash/reboot)
- `nginx` reverse proxy (127.0.0.1:8000 → public) + Certbot for the HTTPS cert. AL2023's `certbot` package does **not** ship a renewal timer/cron despite Certbot's own success message claiming it does — had to hand-roll `certbot-renew.service` + `.timer` (twice daily)
- Security group: opened 80/443 on the ChromaDB EC2's SG; SSH (22) re-allowed after discovering the old allow-listed home IP was stale (dynamic IP had changed)

**Code fixes made alongside deployment** (see git log on `adarsh` branch):
- `backend/main.py` — startup had no DB retry; ported the `wait_for_db()` cold-start-retry pattern from `risk_job.py` (Azure SQL auto-pause takes 20-40s to wake)
- `backend/routers/ws.py` — Kafka consumer hardcoded `bootstrap_servers="localhost:9092"`, breaks now that Kafka (Flink EC2) and the backend (ChromaDB EC2) are different boxes; now reads `KAFKA_BOOTSTRAP_SERVERS` env var like the Flink side already did. Only affects the live news-toast WebSocket feature — Kafka is market-hours-only anyway (Flink EC2 schedule), so this degrades gracefully outside those hours by design
- `backend/requirements.txt` — added missing `scipy`
- `frontend/app/page.tsx` — system-status footer strip had a hardcoded `"API localhost:8000"` label; now reads `NEXT_PUBLIC_API_URL` (cosmetic only, actual API calls were already correct)

**Verified end-to-end**: `/health`, `/docs`, `/api/portfolios` (real data) all working over HTTPS; systemd crash-recovery tested (kill + auto-restart); Certbot cert valid + renewal timer active; frontend confirmed calling the new backend domain via live network inspection (not stale localhost/ngrok config) — WS shows `CONNECTED` in the UI.

**Frontend auto-deploy fixed (2026-07-09, later same day)**: discovered the Vercel project had never actually been Git-connected — it was originally deployed via CLI, which is why `git push` did nothing and dashboard "Redeploy" just rebuilt stale commits (two hardcoded `"API localhost:8000"`-style display bugs went unnoticed through two redeploys because of this). Root cause: the "Vercel" GitHub App wasn't authorized on this private repo — fixed at `github.com/settings/installations`, then `vercel git connect` succeeded. Two project settings needed manual correction via `vercel api` (no CLI flag exists for either): `rootDirectory: "frontend"` (monorepo — without this, a git-triggered build tries to build from the repo root and fails) and confirmed `link.productionBranch: "adarsh"` (Vercel auto-detected this correctly on connect, no action needed). Verified with a real empty-commit push that auto-triggered a deployment reaching `readyState: READY`, `target: production`. Every push to `adarsh` now deploys automatically.

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
- **2026-07-09**: Deleted the unused Lambda/ECR/IAM artifacts from the rejected Lambda attempt (confirmed gone via AWS CLI). Pushed the FastAPI backend to the cloud (reused ChromaDB EC2), registered `fin-sightai.space` domain, wired up nginx+HTTPS, connected Vercel frontend to both the new backend and the custom domain — full writeup above. This was the last major "still local" item from Phase 6 Task 6.3.
- **2026-07-11**: Deployed Task 6.4 (JWT auth + multi-tenant portfolio access) and Task 5.2's event/AI alerts to production.
  - SSH to the backend EC2 (`13.206.225.80`) was timing out — its security group's SSH allow-list (`sg-0e48754e3d50f37dd`) had two stale home IPs from prior sessions; added the current IP via `aws ec2 authorize-security-group-ingress` (kept the stale entries rather than removing them).
  - Found `CORS_ORIGINS` in the EC2's `.env` was missing `https://www.fin-sightai.space` (the actual canonical frontend domain per the DNS setup above) — only had the bare apex and an old Vercel preview URL. Would have silently CORS-blocked the real production frontend the same way it did in local testing (`127.0.0.1` vs `localhost`). Fixed alongside adding `JWT_SECRET_KEY` (generated and appended server-side over SSH — never left the box, never touched the local transcript) and `COOKIE_SECURE=True`.
  - `git pull` + `pip install pyjwt[crypto] bcrypt` into the existing `backendvenv` + `systemctl restart finsight-backend` — same pattern as prior deploys.
  - Frontend: pushed to `adarsh`, Vercel auto-deployed (confirmed via the new `/login` route going live).
  - Verified fully end-to-end against the real production site in a browser: login → scoped dashboard (a demo manager sees exactly their 10 portfolios, not all 50) → WebSocket shows `CONNECTED` with per-connection price-tick filtering → logout.
  - **MCP server (Flink EC2) deliberately NOT deployed this round** — that box only runs weekdays 9:20am–4:45pm ET (auto start/stop via the Lambda scheduler) and was stopped at deploy time (Saturday). Its `mcp_server.py` now requires a `FINSIGHT_MCP_TOKEN` env var and fails closed without one — deploying it needs the token minted and wired into its process env in the same step, planned for the next weekday session rather than done opportunistically.
- **2026-07-11 (later same day)**: Relocated the MCP server from the Flink EC2 to the ChromaDB EC2, and resized the latter (t3.micro → t3.small).
  - **Why it was on the Flink EC2 in the first place**: sequencing, not design. Task 3.4b (MCP server) was built and deployed 2026-07-06, three days *before* the backend moved to the ChromaDB EC2 (2026-07-09) — at the time, the ChromaDB EC2 only ran the ChromaDB Docker container with no Python app environment at all, while the Flink EC2 already had a working DB-capable venv (`mcpvenv`, built for `risk_job.py`). Reusing that was the path of least resistance. Once the backend moved to the ChromaDB EC2, the MCP server should have moved too — it has zero relationship to real-time data ingestion — but that consolidation never happened, leaving it inheriting the Flink EC2's market-hours-only schedule for no real reason.
  - **Capacity check before touching anything**: real numbers on the ChromaDB EC2 (t3.micro, 912MB) showed only 47MB "available" memory and zero swap configured — ChromaDB (360MB) + backend (217MB) already consumed nearly the entire box. Since Redis (Task 6.2) was also planned for this same box per `plan.md`, the full target inventory (ChromaDB + backend + MCP + Redis, roughly 840-940MB) would not have fit on a t3.micro with any safety margin. Resized to **t3.small (1.9GB)** rather than patch with swap alone, since swap only helps with occasional spikes, not a baseline requirement that structurally exceeds available RAM.
  - Resize mechanics: stop → change instance type → start. EBS-backed (confirmed via `describe-instances` before proceeding), so no data loss — only the compute spec changes, not the attached storage. ~3 min downtime; Elastic IP unchanged throughout. Verified post-resize: `free -h` showed ~1.9GB total as expected, both existing services auto-started cleanly, `/health` and login both returned 200.
  - **Real bug caught mid-deployment**: installing the `mcp` Python package pulled in a Starlette upgrade (0.38.6 → 1.3.1) that broke FastAPI 0.115.0's pinned requirement (`starlette<0.39.0`) — installed directly into `backendvenv` (the same venv the live backend uses) the first time, discovered before anything restarted, so no actual outage occurred. Fixed by reinstalling the correct pinned versions in `backendvenv`, verified via a real service restart, *then* creating a completely separate `mcpvenv` for the MCP server so this conflict can't recur. This is the same lesson the Flink EC2 already had encoded in its separate `mcpvenv`/`flinkvenv`/`venv` split — re-learned the hard way rather than anticipated.
  - New `finsight-mcp` systemd service (not the old `nohup`+pid pattern) — auto-restarts on crash/reboot, matching `finsight-backend`'s reliability.
  - Deployed bound to the **admin** identity (single shared identity for the whole SSE server — see `AUTH.md` for why per-caller auth wasn't built for this transport). Port 8002 opened publicly on the security group, matching the access pattern the old Flink EC2 deployment had.
  - Verified with a real MCP protocol client (not just an HTTP status check): connected via SSE, listed all 8 tools, called `list_portfolios` and confirmed exactly 50 content blocks returned (i.e., all 50 portfolios, correct for the admin identity).
  - Final memory state with all three services running: 665MB used of 1.9GB, 1.0GB still available.

---

## Resume Steps for Next Session
1. **Retire the stale MCP server on the Flink EC2** — it still has the pre-auth `mcp_server.py` code sitting there (last pulled 2026-07-06). Not currently running (nohup processes don't survive a stop/start cycle, and the box has been stopped/started multiple times since), but worth an explicit check next time that box is up, and either update or remove it so there's no confusion about which MCP endpoint is authoritative. The ChromaDB EC2 (`http://13.206.225.80:8002/sse`) is now the live one.
2. **Redis** (Task 6.2) — install on the ChromaDB EC2 (now t3.small, ~1GB headroom after ChromaDB+backend+MCP). Was already the planned location per `plan.md`'s Option A; capacity was the open question, now resolved by the resize.
3. Confirm `finsight-daily-price-update`'s first real automated fire succeeded (16:00 ET) — check `/var/log/finsight_price_update.log` on the EC2 and/or `Securities.current_price` timestamps.
4. Rest of Phase 6 (Dockerization, real CI/CD for the backend — frontend now auto-deploys, backend still manual) — see `plan.md`.
