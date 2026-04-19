# Backend - Worklone API

Backend API for Gemenic Workplace self-learning employees.

> License notice: non-commercial research and evaluation only. See [../LICENSE](../LICENSE).

## Structure

```
backend/
├── api/                    # FastAPI application
├── services/               # Business logic
├── core/                   # Agents, tools, workflows
├── db/                     # Shared SQLite stores
├── lib/                    # Auth/OAuth helpers
└── ...
```

## Setup

```bash
cd /Users/hritvik/Downloads/ceo-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
source venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Server: `http://localhost:8000`

## API

- Health: `GET /health`
- Chat: `POST /api/chat/`
- Streaming chat: `POST /api/chat/stream`

## Frontend Integration

```bash
cd frontend
npm install
npm run dev
```

## Notes

- This backend supports adaptive, self-learning employee execution loops.
- Integration endpoints and workflow orchestration are exposed through FastAPI routers.
- Storage defaults to shared SQLite for local/self-hosted operation.

## Troubleshooting

- Ensure `venv` is activated.
- Ensure port `8000` is free.
- Ensure `.env` keys are set.
- Ensure frontend `VITE_BACKEND_URL` points to `http://localhost:8000`.
