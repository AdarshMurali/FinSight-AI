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
| `risk_job.py` (daily risk computation) | Same Flink EC2, via EventBridge → SSM | `/home/ec2-user/FinSight-AI/backend/scripts/risk_job.py` | Live, redeployed 2026-07-15 | Runs Mon–Fri 16:10 ET. Confirmed byte-identical to GitHub (sha256 checked) as of 2026-07-15's alert dedup/mute deploy — see Session Log. Deploy mechanism is manual tar+scp (only the changed files this round), not git (see "Redeploying to the Flink EC2" below) until CI/CD replaces it. |
| `price_update_job.py` (daily price refresh) | Same Flink EC2, via EventBridge → SSM (`finsight-daily-price-update`) | `/home/ec2-user/FinSight-AI/backend/scripts/price_update_job.py` | Live, deployed 2026-07-08 | Runs Mon–Fri 16:00 ET, 10 min before `risk_job.py`. Verified via manual SSM trigger before relying on the schedule (lesson from `risk_job.py`'s silent failure — see [[eventbridge-risk-job]]). |
| MCP Server | ChromaDB EC2 (SSE transport), moved 2026-07-11 | `http://13.206.225.80:8002/sse` | Live | Moved off the Flink EC2 — see writeup below. Own isolated venv (`mcpvenv`), own systemd service (`finsight-mcp`), bound to the admin identity. |
| Frontend | Vercel | `https://www.fin-sightai.space` (also `https://frontend-sandy-seven-21.vercel.app`) | Live | Deployed from git; custom domain added 2026-07-09 |
| FastAPI backend | Same EC2 as ChromaDB (`13.206.225.80`), reused for $0 extra cost | `https://api.fin-sightai.space` | Live | Deployed 2026-07-09 — see below |
| Redis (caching) | Same EC2 as ChromaDB/backend, self-hosted as **Valkey** (Redis-compatible fork) | `localhost:6379` on `13.206.225.80` | Live, deployed 2026-07-11 | Bind `127.0.0.1` only, no security group change needed. Caches alert counts (60s), risk metrics (30min), portfolio summary/positions (5min). See Task 6.2 writeup below. |

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

## Redeploying backend code to the Flink EC2 (interim — until CI/CD)

`/home/ec2-user/FinSight-AI/` on the Flink EC2 (`13.233.21.229`) is **not a git repo** — it was originally populated by a one-time file copy (2026-06-24) and has been updated by manual tar+scp ever since, unlike the ChromaDB/backend EC2 which uses a real `git sparse-checkout` clone. This gap caused the parametric shocks feature (built 2026-07-12) to sit live on GitHub and in Azure SQL but **not actually run** on this box for 2 days — see Session Log 2026-07-14.

**Deliberately not converting this to a real git clone right now** — a proper CI/CD pipeline (`plan.md` Task 6.3) is the intended fix and will set up correct deploy auth (deploy key) and an automated push step at that time. Until then, use this manual process and update this file whenever it's used:

1. From local repo root, package only the code that changed (never the venvs or `.env`):
   ```
   tar czf backend_deploy.tar.gz backend/ aws/ --exclude='backend/**/__pycache__'
   ```
2. Copy to the box:
   ```
   scp -i C:\Agentic_AI\aws\finsight-key.pem backend_deploy.tar.gz ec2-user@13.233.21.229:/home/ec2-user/
   ```
3. SSH in, back up the current copy before overwriting (don't skip this — it's what made the 2026-07-14 recovery safe), then extract:
   ```
   ssh -i C:\Agentic_AI\aws\finsight-key.pem ec2-user@13.233.21.229
   mv /home/ec2-user/FinSight-AI/backend /home/ec2-user/FinSight-AI/backend.stale.bak.$(date +%Y%m%d)
   tar xzf /home/ec2-user/backend_deploy.tar.gz -C /home/ec2-user/FinSight-AI/
   ```
   This does **not** touch `mcpvenv/`, `flinkvenv/`, or `aws/ec2-flink/.env` — those live alongside `backend/`, not inside it, and the tar only contains `backend/` + `aws/`.
4. Verify the deploy actually landed correctly (the failure mode that bit us on 2026-07-14 wasn't a bad copy, it was *never redeploying at all* — so confirm, don't assume):
   ```
   sha256sum /home/ec2-user/FinSight-AI/backend/services/risk_analytics.py   # on the box
   sha256sum backend/services/risk_analytics.py                              # locally
   ```
   Hashes must match.
5. No service restart needed for `risk_job.py` / `price_update_job.py` — SSM invokes them fresh each run, they're not long-running daemons. If `backend/flink/*.py` changed, the Flink Docker containers **do** need a restart to pick up the bind-mounted files (`docker restart finsight-flink-jobmanager finsight-flink-taskmanager`).
6. Update this file's Session Log with what was deployed and when — this is exactly the step that got skipped on 2026-07-12, which is why the gap went unnoticed for 2 days.

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
- **2026-07-11 (Task 6.2)**: Deployed Redis caching — as **Valkey** (Redis-compatible fork), self-hosted on the ChromaDB EC2 alongside ChromaDB + backend + MCP.
  - `dnf search redis` turned up nothing in AL2023's default repos; `valkey` (v9.0.4) and the older `redis6` (v6.2.20) were both available. Chose Valkey — actively maintained, AWS's current recommendation, fully wire-compatible with the Python `redis` client already in `requirements.txt`.
  - Default config binds `127.0.0.1` only, `protected-mode yes` — no security group change needed, unlike MCP. Backend connects via `localhost:6379` on the same box.
  - Caches: unread alert count (60s), risk metrics (30min — see Task 6.4's note above on why not the originally-planned 24h), portfolio summary/positions (5min). Reusable `get_or_set()`/`invalidate()` wrapper in `backend/services/cache.py`, graceful fallback if Redis is unreachable.
  - Verified for real, not just "endpoint returns 200": confirmed cache keys actually appear in Valkey with correct TTLs (`valkey-cli keys`/`ttl`), confirmed `mark_read` genuinely invalidates the alert-count key (count updated 10→9 immediately, not after the 60s TTL), confirmed full page renders (dashboard, portfolio detail, Risk Analytics tab) still work correctly end-to-end in a real browser against the live site post-deploy.
  - Final memory with all four services (ChromaDB, backend, MCP, Valkey) running: Valkey itself uses ~3MB idle — negligible next to the other three.
- **2026-07-14**: Removed `finsight-chromadb` (`i-0d5332841d8f8da41`) from the `finsight-ec2-scheduler` Lambda's `INSTANCE_IDS` — it was still being auto-stopped nightly (4:25 PM ET) by the same scheduler that manages the market-hours-only Flink EC2, even though it's been hosting always-on production services (ChromaDB, FastAPI backend, MCP server, Valkey) since the 2026-07-09/07-11 consolidation. Caught because the box had actually gone down and needed a manual restart before this was noticed. Fixed in `aws/lambda/ec2_scheduler.py` (now only lists the Flink instance) and deployed via `aws lambda update-function-code`; verified by re-downloading the deployed zip and diffing it against the local source. The Flink EC2 keeps its existing 9:20 AM/4:25 PM ET start/stop schedule unchanged.
- **2026-07-14 (later same day)**: **Correction to this file's own 2026-07-11 entry above** — "Task 5.2's event/AI alerts" were built and committed (`08c92c3`) that day, but were never actually deployed to the Flink EC2, which is the box that runs `risk_job.py` on a schedule. That claim conflated the JWT-auth backend deploy (git pull on the ChromaDB EC2, real) with the alert engine (which needed a separate deploy to a different box, never done). Root cause: the Flink EC2 has no git repo — `/home/ec2-user/FinSight-AI/` there was set up via a one-time file copy, not `git clone`, so `git push` never reaches it. Its code was still dated 2026-07-06/07, five days stale, confirmed via `grep`/`stat` on the box directly (zero references to the new alert functions).
  - Fixed by tarring the current `backend/` locally (excluding `.env` and cruft like the stale nested `backend/backend/` dir and `__pycache__`), scp'ing it to the box, extracting over the old copy, and restoring the box's own `.env` (never overwritten — it has box-specific `CHROMA_HOST`/`KAFKA_BOOTSTRAP_SERVERS` values). Old copy preserved at `backend.stale.bak.20260714` rather than deleted.
  - Confirmed `mcpvenv` already had every package the new code needs (`openai`, `chromadb`, `scipy`, etc.) — no reinstall required.
  - Verified with a real manual `risk_job.py` run (same lesson as the original outage — never trust a schedule without a manual run first): 50/50 portfolios succeeded, 3 real AI alerts generated (~$0.008 total OpenAI spend), 0 event alerts (ran cleanly, just no portfolio crossed the exposure threshold this pass).
  - **Not fixed**: the Flink EC2 still has no git repo, so this exact staleness bug will recur on the next code change to anything `risk_job.py` touches unless someone remembers to manually re-copy files, or the box gets converted to a proper git deploy-key clone like the backend EC2.
  - **Same deploy also covered the parametric shocks feature** (`9e3ce25`, `53e004f`, built 2026-07-12) — it had the identical staleness problem for the identical reason (same undeployed `backend/` folder), just discovered independently: `Risk_Metrics.parametric_data` existed as a column (the additive migration `db_migration_parametric_shocks.sql` was run directly against Azure SQL on 07-12) but every automated row through 2026-07-13 had it empty. Confirmed fixed by this same tar deploy — post-deploy `sha256sum` of `backend/services/risk_analytics.py` and `backend/scripts/risk_job.py` on the box match the local/GitHub copies exactly.
- **2026-07-14 (later still)**: Separately, found and fixed why the Flink EC2's 9:20 AM ET scheduled *start* didn't fire today even though EventBridge triggered right on time (confirmed via CloudTrail AssumeRole + CloudWatch `Invocations=3`/`Errors=3` at 13:20 UTC). Root cause: the `finsight-ec2-scheduler` Lambda's **Handler config** (`lambda_function.lambda_handler`) didn't match the actual file in the deployed zip (`ec2_scheduler.py`) after the same-day `INSTANCE_IDS` fix was pushed via `update-function-code` — that command replaces code but not the Handler setting, so every invocation failed instantly with `Runtime.ImportModuleError` before any logging could occur (which is why the CloudWatch log group didn't even exist, making this look like "never ran" rather than "erroring"). Fixed via `aws lambda update-function-configuration --handler ec2_scheduler.lambda_handler` (matches the zip that's already deployed, no re-zip needed); confirmed `LastUpdateStatus: Successful`. This is unrelated to the git/tar deploy issue above — it's specific to this one Lambda's config, not a general EC2 code-staleness problem. **Lesson for any future Lambda `update-function-code` deploy**: cross-check `aws lambda get-function-configuration --query Handler` against the actual filename inside the zip (`unzip -l`) — a code-content diff alone won't catch a Handler mismatch.
  - **End-to-end readiness confirmed for tonight's real schedule** (neither had fired yet as of this check, 16:32 UTC): EC2 running, SSM agent `Online` (last ping confirmed), `mcpvenv` has all required packages (sqlalchemy, pyodbc, scipy, pandas, yfinance), deployed code hash-matches GitHub, and a manual `risk_job.py` run already succeeded 50/50 today (see entry above). `price_update_job.py` (20:00 UTC) and `risk_job.py` (20:10 UTC) had not yet fired at check time — first real automated confirmation is still pending, see Resume Steps.
  - **Resolved 2026-07-15**: confirmed via `/var/log/finsight_risk.log` / `finsight_price_update.log` — both fired and succeeded automatically that night (`RiskJob RUN ENDED (OK) — 481.9s` at 20:18 UTC, `PriceUpdateJob RUN ENDED (OK) — 107.3s` at 20:01 UTC on 2026-07-14). First clean automated cycle since the code redeploy + Lambda Handler fix.
- **2026-07-15**: Deployed the alert dedup/mute-cooldown/portfolio-name pass (see `status.md`/`plan.md` for the feature writeup) to both EC2s and production.
  - **SSH was blocked on both boxes before starting** — same stale-IP gotcha as 2026-07-11's entry above, this time on the Flink EC2's SG too (`sg-090d519b50c95f1c2`, SSH allow-listed to a since-changed home IP). Rotated it via `revoke`+`authorize` (single-IP allowlist kept tight, unlike the backend EC2 which has accumulated 3 stale entries alongside the current one — worth a cleanup pass sometime, low priority). Added the current IP to the backend EC2's SG additively.
  - Committed `3a850f8` to `adarsh`, pushed. Backend EC2: `git pull` (fast-forward, 03038be → 3a850f8) + `systemctl restart finsight-backend`; verified live via `https://api.fin-sightai.space/api/alerts` (authenticated) returning the new `portfolio_name`/`status`/`occurrence_count` fields.
  - Flink EC2: **did not use the tar-the-whole-tree pattern this time** — scoped the deploy to just the 4 files `risk_job.py` actually imports (`config.py`, `models.py`, `scripts/risk_job.py`, `services/alert_engine.py`), backed up the originals with a timestamped copy first (`backend_files_bak_20260715_111042`), then sha256-verified all 4 against local/GitHub. Narrower than the documented tar+scp process but achieves the same verified-deploy guarantee with a smaller footprint — the full-tree tar remains the documented default for larger changes.
  - **Manual `risk_job.py` run before trusting the 16:10 ET schedule** (same discipline as every prior deploy to this box): ran via `/home/ec2-user/FinSight-AI/mcpvenv/bin/python scripts/risk_job.py` — note the venv lives at `FinSight-AI/mcpvenv/`, *not* `FinSight-AI/backend/mcpvenv/`, tripped over this once before finding the right path. Confirmed the new upsert logic firing correctly against production data live (e.g. `[RiskJob] Portfolio 20 done — 0 new, 2 bumped, 0 resolved threshold alert(s)` — bumping existing rows, not inserting fresh duplicates).
  - **Found while deploying, unrelated to this feature**: restarting `finsight-mcp.service` on the backend EC2 (needed since it shares `models.py` with the FastAPI backend) revealed it's been crash-looping on stale `FINSIGHT_MCP_TOKEN` (`401: Invalid session` — a signature mismatch, not the 365-day expiry) since some point before today, silently masked because the old process never needed to re-authenticate until restarted. Re-minting a fresh admin token was correctly blocked pending explicit user sign-off (privileged credential creation, outside the literal "deploy and test" scope) — service is currently down; `finsight-backend` and the frontend are unaffected. Tracked as a follow-up, not fixed in this session.
  - Also added a defensive server-side `DEFAULT GETUTCDATE()` on `Alerts.last_triggered_at` (folded into `db_migration_alerts_v3.sql`) — the column was NOT NULL with no DB default, which would have broken any *old*, not-yet-redeployed code's inserts the moment it tried to write a new alert row. Applied before either EC2 deploy, as insurance against exactly the kind of deploy-ordering gap this file exists to prevent.

---

## Resume Steps for Next Session
1. **Restore `finsight-mcp.service`** — down since 2026-07-15, stale `FINSIGHT_MCP_TOKEN` failing signature validation (`401: Invalid session`). Needs `python scripts/mint_mcp_token.py admin@finsight.demo` run on the backend EC2 and the result pasted into `.env.mcp`, then `sudo systemctl restart finsight-mcp` — held pending explicit user go-ahead since minting a privileged long-lived token wasn't in scope of the deploy that surfaced this. `finsight-backend` and the frontend are unaffected in the meantime.
2. **Retire the stale MCP server on the Flink EC2** — it still has the pre-auth `mcp_server.py` code sitting there (last pulled 2026-07-06). Not currently running (nohup processes don't survive a stop/start cycle, and the box has been stopped/started multiple times since), but worth an explicit check next time that box is up, and either update or remove it so there's no confusion about which MCP endpoint is authoritative. The ChromaDB EC2 (`http://13.206.225.80:8002/sse`) is now the live one.
3. **Flink EC2 git conversion — deliberately deferred, not abandoned.** Reconfirmed 2026-07-15 (second time this decision has come up): don't ad-hoc convert `/home/ec2-user/FinSight-AI/` to a git deploy-key clone right now. The real fix is Task 6.3 (CI/CD pipeline) doing this properly as part of setting up automated deploys for both EC2s. Until then, use the documented manual process ("Redeploying backend code to the Flink EC2" section above — either the full tar+scp, or a scoped just-the-changed-files copy like 2026-07-15 used) for any code change touching `risk_job.py`, `alert_engine.py`, `risk_analytics.py`, or anything else they import — and update this file's Session Log every time.
4. **Backend EC2 SSH security group has 3 stale IPs accumulated** (`sg-0e48754e3d50f37dd`) alongside the current one — low priority, but worth pruning next time that box is touched rather than continuing to add entries.
5. Rest of Phase 6 (Dockerization, real CI/CD for the backend — frontend now auto-deploys, backend still manual) — see `plan.md`. When Task 6.3 is built, fold both EC2s' deploys into it and retire the manual process in item 3.
