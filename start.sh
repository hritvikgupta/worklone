#!/bin/bash
# Start CEO Agent full stack: Redis, backend API, worker pool, frontend.

set -e
echo "Starting CEO Agent..."

# ─── Python env ───
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
    pip install -q -r requirements.txt
fi

# ─── Redis (docker-compose) ───
if ! nc -z localhost 6379 2>/dev/null; then
    echo "Redis not running on :6379 — bringing up docker-compose..."
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose up -d redis
    elif docker compose version >/dev/null 2>&1; then
        docker compose up -d redis
    else
        echo "ERROR: docker/docker-compose not found. Install Redis yourself on :6379."
        exit 1
    fi
    # Wait briefly for readiness
    for i in 1 2 3 4 5 6 7 8 9 10; do
        nc -z localhost 6379 2>/dev/null && break
        sleep 0.5
    done
fi
echo "Redis ready on :6379"

export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export RUN_WORKER_IN_API="${RUN_WORKER_IN_API:-0}"  # prefer dedicated worker

# ─── Backend API ───
echo "Starting backend API on http://localhost:8000..."
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ─── Worker pool ───
echo "Starting dispatch worker pool..."
python -m backend.worker.main &
WORKER_PID=$!

# ─── Frontend ───
echo "Starting frontend on http://localhost:3000..."
cd frontend
if [ ! -d "node_modules/socket.io-client" ]; then
    echo "Installing new frontend deps (socket.io-client)..."
    npm install --silent
fi
npm run dev &
FRONTEND_PID=$!
cd ..

cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $WORKER_PID $FRONTEND_PID 2>/dev/null || true
    echo "Done."
    exit 0
}
trap cleanup SIGINT SIGTERM

cat <<EOF

=========================================
CEO Agent is running!
Backend:  http://localhost:8000
Frontend: http://localhost:3000
Redis:    localhost:6379
Worker:   PID=$WORKER_PID
=========================================

Press Ctrl+C to stop everything.
EOF

wait
