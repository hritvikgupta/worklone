#!/bin/bash
# Start the backend server

cd "$(dirname "$0")/.."

echo "Starting Katy Backend Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start the server
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
