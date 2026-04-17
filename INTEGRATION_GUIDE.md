# Frontend-Backend Integration Guide

## Overview

The CEO Agent application now has a proper separation of concerns:
- **Frontend**: React + TypeScript + Vite (runs on port 3000)
- **Backend**: FastAPI + Katy PM Agent (runs on port 8000)

## Architecture

```
ceo-agent/
├── backend/                    # Python FastAPI Backend
│   ├── api/                   # FastAPI application
│   │   ├── main.py           # Main app with CORS
│   │   └── routes.py         # Route aggregation
│   ├── routers/              # API endpoints
│   │   └── chat.py          # /api/chat/ endpoint
│   ├── services/             # Business logic
│   │   └── katy_service.py  # Katy agent wrapper
│   ├── product_manager/      # Katy PM Agent
│   │   ├── katy.py          # Main agent
│   │   ├── pm_tools.py      # PM tools
│   │   └── tools/           # External integrations
│   ├── workflows/            # Workflow engine
│   └── README.md             # Backend documentation
│
├── frontend/                  # React TypeScript Frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── AIAssistant.tsx  # Katy chat (sidebar)
│   │   │   └── ChatView.tsx     # Full chat view
│   │   └── lib/              # Utilities
│   └── lib/
│       └── api.ts            # Backend API client
│
└── scripts/
    └── start-backend.sh      # Backend startup script
```

## Quick Start

### 1. Start the Backend

```bash
# Option A: Using the startup script
chmod +x scripts/start-backend.sh
./scripts/start-backend.sh

# Option B: Manual start
cd /Users/hritvik/Downloads/ceo-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will be available at: `http://localhost:8000`

**Test it:**
```bash
curl http://localhost:8000/health
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at: `http://localhost:3000`

### 3. Test the Integration

1. Open `http://localhost:3000` in your browser
2. Click on the "Chat" tab or open the AI Assistant panel
3. Type a message like "Hello Katy, introduce yourself"
4. Katy should respond through the backend API

## API Endpoints

### Health Check
```
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Chat (Non-streaming)
```
POST /api/chat/
Content-Type: application/json

{
  "message": "Help me prioritize my backlog",
  "user_id": "anonymous",
  "conversation_history": [
    {"role": "user", "content": "Previous message"},
    {"role": "assistant", "content": "Previous response"}
  ]
}
```

**Response:**
```json
{
  "response": "Katy's full response text here...",
  "success": true,
  "error": null
}
```

### Chat (Streaming - SSE)
```
POST /api/chat/stream
Content-Type: application/json

{
  "message": "Hello Katy",
  "user_id": "anonymous"
}
```

**Response:** Server-Sent Events stream
```
data: chunk1
data: chunk2
data: [DONE]
```

## Configuration

### Backend Configuration

Edit `.env` in the root directory:
```bash
# Add any backend-specific env vars here
```

### Frontend Configuration

Edit `frontend/.env`:
```env
# Backend API URL
VITE_BACKEND_URL="http://localhost:8000"
```

To change the backend URL:
1. Update `VITE_BACKEND_URL` in `frontend/.env`
2. Restart the frontend dev server

## How the Integration Works

### Frontend → Backend Flow

1. **User types a message** in `AIAssistant.tsx` or `ChatView.tsx`
2. **Component calls** `sendChatMessage()` from `lib/api.ts`
3. **API client sends** POST request to `http://localhost:8000/api/chat/`
4. **FastAPI receives** the request in `backend/routers/chat.py`
5. **Router calls** `KatyService.chat()` in `backend/services/katy_service.py`
6. **Service invokes** `KatyPMAgent.chat()` in `backend/product_manager/katy.py`
7. **Katy processes** the message using ReAct pattern (Thought → Action → Observation)
8. **Response flows back** through the layers
9. **Frontend displays** Katy's response

### Key Files

#### Frontend
- **`lib/api.ts`**: API client with `sendChatMessage()` function
- **`components/AIAssistant.tsx`**: Sidebar chat component
- **`components/ChatView.tsx`**: Full-page chat view

#### Backend
- **`backend/api/main.py`**: FastAPI app with CORS middleware
- **`backend/routers/chat.py`**: POST `/api/chat/` endpoint
- **`backend/services/katy_service.py`**: Wraps Katy agent for API use
- **`backend/product_manager/katy.py`**: The actual Katy PM agent

## Development Workflow

### Making Changes to Katy

1. Edit files in `backend/product_manager/`
2. The backend auto-reloads (thanks to `--reload` flag)
3. Test changes through the frontend chat interface

### Adding New API Endpoints

1. Create a new router in `backend/api/routers/`
2. Include it in `backend/api/routes.py`:
   ```python
   from backend.api.routers.new_feature import router as new_feature_router
   router.include_router(new_feature_router, prefix="/new-feature")
   ```
3. Create corresponding API client function in `frontend/lib/api.ts`
4. Use it in your frontend components

### Debugging

**Backend logs:**
```bash
# Backend runs in terminal, logs appear there
# Or check the log file if running in background
tail -f /tmp/katy-backend.log
```

**Frontend logs:**
```javascript
// Open browser DevTools (F12) → Console
// API errors are logged there
```

**Test API directly:**
```bash
# Test health
curl http://localhost:8000/health

# Test chat
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## Troubleshooting

### Frontend can't connect to backend

**Symptoms:**
- Error: "Sorry, I encountered an error processing your request"
- Console shows: `Failed to fetch` or `ECONNREFUSED`

**Solutions:**
1. Check if backend is running: `curl http://localhost:8000/health`
2. Verify `VITE_BACKEND_URL` in `frontend/.env`
3. Check CORS settings in `backend/api/main.py`

### Backend import errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'backend'`

**Solutions:**
1. Make sure you're running from project root (`/Users/hritvik/Downloads/ceo-agent`)
2. All imports should use `backend.` prefix (e.g., `from backend.core.workflows...`)

### TypeScript errors

**Symptoms:**
- `TS2307: Cannot find module '@/lib/api'`

**Solutions:**
1. Run `npm run lint` to see all errors
2. Check that `api.ts` is in `frontend/lib/` (not `frontend/src/lib/`)
3. Verify `tsconfig.json` has correct path aliases

### Port already in use

**Symptoms:**
- `ERROR: [Errno 48] Address already in use`

**Solutions:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn backend.api.main:app --host 0.0.0.0 --port 8001
```

## Features Available Through API

### Katy PM Capabilities

Katy can help with:

1. **Strategic Planning**
   - Product vision and roadmap
   - Competitive analysis
   - Market research

2. **Feature Prioritization**
   - Backlog management
   - RICE/MoSCoW prioritization
   - Trade-off decisions

3. **Requirements Definition**
   - PRD generation
   - User stories
   - Acceptance criteria

4. **Customer Advocacy**
   - User research planning
   - Feedback analysis
   - User interviews

5. **Data-Driven Decisions**
   - Metrics definition
   - A/B test analysis
   - KPI tracking

6. **Go-to-Market**
   - Launch planning
   - Positioning
   - Pricing strategy

### Example Prompts

Try these in the chat:

- "Help me prioritize my backlog"
- "Draft a PRD for a dark mode feature"
- "Analyze competitors in the project management space"
- "Define metrics for our MVP"
- "Create a user research plan for feature X"
- "What should be our Q3 roadmap?"

## Next Steps

### To Enhance the Integration

1. **Add Streaming Support**
   - Update `AIAssistant.tsx` to use SSE streaming
   - Provides more responsive UX

2. **Add Authentication**
   - Implement user auth in backend
   - Pass user tokens from frontend

3. **Add More Endpoints**
   - `/api/roadmap` - Roadmap management
   - `/api/backlog` - Backlog CRUD operations
   - `/api/analytics` - Product metrics

4. **Add WebSocket Support**
   - Real-time bidirectional communication
   - Better for interactive sessions

5. **Add File Upload**
   - Upload documents for analysis
   - Attach files to PRDs

## Support

For issues or questions:
1. Check `backend/README.md` for backend details
2. Check `frontend/README.md` for frontend details
3. Review this integration guide
4. Check the code comments for implementation details

---

**Last Updated:** April 9, 2026
**Version:** 1.0.0
