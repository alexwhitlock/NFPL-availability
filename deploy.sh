#!/bin/bash
# deploy.sh — pull latest from GitHub and deploy to t3600
# Run this on the t3600: ./deploy.sh
set -euo pipefail

REPO="$HOME/NFPL-availability"
WEB="/srv/www/nfpl"

echo "==> Pulling from GitHub..."
cd "$REPO"
git pull

echo "==> Deploying web files..."
cp web/index.html  "$WEB/"
cp web/sites.json  "$WEB/"

echo "==> Rebuilding Docker image..."
docker compose -f "$REPO/docker-compose.yml" build

echo "==> Restarting proxy container..."
docker compose -f "$REPO/docker-compose.yml" up -d

echo "==> Done. $(date)"
echo "==> Health check..."
sleep 2
curl -sf http://127.0.0.1:5004/health && echo " healthy" || echo " health check failed"
