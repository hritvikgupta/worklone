# Workflow Engine

Worklone includes a powerful **DAG-based workflow engine** that lets AI employees design, build, and execute complex multi-step processes. Workflows can include agents, tools, conditions, loops, parallel execution, and human approvals.

---

## What is a Workflow?

A workflow is a **Directed Acyclic Graph (DAG)** of blocks that execute in a defined order. Each block performs a specific action, and blocks are connected to define the flow of data and control.

```
┌───────┐     ┌───────┐     ┌───────┐     ┌───────┐
│ Start │ ──► │ Agent │ ──► │ Tool  │ ──► │  End  │
└───────┘     └───────┘     └───────┘     └───────┘
```

---

## Block Types

| Block | Purpose | Input | Output |
|-------|---------|-------|--------|
| `start` | Entry point, receives input data | Workflow input | Input data |
| `agent` | Invokes an AI employee | Prompt, context | Agent response |
| `tool` | Executes a single tool | Tool name, parameters | Tool result |
| `function` | Runs custom Python code | Code string | Function output |
| `http` | Makes HTTP requests | URL, method, headers, body | HTTP response |
| `condition` | Branching logic (if/else) | Condition expression | Branch taken |
| `loop` | Iteration over collections | Collection, body | Loop results |
| `parallel` | Concurrent execution | Multiple blocks | Combined results |
| `wait` | Timed delays | Duration | — |
| `variable` | Data manipulation | Expression | Computed value |
| `trigger` | External event triggers | Trigger config | Trigger data |
| `human_approval` | Human-in-the-loop pause | Approval request | Approved/rejected |
| `end` | Workflow completion | Final data | Workflow output |

---

## Trigger Types

| Trigger | Description | Configuration |
|---------|-------------|---------------|
| `api` | Manual API call | None |
| `webhook` | External webhook | Webhook URL |
| `schedule` | Cron-based scheduling | Cron expression |
| `manual` | UI-triggered | None |

---

## Creating a Workflow

### Via API

```bash
# Create workflow
curl -X POST http://localhost:8000/api/workflows \
  -H "Content-Type: application/json" \
  -H "x-user-id: your-user-id" \
  -d '{
    "name": "Daily Report",
    "description": "Generate and send daily metrics report",
    "trigger_type": "schedule",
    "trigger_config": {"cron": "0 9 * * *"}
  }'

# Add blocks
curl -X POST http://localhost:8000/api/workflows/{id}/blocks \
  -H "Content-Type: application/json" \
  -d '{
    "type": "agent",
    "config": {
      "employee_id": "emp-1",
      "prompt": "Generate a summary of yesterday's metrics"
    }
  }'

# Connect blocks
curl -X POST http://localhost:8000/api/workflows/{id}/connections \
  -H "Content-Type: application/json" \
  -d '{
    "from_block_id": "block-1",
    "to_block_id": "block-2"
  }'
```

### Via Dashboard

1. Go to **Workflows** in the sidebar
2. Click **Create Workflow**
3. Use the drag-and-drop builder to add and connect blocks
4. Configure the trigger
5. Click **Save**

---

## Variable Resolution

Blocks can reference outputs from previous blocks using `{{block_name.output.field}}` syntax:

```
Block 1 (agent): Generates a report
Block 2 (tool): Sends the report via email

Block 2 config:
  to: "team@company.com"
  subject: "Daily Report"
  body: "{{generate_report.output.summary}}"
```

### Variable Syntax

| Syntax | Description |
|--------|-------------|
| `{{block_name.output}}` | Full output of a block |
| `{{block_name.output.field}}` | Specific field from output |
| `{{input.field}}` | Workflow input data |
| `{{trigger.data}}` | Trigger payload |

---

## Executing Workflows

### Manual Execution

```bash
curl -X POST http://localhost:8000/api/workflows/{id}/execute \
  -H "Content-Type: application/json" \
  -d '{"input_data": {"date": "2026-04-17"}}'
```

### Scheduled Execution

Workflows with `schedule` triggers run automatically based on cron expressions:

```json
{
  "trigger_type": "schedule",
  "trigger_config": {
    "cron": "0 9 * * *"
  }
}
```

The background worker polls every 5 seconds for scheduled workflows.

### Webhook Execution

```bash
curl -X POST http://localhost:8000/api/workflows/{id}/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "new_user", "user_id": "123"}'
```

---

## Human-in-the-Loop

Use `human_approval` blocks to pause workflows for human review:

```json
{
  "type": "human_approval",
  "config": {
    "message": "Deploy to production?",
    "timeout_seconds": 3600
  }
}
```

### Approving via API

```bash
curl -X POST http://localhost:8000/api/workflows/{id}/executions/{exec_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

---

## Parallel Execution

Run multiple blocks concurrently:

```json
{
  "type": "parallel",
  "config": {
    "blocks": [
      {"type": "tool", "config": {"tool": "analyze_sales"}},
      {"type": "tool", "config": {"tool": "analyze_marketing"}},
      {"type": "tool", "config": {"tool": "analyze_engineering"}}
    ]
  }
}
```

---

## Condition Blocks

Branch based on conditions:

```json
{
  "type": "condition",
  "config": {
    "expression": "{{analyze_data.output.score}} > 80",
    "true_block": "notify_success",
    "false_block": "notify_failure"
  }
}
```

---

## Loop Blocks

Iterate over collections:

```json
{
  "type": "loop",
  "config": {
    "collection": "{{get_users.output.users}}",
    "body": {
      "type": "tool",
      "config": {"tool": "send_email", "parameters": {"to": "{{item.email}}"}}
    }
  }
}
```

---

## Monitoring Workflows

### Execution History

```bash
curl http://localhost:8000/api/workflows/{id}/executions
```

Returns all executions with status, duration, and results.

### Execution Status

```bash
curl http://localhost:8000/api/workflows/{id}/executions/{exec_id}
```

Returns detailed execution status including per-block results.

### Execution States

| State | Description |
|-------|-------------|
| `pending` | Waiting to start |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Execution failed |
| `paused` | Waiting for human approval |
| `cancelled` | Manually cancelled |

---

## Background Worker

The background worker (`backend/core/workflows/worker.py`) handles scheduled workflow execution:

| Setting | Default | Description |
|---------|---------|-------------|
| `WORKER_POLL_INTERVAL` | 5 seconds | How often to check for scheduled workflows |
| `WORKER_MAX_CONCURRENT` | 10 | Maximum concurrent workflow executions |

Configure via `.env`:

```env
WORKER_POLL_INTERVAL=10
WORKER_MAX_CONCURRENT=20
```

---

## Workflow Architecture

### DAG Builder

Converts workflow definitions into a Directed Acyclic Graph:

```
Workflow Definition → DAG Builder → Topological Sort → Execution Plan
```

### Executor

Executes blocks in dependency order:

1. **Topological sort** — determine execution order
2. **Sequential blocks** — execute one at a time
3. **Parallel blocks** — execute concurrently
4. **Variable resolution** — substitute `{{...}}` references
5. **Error handling** — catch and report failures

### Data Flow

```
Trigger → Input Data → Block 1 → Block 2 → ... → Output Data
              │            │         │
              ▼            ▼         ▼
         {{input}}   {{block1}}  {{block2}}
```

---

## Best Practices

1. **Start simple** — begin with linear workflows before adding complexity
2. **Use variables** — pass data between blocks with `{{block.output}}` syntax
3. **Add human approvals** — for critical steps like deployments
4. **Monitor executions** — check execution history for failures
5. **Handle errors** — use condition blocks for error routing
6. **Parallelize** — use parallel blocks for independent tasks
7. **Test manually** — execute workflows manually before scheduling
