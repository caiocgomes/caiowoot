#!/bin/bash
set -e

cd /opt/caiowoot

echo "==> Pulling latest code..."
sudo git pull

echo "==> Syncing dependencies..."
sudo -u caiowoot uv sync --frozen --no-dev

echo "==> Fixing permissions..."
sudo chown -R caiowoot:caiowoot /opt/caiowoot

echo "==> Restarting service..."
sudo systemctl restart caiowoot

echo "==> Done. Checking status..."
sleep 2
sudo systemctl status caiowoot --no-pager -l | head -15
