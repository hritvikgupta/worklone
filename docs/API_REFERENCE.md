# API Reference

Worklone provides a comprehensive REST API and WebSocket interface for interacting with the platform.

---

## Base URL

```
http://localhost:8000
```

---

## Authentication

Most requests require authentication (except health + register/login).

### Methods

| Method | Header | Example |
|--------|--------|---------|
| API Key | `x-api-key` | `x-api-key: sk-worklone-...` |
| Bearer Token | `Authorization` | `Authorization: Bearer token` |

---

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |

```bash
curl http://localhost:8000/health
# {"status": "healthy", "version": "1.0.0"}
```

---

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and create session |
| `GET` | `/api/auth/me` | Get current user info |
| `POST` | `/api/auth/logout` | Logout current session |

---

### Chat

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/chat` | Send message (non-streaming) |
| `POST` | `/api/chat/stream` | Send message (SSE streaming) |
| `GET` | `/api/chat/sessions` | List chat sessions |
| `POST` | `/api/chat/sessions` | Create chat session |
| `GET` | `/api/chat/sessions/{id}/messages` | Get session messages |

#### Chat (Non-Streaming)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "x-user-id: your-user-id" \
  -d '{"message": "Create a PRD for a new feature"}'
```

#### Chat (Streaming)

```javascript
const eventSource = new EventSource(
  '/api/chat/stream?message=Create+a+PRD'
);

eventSource.onmessage = (event) => {
  console.log(event.data);
};
```

---

### Employees

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/employees` | List employees |
| `POST` | `/api/employees` | Create employee |
| `GET` | `/api/employees/{id}` | Get employee details |
| `PATCH` | `/api/employees/{id}` | Update employee |
| `DELETE` | `/api/employees/{id}` | Delete employee |
| `PATCH` | `/api/employees/{id}/tools` | Update employee tools |
| `POST` | `/api/employees/{id}/skills` | Assign skill |
| `DELETE` | `/api/employees/{id}/skills/{skill_id}` | Remove skill |
| `POST` | `/api/employees/{id}/chat` | Chat with employee |
| `POST` | `/api/employees/{id}/chat/stream` | Chat with employee (SSE) |
| `GET` | `/api/employees/{id}/activity` | Get activity logs |
| `GET` | `/api/employees/{id}/tasks` | List employee tasks |
| `POST` | `/api/employees/{id}/tasks` | Create task |
| `PATCH` | `/api/employees/{id}/tasks/{task_id}` | Update task |
| `GET` | `/api/employees/{id}/memory` | Get employee memory |

#### Create Employee

```bash
curl -X POST http://localhost:8000/api/employees \
  -H "Content-Type: application/json" \
  -H "x-user-id: your-user-id" \
  -d '{
    "name": "Alex",
    "role": "Sales Rep",
    "description": "AI sales representative",
    "system_prompt": "You are Alex...",
    "model": "openai/gpt-4o",
    "tools": ["salesforce_create_lead", "gmail_send_email"]
  }'
```

---

### Workflows

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/workflows` | List workflows |
| `POST` | `/api/workflows` | Create workflow |
| `GET` | `/api/workflows/{id}` | Get workflow details |
| `PATCH` | `/api/workflows/{id}` | Update workflow |
| `DELETE` | `/api/workflows/{id}` | Delete workflow |
| `POST` | `/api/workflows/{id}/blocks` | Add block |
| `PATCH` | `/api/workflows/blocks/{block_id}` | Update block |
| `DELETE` | `/api/workflows/blocks/{block_id}` | Delete block |
| `POST` | `/api/workflows/{id}/connections` | Connect blocks |
| `DELETE` | `/api/workflows/{id}/connections/{conn_id}` | Remove connection |
| `POST` | `/api/workflows/{id}/execute` | Execute workflow |
| `GET` | `/api/workflows/{id}/executions` | List executions |
| `GET` | `/api/workflows/{id}/executions/{exec_id}` | Get execution details |
| `POST` | `/api/workflows/{id}/executions/{exec_id}/approve` | Approve human-in-loop |
| `POST` | `/api/workflows/{id}/executions/{exec_id}/pause` | Pause execution |
| `POST` | `/api/workflows/{id}/executions/{exec_id}/resume` | Resume execution |
| `POST` | `/api/workflows/{id}/executions/{exec_id}/cancel` | Cancel execution |

---

### Teams

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/teams` | List teams |
| `POST` | `/api/teams` | Create team |
| `GET` | `/api/teams/{id}` | Get team details |
| `PATCH` | `/api/teams/{id}` | Update team |
| `DELETE` | `/api/teams/{id}` | Delete team |
| `POST` | `/api/teams/{id}/runs` | Create team run |
| `GET` | `/api/teams/{id}/runs` | List team runs |

---

### Sprints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/sprints` | List sprints |
| `POST` | `/api/sprints` | Create sprint |
| `GET` | `/api/sprints/{id}` | Get sprint details |
| `PATCH` | `/api/sprints/{id}` | Update sprint |
| `DELETE` | `/api/sprints/{id}` | Delete sprint |
| `POST` | `/api/sprints/{id}/runs` | Create sprint run |
| `GET` | `/api/sprints/{id}/runs` | List sprint runs |

---

### Dashboard

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/dashboard/overview` | Get dashboard overview |
| `GET` | `/api/dashboard/usage` | Get usage statistics |

---

### Files

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/files/upload` | Upload file |
| `GET` | `/api/files/tree` | Get file tree |
| `GET` | `/api/files/raw` | Read file bytes/content by `scope` + `path` |
| `GET` | `/api/files/content` | Read text content by `scope` + `path` |
| `PUT` | `/api/files/content` | Create/update text content by `scope` + `path` |

---

### Skills

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/skills` | List public skills |
| `POST` | `/api/skills` | Create skill |
| `GET` | `/api/skills/{id}` | Get skill details |
| `POST` | `/api/skills/generate` | Generate skill from description |

---

### Integrations

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/integrations/` | List integrations and connection status |
| `GET` | `/api/integrations/authorize` | Generate OAuth authorization URL |
| `GET` | `/api/integrations/callback/{provider}` | OAuth callback handler |
| `POST` | `/api/integrations/{provider}/disconnect` | Disconnect integration |
| `PUT` | `/api/integrations/credentials` | Save self-hosted OAuth client credentials |
| `GET` | `/api/integrations/credentials/{provider}` | Get client credential status |

---

## Realtime Interface

The backend mounts Socket.IO under:

- `http://localhost:8000/socket.io`

SSE is still used for streaming chat endpoints.

---

## Source of Truth

Use the generated OpenAPI docs for exact request/response schemas:

- `http://localhost:8000/docs`
- `http://localhost:8000/openapi.json`

---

## SSE (Server-Sent Events)

Streaming endpoints use SSE for real-time token output.

### Chat Streaming

```javascript
const eventSource = new EventSource('/api/chat/stream?message=Hello');

eventSource.onmessage = (event) => {
  // Streaming tokens
  console.log(event.data);
};

eventSource.onerror = (error) => {
  // Stream ended or error occurred
};
```

---

## Error Handling

Standard HTTP status codes:

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `409` | Conflict |
| `500` | Internal Server Error |

Error response format:

```json
{
  "detail": "Error message description"
}
```

---

## Rate Limiting

Rate limiting is not enforced by default. For production deployments, configure rate limiting at the reverse proxy level (nginx, caddy, etc.).

---

## Interactive Documentation

FastAPI provides interactive API documentation at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
