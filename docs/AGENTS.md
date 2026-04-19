# AI Employees

Worklone's core concept: **AI employees** are autonomous agents that work for your company. They reason about tasks, use tools, execute workflows, collaborate with other employees, and learn from every interaction.

---

## What is an AI Employee?

An AI employee is not a chatbot. It's an autonomous agent that:

- **Reasons** about problems using the ReAct (Reasoning + Acting) pattern
- **Uses tools** autonomously — decides which tool to use and when
- **Plans** multi-step tasks before executing them
- **Learns** from experience — builds skills and remembers user preferences
- **Collaborates** — can message other employees and humans
- **Executes workflows** — can create and run DAG-based workflows
- **Adapts** — gets better at understanding your needs over time

---

## Employee Anatomy

Every employee has these attributes:

| Attribute | Description |
|-----------|-------------|
| `name` | Employee's display name |
| `role` | Their job title (e.g., "Product Manager", "Sales Rep") |
| `description` | What they do and their expertise |
| `system_prompt` | Core instructions and personality |
| `model` | LLM model to use (e.g., `openai/gpt-4o`) |
| `temperature` | Creativity level (0.0–1.0) |
| `max_tokens` | Maximum response length |
| `tools` | List of tool names the employee can use |
| `skills` | Assigned skills with proficiency levels |
| `status` | Current state: IDLE, WORKING, BLOCKED |

---

## Pre-configured Employee Templates

Worklone includes example employee configurations you can use as starting points.

Typical template focus areas:

- Product and planning roles
- Engineering and debugging roles
- Operations and support roles
- Research and analysis roles

You can fully customize any template:

- identity and role
- system prompt
- allowed tools
- assigned skills
- model/provider behavior via LLM settings

---

## Creating Custom Employees

You can create AI employees for any role. Here's how:

### Via API

```bash
curl -X POST http://localhost:8000/api/employees \
  -H "Content-Type: application/json" \
  -H "x-user-id: your-user-id" \
  -d '{
    "name": "Alex",
    "role": "Sales Development Rep",
    "description": "AI sales rep that manages leads and outreach",
    "system_prompt": "You are Alex, an experienced SDR...",
    "model": "openai/gpt-4o",
    "temperature": 0.7,
    "tools": ["salesforce_create_lead", "gmail_send_email", "google_calendar_create_event"]
  }'
```

### Via Dashboard

1. Go to **Employees** in the sidebar
2. Click **Create Employee**
3. Fill in name, role, description, and system prompt
4. Select tools from the catalog
5. Click **Create**

---

## Assigning Tools

Tools define what an employee can do. Assign tools during creation or update:

```bash
curl -X PATCH http://localhost:8000/api/employees/{id}/tools \
  -H "Content-Type: application/json" \
  -d '{"tools": ["github_create_issue", "slack_send_message", "notion_create_page"]}'
```

### Tool Categories

| Category | Description | Example Tools |
|----------|-------------|---------------|
| System | Core utilities | `file_read`, `http_request`, `shell_exec` |
| Integrations | External services | `github_create_issue`, `slack_send_message` |
| Employee | Agent collaboration | `ask_user`, `run_task_async`, `send_message_to_coworker` |
| Workflow | Workflow management | `create_workflow`, `execute_workflow` |
| Specialized | Role-specific | `pm_create_prd`, `engineer_review_code` |

See [Tools Documentation](TOOLS.md) for the complete list and how to build custom tools.

---

## Assigning Skills

Skills are procedural knowledge — step-by-step guides for complex tasks. Employees can have:

- **Public skills** — from the shared skills library
- **Learned skills** — automatically discovered through experience

```bash
curl -X POST http://localhost:8000/api/employees/{id}/skills \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "skill-123",
    "category": "data_analysis",
    "proficiency": "expert"
  }'
```

---

## Chatting with Employees

### Direct Chat (Non-Streaming)

```bash
curl -X POST http://localhost:8000/api/employees/{id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a GitHub issue for the login bug"}'
```

### Streaming Chat (SSE)

```javascript
const eventSource = new EventSource(
  `/api/employees/${id}/chat/stream?message=Create+a+GitHub+issue`
);

eventSource.onmessage = (event) => {
  console.log(event.data); // Streaming tokens
};
```

---

## Employee Statuses

| Status | Meaning |
|--------|---------|
| `IDLE` | Employee is available for new tasks |
| `WORKING` | Employee is currently processing a task |
| `BLOCKED` | Employee is waiting for user input (human-in-the-loop) |

---

## Team Collaboration

Employees can work together in teams:

### Creating a Team Run

```bash
curl -X POST http://localhost:8000/api/teams/{id}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"employee_id": "emp-1", "task": "Research competitors"},
      {"employee_id": "emp-2", "task": "Analyze pricing data"},
      {"employee_id": "emp-3", "task": "Draft pricing strategy"}
    ]
  }'
```

### How Teams Work

- The `TeamRunner` spawns all employee agents concurrently
- Each agent discovers team context via `get_my_team_context`
- Agents communicate through shared conversation
- Results are aggregated when all agents complete

---

## Sprint Execution

Sprints are for sequential task execution with auto-approval:

```bash
curl -X POST http://localhost:8000/api/sprints/{id}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "emp-1",
    "tasks": [
      "Analyze the codebase",
      "Identify technical debt",
      "Create refactoring plan"
    ]
  }'
```

Sprint agents run with `auto_approve_human=True` — they don't pause for approval between tasks.

---

## Monitoring Employees

### Activity Logs

```bash
curl http://localhost:8000/api/employees/{id}/activity
```

Returns detailed activity logs with timestamps, actions, and outcomes.

### Usage Statistics

```bash
curl http://localhost:8000/api/employees/{id}/usage
```

Returns token usage, cost, and duration metrics per employee.

### Tasks

```bash
# List tasks
curl http://localhost:8000/api/employees/{id}/tasks

# Create task
curl -X POST http://localhost:8000/api/employees/{id}/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Review Q4 metrics",
    "description": "Analyze Q4 performance data",
    "status": "pending",
    "priority": "high",
    "tags": ["analytics", "quarterly"]
  }'
```

---

## Employee Memory

Employees automatically build memory about users:

- **User memory** — facts about work style, preferences, goals (updated every 8 turns)
- **Team memory** — shared context for team runs
- **Learned skills** — procedural knowledge from experience (updated every 10 tool iterations)

Memory is injected into the system prompt automatically so employees remember context across conversations.

See [Self-Learning Documentation](SELF_LEARNING.md) for details.

---

## Execution Modes

Employees support different execution modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Direct Response** | Single LLM call, no planning | Simple questions |
| **Plan-First** | Creates plan, asks user, then executes | Multi-step tasks |
| **Background** | Spawns async task, returns immediately | Long-running work |

---

## Best Practices

1. **Be specific with system prompts** — detailed role definitions produce better results
2. **Assign only needed tools** — fewer tools = faster decisions
3. **Use plan-first mode** — for complex tasks, planning reduces errors
4. **Monitor usage** — track tokens and costs per employee
5. **Let employees learn** — the more you use them, the better they get
6. **Create teams** — combine specialized employees for complex workflows
