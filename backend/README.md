# Backend - CEO Agent

Backend API for the CEO Agent application, featuring Katy - the AI Product Manager.

## Structure

```
backend/
├── api/                    # FastAPI application
│   ├── main.py            # Main FastAPI app
│   └── routes.py          # Route aggregation
├── routers/               # API route handlers
│   └── chat.py           # Chat endpoints
├── services/              # Business logic
│   └── katy_service.py   # Katy agent service
├── store/                 # Centralized persistence layer and shared DB config
│   ├── auth_store.py     # Auth, sessions, integrations, chat storage
│   ├── employee_store.py # Employee storage
│   ├── workflow_store.py # Workflow storage
│   └── database.py       # Shared DB path + connection helpers
├── product_manager/       # Katy PM Agent
│   ├── katy.py           # Main agent implementation
│   ├── types.py          # Type definitions
│   └── README.md
├── tools/                 # Centralized shared tools for employee, PM, and workflows
│   ├── system_tools/     # Base tool types, registry, file/http/shell/memory
│   ├── integration_tools/# Slack, Gmail, Jira, Notion, Analytics, Research, GitHub
│   ├── run_tools/        # LLM and function execution tools
│   ├── workflow_tools/   # Workflow creation and approval tools
│   └── specialized_tools/# PM, engineering, analyst, designer, ops, sales, recruiter
├── workflows/             # Workflow engine
│   ├── engine/           # Execution engine
│   └── ...
├── models/                # Pydantic models
└── config/                # Configuration
```

## Setup

### Prerequisites

- Python 3.9+
- pip

### Installation

1. **Navigate to project root:**
   ```bash
   cd /Users/hritvik/Downloads/ceo-agent
   ```

2. **Create virtual environment (if not exists):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Running the Backend

### Option 1: Using the startup script

```bash
chmod +x scripts/start-backend.sh
./scripts/start-backend.sh
```

### Option 2: Manual start

```bash
source venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```
Returns server status.

### Chat
```
POST /api/chat/
```
Send a message to Katy and get a response.

**Request:**
```json
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
  "response": "Katy's full response text",
  "success": true
}
```

### Chat (Streaming)
```
POST /api/chat/stream
```
Stream Katy's response using Server-Sent Events (SSE).

## Integration with Frontend

1. **Start the backend:**
   ```bash
   ./scripts/start-backend.sh
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Configure frontend:**
   - The frontend will automatically connect to `http://localhost:8000`
   - To change the backend URL, update `VITE_BACKEND_URL` in `frontend/.env`

## Features

### Katy PM Agent
- **Strategic Planning**: Vision, roadmap, competitive analysis
- **Feature Prioritization**: Backlog management, trade-offs
- **Cross-functional Leadership**: Team coordination
- **Customer Advocacy**: Feedback gathering, user research
- **Data-Driven Decisions**: Metrics, A/B tests
- **Go-to-Market**: Launches, positioning
- **Requirements Definition**: PRDs, user stories

### External Integrations
- **Jira**: Backlog and sprint management
- **Notion**: Documentation and PRDs
- **Analytics**: Product metrics tracking
- **Research**: Market and competitor analysis
- **Slack**: Team communication
- **Gmail**: Stakeholder communication

## Development

### Adding New Endpoints

1. Create a new router in `backend/routers/`
2. Include it in `backend/api/routes.py`
3. Create corresponding service in `backend/services/`

### Adding New Tools

1. Create tool class in `backend/tools/` under the appropriate tool category
2. Inherit from `BaseTool`
3. Implement the `execute` method
4. Register or import it where needed

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all dependencies are installed

### Frontend can't connect to backend
- Check `VITE_BACKEND_URL` in `.env`
- Ensure backend is running on correct port
- Check CORS settings in `backend/api/main.py`

### Import errors
- Make sure you're running from project root
- Check that `backend/` is in Python path
- Verify all imports use `backend.` prefix
