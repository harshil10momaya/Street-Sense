#!/usr/bin/env bash
# StreetSense — Development Startup Script
# Usage: ./scripts/start_dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  StreetSense — Development Environment"
echo "============================================"

# ─── 1. Check Docker ───
echo ""
echo "[1/5] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker Desktop first."
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi
echo "✅ Docker found"

# ─── 2. Start PostgreSQL ───
echo ""
echo "[2/5] Starting PostgreSQL..."
cd "$ROOT_DIR/docker"
docker compose up -d postgres
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 3

# Check if postgres is healthy
for i in $(seq 1 10); do
    if docker compose exec -T postgres pg_isready -U streetsense -d streetsense_db &>/dev/null; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "❌ PostgreSQL failed to start. Check: docker compose logs postgres"
        exit 1
    fi
    sleep 2
done

# ─── 3. Setup Python venv ───
echo ""
echo "[3/5] Setting up Python environment..."
cd "$ROOT_DIR/backend"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created virtual environment"
fi

source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✅ Dependencies installed"

# ─── 4. Copy .env if needed ───
echo ""
echo "[4/5] Checking environment config..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
fi
echo "✅ Environment configured"

# ─── 5. Start FastAPI ───
echo ""
echo "[5/5] Starting FastAPI server..."
echo ""
echo "============================================"
echo "  🚀 StreetSense is starting!"
echo ""
echo "  API:      http://localhost:8000"
echo "  Docs:     http://localhost:8000/docs"
echo "  ReDoc:    http://localhost:8000/redoc"
echo "  Health:   http://localhost:8000/api/v1/health"
echo "  pgAdmin:  http://localhost:5050"
echo "============================================"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
