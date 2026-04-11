#!/bin/bash

# Start both backend and frontend for CEO Agent

echo "Starting CEO Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start backend
echo "Starting backend on http://localhost:8000..."
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on http://localhost:3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# Function to handle cleanup on script exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

echo ""
echo "========================================="
echo "CEO Agent is running!"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "========================================="
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for both processes
wait
