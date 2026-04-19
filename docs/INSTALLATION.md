# Installation Guide

This guide covers every way to get Worklone running — from local development to production deployment.

> License notice: Worklone is released for non-commercial research/evaluation use only. See [../LICENSE](../LICENSE).

---

## Prerequisites

| Requirement | Version | Why |
|-------------|---------|-----|
| Python | 3.9+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Git | Any | Clone the repository |
| OpenRouter API Key | — | LLM access (required) |
| NVIDIA API Key | — | Alternative LLM provider (optional) |

---

## Option 1: Quick Start (Recommended for Development)

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/worklone.git
cd worklone
cp .env.example .env
```

Edit `.env` and add your API key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 2. Launch (Docker-assisted local setup)

```bash
# Optional infra
docker compose up -d redis

# Backend (terminal 1)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

### 3. Verify

- **Backend**: `http://localhost:8000/health` → `{"status": "ok"}`
- **Frontend**: `http://localhost:5173` → Worklone dashboard
- **API Docs**: `http://localhost:8000/docs` → Interactive Swagger UI

---

## Option 2: Manual Setup

### Backend

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start the server
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## Option 3: Production Deployment

### Backend (Production)

```bash
# Disable reload, bind to specific host
uvicorn backend.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

For production, use a process manager:

**With Gunicorn:**
```bash
gunicorn backend.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

**With systemd:**
```ini
[Unit]
Description=Worklone Backend
After=network.target

[Service]
User=worklone
WorkingDirectory=/opt/worklone
Environment=PATH=/opt/worklone/venv/bin
ExecStart=/opt/worklone/venv/bin/uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Frontend (Production)

```bash
cd frontend
npm install
npm run build
```

Serve the `frontend/dist` directory with nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /opt/worklone/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | LLM access via OpenRouter | `sk-or-v1-...` |

### Optional

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NVIDIA_API_KEY` | NVIDIA NIM LLM access | — | `nvapi-...` |
| `SLACK_BOT_TOKEN` | Slack integration | — | `xoxb-...` |
| `GMAIL_ACCESS_TOKEN` | Gmail integration | — | `ya29....` |
| `WORKFLOW_DB` | SQLite database path | `workflows.db` | `/data/worklone.db` |
| `PORT` | Backend server port | `8002` | `8000` |
| `HOST` | Backend server host | `0.0.0.0` | `127.0.0.1` |
| `WORKER_POLL_INTERVAL` | Workflow poll interval (seconds) | `5` | `10` |
| `WORKER_MAX_CONCURRENT` | Max concurrent workflow executions | `10` | `20` |
| `FRONTEND_URL` | CORS origin | — | `http://localhost:5173` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | — | `https://your-domain.com` |
| `CORS_ALLOWED_ORIGIN_REGEX` | Regex for dynamic tunnel hosts | — | `.*\.ngrok-free\.app` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_BACKEND_URL` | Backend API URL | `http://localhost:8000` |

---

## Getting API Keys

### OpenRouter

1. Visit [openrouter.ai](https://openrouter.ai/)
2. Sign up for an account
3. Go to **Keys** in the dashboard
4. Create a new API key
5. Copy it to your `.env` file

OpenRouter gives you access to multiple LLM providers (OpenAI, Anthropic, Google, etc.) through a single API.

### NVIDIA NIM (Optional)

1. Visit [build.nvidia.com](https://build.nvidia.com/)
2. Sign up for an account
3. Generate an API key
4. Add `NVIDIA_API_KEY` to your `.env`

---

## Verification

After setup, verify everything works:

### 1. Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

### 2. API Documentation

Open `http://localhost:8000/docs` in your browser. You should see the interactive Swagger UI with all endpoints.

### 3. Frontend

Open `http://localhost:5173` and register a new account. You should see the Worklone dashboard.

### 4. Test Chat

Try chatting with a self-learning employee to verify LLM connectivity:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Introduce your role and capabilities"}'
```

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Must be 3.9+

# Check dependencies
pip install -r requirements.txt

# Check .env file
cat .env  # Ensure OPENROUTER_API_KEY is set
```

### Frontend build fails

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Must be 18+
```

### LLM errors

- Verify your API key is correct
- Check your OpenRouter account has credits
- Try a different model by setting it in the employee configuration

### CORS errors

- Ensure `FRONTEND_URL` or `CORS_ALLOWED_ORIGINS` includes your frontend URL
- For ngrok/tunneling, use `CORS_ALLOWED_ORIGIN_REGEX`

---

## Running with Docker (Coming Soon)

Docker deployment is on our roadmap. Stay tuned for one-click container deployment.
