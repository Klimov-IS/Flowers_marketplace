#!/bin/bash
set -e

cd /opt/flower-market

echo "=== FLOWER MARKET DEPLOY ==="
echo "Time: $(date)"

# Pull latest code (if git repo exists)
if [ -d ".git" ]; then
    echo "Pulling latest code..."
    git pull origin main
fi

# Backend setup
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Build frontend
echo "Building frontend..."
cd frontend
npm ci --silent
VITE_BASE_PATH=/flower/ VITE_API_BASE_URL=/flower/api npm run build
# Ensure public images are synced to dist
cp -r public/images dist/
cd ..

# Restart services
echo "Restarting services..."
sudo systemctl daemon-reload
sudo systemctl restart flower-api
sudo systemctl enable flower-api
sudo systemctl restart flower-bot
sudo systemctl enable flower-bot

# Reload nginx
sudo nginx -t && sudo systemctl reload nginx

echo "=== DEPLOY COMPLETE ==="
echo "Frontend: https://вцвет.рф/flower/"
echo "API:      https://вцвет.рф/flower/api/"
echo "IP:       http://158.160.229.16/flower/"
echo "Bot:      flower-bot.service ($(sudo systemctl is-active flower-bot))"
