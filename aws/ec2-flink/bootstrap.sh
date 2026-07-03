#!/bin/bash
# ============================================================
# Flink + Kafka EC2 Bootstrap — run once after instance launch
# Instance type : t3.medium (2 vCPU, 4 GB RAM)
# EBS volume    : 20 GB gp2, mounted at /data
# Schedule      : Start/stop via EventBridge (market hours only)
# ============================================================
set -e

echo "=== [1/6] System update ==="
sudo apt-get update -y && sudo apt-get upgrade -y

echo "=== [2/6] Install Docker + Python ==="
sudo apt-get install -y ca-certificates curl gnupg python3 python3-pip python3-venv git
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

echo "=== [3/6] Mount EBS volume at /data ==="
EBS_DEVICE="/dev/xvdf"
if [ -b /dev/nvme1n1 ]; then EBS_DEVICE="/dev/nvme1n1"; fi
if ! blkid "$EBS_DEVICE"; then
  sudo mkfs -t ext4 "$EBS_DEVICE"
fi
sudo mkdir -p /data
sudo mount "$EBS_DEVICE" /data
echo "$EBS_DEVICE /data ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab
sudo chown -R ubuntu:ubuntu /data

echo "=== [4/6] Clone repo and install Python deps ==="
cd /home/ubuntu
git clone https://github.com/<YOUR_GITHUB_USERNAME>/FinSight-AI.git
# ↑ Replace with your actual repo URL

cd /home/ubuntu/FinSight-AI
python3 -m venv flinkvenv
source flinkvenv/bin/activate
pip install --upgrade pip
pip install kafka-python websocket-client python-dotenv

echo "=== [5/6] Copy .env (contains API keys) ==="
# You must copy your backend/.env to this path manually via SCP:
# scp -i your-key.pem backend/.env ubuntu@<EC2-IP>:/home/ubuntu/FinSight-AI/aws/ec2-flink/.env
# The .env must contain: OPENAI_API_KEY, FINNHUB_API_KEY, KAFKA_EXTERNAL_IP, CHROMADB_EC2_IP
echo "Remember to SCP your .env file to /home/ubuntu/FinSight-AI/aws/ec2-flink/.env"

echo "=== [6/6] Build Flink Docker image ==="
cd /home/ubuntu/FinSight-AI
docker build -t finsight-flink:1.18 ./backend/flink/

echo ""
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. SCP your .env to /home/ubuntu/FinSight-AI/aws/ec2-flink/.env"
echo "  2. Set up the cron schedule: crontab /home/ubuntu/FinSight-AI/aws/ec2-flink/crontab.txt"
echo "  3. Test manually: bash /home/ubuntu/FinSight-AI/aws/ec2-flink/start_pipeline.sh"
