#!/usr/bin/env bash
# ==============================================================================
# AWS EC2 Automated Deployment Script for Agentic Financial Operations Assistant
# ==============================================================================

set -euo pipefail

echo ">>> [1/6] Updating Ubuntu System Packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

echo ">>> [2/6] Installing Docker & Docker Compose..."
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-compose

sudo usermod -aG docker "$USER"

echo ">>> [3/6] Setting Up Project Directory..."
APP_DIR="/opt/finops-assistant"
sudo mkdir -p "$APP_DIR"
sudo chown -R "$USER:$USER" "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
    git clone https://github.com/harsharaju1314-hash/Agentic-AI-Financial-Operations-Assistant.git "$APP_DIR"
else
    cd "$APP_DIR" && git pull origin main
fi

cd "$APP_DIR"

echo ">>> [4/6] Configuring Environment Variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Please review and populate production secrets."
fi

echo ">>> [5/6] Building and Launching Docker Containers..."
docker-compose -f docker-compose.yml up -d --build

echo ">>> [6/6] Verifying Services Health..."
sleep 15
docker-compose ps

echo "======================================================================"
echo "Deployment Complete!"
echo "FastAPI Backend:    http://$(curl -s ifconfig.me):8000/docs"
echo "Streamlit UI:       http://$(curl -s ifconfig.me):8501"
echo "======================================================================"
