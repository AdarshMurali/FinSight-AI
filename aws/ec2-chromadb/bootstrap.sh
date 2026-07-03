#!/bin/bash
# ============================================================
# ChromaDB EC2 Bootstrap — run once after instance launch
# Instance type : t2.micro (FREE TIER — 1 vCPU, 1 GB RAM)
# EBS volume    : 8 GB gp2, mounted at /data
# ============================================================
set -e

echo "=== [1/5] System update ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== [2/5] Install Docker ==="
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu
newgrp docker

echo "=== [3/5] Mount EBS volume at /data ==="
# The EBS volume is attached as /dev/xvdf (or /dev/nvme1n1 on Nitro instances).
# Check with: lsblk
EBS_DEVICE="/dev/xvdf"
if [ -b /dev/nvme1n1 ]; then EBS_DEVICE="/dev/nvme1n1"; fi

# Format only if not already formatted
if ! blkid "$EBS_DEVICE"; then
  sudo mkfs -t ext4 "$EBS_DEVICE"
fi
sudo mkdir -p /data/chroma
sudo mount "$EBS_DEVICE" /data
# Persist mount across reboots
echo "$EBS_DEVICE /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
sudo mkdir -p /data/chroma
sudo chown -R ubuntu:ubuntu /data

echo "=== [4/5] Copy docker-compose for ChromaDB ==="
mkdir -p /home/ubuntu/chromadb
# Copy the file from the repo or paste inline — adjust path if you git clone first
cat > /home/ubuntu/chromadb/docker-compose.yml << 'COMPOSE'
services:
  chromadb:
    image: ghcr.io/chroma-core/chroma:latest
    container_name: FinSight_AI_chromadb
    ports:
      - "8001:8000"
    environment:
      - IS_PERSISTENT=TRUE
      - PERSIST_DIRECTORY=/data
      - ANONYMIZED_TELEMETRY=FALSE
    volumes:
      - /data/chroma:/data
    restart: unless-stopped
COMPOSE

echo "=== [5/5] Start ChromaDB ==="
cd /home/ubuntu/chromadb
docker compose up -d

echo ""
echo "Done. ChromaDB is running on port 8001."
echo "Verify: curl http://localhost:8001/api/v2/heartbeat"
echo ""
echo "NEXT STEP: Copy the public IP of this instance into aws/env.template as CHROMA_HOST."
