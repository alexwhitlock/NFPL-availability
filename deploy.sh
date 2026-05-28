#!/bin/bash
# deploy.sh — pull latest from GitHub and deploy to t3600
# Run this on the t3600: ./deploy.sh
set -e

REPO="$HOME/NFPL-availability"
WEB="/srv/www/nfpl"
SCRIPTS="$HOME/scripts"

echo "==> Pulling from GitHub..."
cd "$REPO"
git pull

echo "==> Deploying web files..."
cp web/index.html  "$WEB/"
cp web/sites.json  "$WEB/"

echo "==> Deploying scripts..."
cp web/nfpl_proxy.py "$SCRIPTS/"
cp check_nfpl.py     "$SCRIPTS/"

echo "==> Done. $(date)"
echo ""
echo "If nfpl_proxy.py changed, restart the proxy:"
echo "  sudo systemctl restart nfpl-proxy"
