# FinSight AI — AWS Deployment (Flink + ChromaDB)

Moves ChromaDB and the Flink streaming pipeline (Kafka + Flink) to AWS.
FastAPI backend and SQL Server stay on your local machine.

---

## Architecture

```
Your Laptop (local)
├── FastAPI backend (port 8000)
│   ├── SQL Server  ←  localhost:1433
│   ├── ChromaDB    ←  <CHROMADB_EC2_IP>:8001   (AWS)
│   └── Kafka bridge ← <FLINK_EC2_ELASTIC_IP>:9092  (AWS)
├── Trade producer
│   └── Kafka  ←  <FLINK_EC2_ELASTIC_IP>:9092   (AWS)
└── Next.js dev server  OR  Vercel (frontend, always free)

AWS EC2 t2.micro — ChromaDB  [FREE TIER, always on]
└── ChromaDB Docker  (port 8001)
    └── Data on EBS 8 GB gp2  (within free-tier 30 GB)

AWS EC2 t3.medium — Flink + Kafka  [scheduled, market hours only]
├── Zookeeper Docker
├── Kafka Docker         (port 9092, reachable via Elastic IP)
├── Flink JobManager     (port 8082)
├── Flink TaskManager
└── finnhub_trade_producer.py  (started by cron, runs inside EC2)
    → publishes to Kafka (localhost:9092, internal)
    → Flink reads Kafka, detects volatility
    → writes embeddings to ChromaDB t2.micro
```

---

## Cost Estimate

| Resource | Type | Cost |
|---|---|---|
| ChromaDB EC2 | t2.micro — **FREE TIER** 12 months | $0 |
| ChromaDB EBS | 8 GB gp2 — within **FREE TIER** 30 GB | $0 |
| ChromaDB Elastic IP | Attached to running instance | $0 |
| Flink EC2 | t3.medium, ~165 hrs/month (scheduled) | ~$7.76/mo |
| Flink EBS | 20 GB gp2 — within **FREE TIER** 30 GB | $0 |
| Flink Elastic IP | $0.005/hr × ~565 hrs stopped | ~$2.83/mo |
| **Total** | | **~$10.59/mo** |

$200 in credits covers ~19 months of the Flink instance.

---

## One-Time Setup (do this once)

### Step 1 — Launch ChromaDB EC2

1. AWS Console → EC2 → Launch Instance
   - Name: `finsight-chromadb`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: **t2.micro** (Free tier eligible)
   - Key pair: create or select existing
   - Security Group — inbound rules:
     - Port 22 (SSH) from your IP
     - Port 8001 (ChromaDB) from your IP + Flink EC2 security group
   - Storage: 8 GB gp2

2. Attach an Elastic IP to this instance (EC2 → Elastic IPs → Allocate → Associate)

3. SSH in and run the bootstrap:
   ```bash
   ssh -i your-key.pem ubuntu@<CHROMADB_EC2_IP>
   bash <(curl -fsSL https://raw.githubusercontent.com/<USER>/FinSight-AI/main/aws/ec2-chromadb/bootstrap.sh)
   ```

4. Verify:
   ```bash
   curl http://localhost:8001/api/v2/heartbeat
   # Expected: {"nanosecond heartbeat": <number>}
   ```

5. Note the public IP — this is your `CHROMADB_EC2_IP`.

---

### Step 2 — Launch Flink EC2

1. AWS Console → EC2 → Launch Instance
   - Name: `finsight-flink`
   - AMI: Ubuntu Server 22.04 LTS
   - Instance type: **t3.medium** (2 vCPU, 4 GB RAM)
   - Key pair: same as above
   - Security Group — inbound rules:
     - Port 22 (SSH) from your IP
     - Port 9092 (Kafka) from your IP only
     - Port 8082 (Flink UI) from your IP only
   - Storage: 20 GB gp2

2. Attach an Elastic IP to this instance (this is your `FLINK_EC2_ELASTIC_IP`).

3. SSH in and run the bootstrap:
   ```bash
   ssh -i your-key.pem ubuntu@<FLINK_EC2_ELASTIC_IP>
   # Edit bootstrap.sh first to set your GitHub repo URL, then:
   bash /path/to/aws/ec2-flink/bootstrap.sh
   ```

4. SCP your `.env` file to the instance:
   ```powershell
   # From your local machine (PowerShell)
   scp -i your-key.pem backend/.env ubuntu@<FLINK_EC2_ELASTIC_IP>:/home/ubuntu/FinSight-AI/aws/ec2-flink/.env
   ```

5. Install the cron schedule:
   ```bash
   crontab /home/ubuntu/FinSight-AI/aws/ec2-flink/crontab.txt
   crontab -l   # verify it's installed
   ```

---

### Step 3 — Update local backend/.env

Append these lines (fill in your actual IPs):

```env
CHROMA_HOST=<CHROMADB_EC2_PUBLIC_IP>
CHROMA_PORT=8001
KAFKA_BOOTSTRAP_SERVERS=<FLINK_EC2_ELASTIC_IP>:9092
```

See `aws/env.template` for the full template.

---

### Step 4 — Update .env on the Flink EC2

The `.env` you SCP'd in Step 2 must also have:

```env
CHROMA_HOST=<CHROMADB_EC2_PUBLIC_IP>
CHROMA_PORT=8001
KAFKA_EXTERNAL_IP=<FLINK_EC2_ELASTIC_IP>
CHROMADB_EC2_IP=<CHROMADB_EC2_PUBLIC_IP>
```

These are read by the Flink docker-compose and the volatility detector job.

---

### Step 5 — Test the full pipeline manually

SSH into the Flink EC2 and run:

```bash
bash /home/ubuntu/FinSight-AI/aws/ec2-flink/start_pipeline.sh
```

Wait ~10 minutes, then from your local machine check ChromaDB:

```powershell
$volId = "2149b560-44a8-42b5-97ab-ef8f6b140527"
Invoke-RestMethod "http://<CHROMADB_EC2_IP>:8001/api/v2/tenants/default_tenant/databases/default_database/collections/$volId/count"
# Expected: growing number > 0
```

---

## Daily Operation (automated)

After setup, nothing manual is needed on trading days.

| Time (ET) | What happens |
|---|---|
| 9:25 AM Mon–Fri | Cron fires `start_pipeline.sh` on Flink EC2 |
| 9:25 AM | Docker stack starts (Kafka + Flink) |
| 9:30 AM | Trade producer connects to Finnhub WebSocket, publishes live trades |
| Every 5 min | Flink detects volatility events, writes to ChromaDB on t2.micro |
| 4:15 PM | Cron fires `stop_pipeline.sh`, cancels Flink job, stops trade producer |
| After 4:15 PM | ChromaDB on t2.micro stays on — AI Chat/Insights still work |

---

## What Changed in the Codebase

| File | Change |
|---|---|
| `backend/flink/config.py` | `KAFKA_BOOTSTRAP_SERVERS_EXTERNAL` now reads from `KAFKA_BOOTSTRAP_SERVERS` env var (falls back to `localhost:9092`) |
| `backend/rag/chromadb_setup.py` | `get_chroma_client()` reads `CHROMA_HOST` / `CHROMA_PORT` from env (falls back to localhost) |
| `backend/rag/query_engine.py` | `MarketRAGEngine` reads `CHROMA_HOST` / `CHROMA_PORT` from env |

**No breaking changes** — local setup still works with no `.env` changes because all new
values fall back to `localhost` defaults.

---

## Stopping / Pausing to Save Credits

To stop the Flink EC2 outside of testing (weekends / holidays):
```bash
# AWS CLI (install with: pip install awscli)
aws ec2 stop-instances --instance-ids <FLINK_EC2_INSTANCE_ID>
aws ec2 start-instances --instance-ids <FLINK_EC2_INSTANCE_ID>
```

Or from the AWS Console: EC2 → Instances → select → Instance State → Stop.

The Elastic IP cost while stopped is ~$0.005/hr (~$2.83/month). Stopping for full weekends
saves ~$2.50/month in compute — minor, but worth it for long holidays.

ChromaDB t2.micro should stay on always (AI features need it) — it's free tier anyway.

---

## Security Notes

- Never open port 9092 (Kafka) to `0.0.0.0/0` — restrict to your public IP only.
- Never open port 8001 (ChromaDB) publicly — restrict to your IP + Flink EC2 security group.
- Your `.env` (with API keys) is never committed to git — transfer via SCP only.
- Rotate your Elastic IP association if you recreate instances.
